import hashlib
from uuid import uuid4

from django.db import transaction
from django.db.models import F, Max, Q
from django.utils import timezone

from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.businesses.models import Membership
from tapme.customers.models import CustomerRecord
from tapme.messaging.domain import message_text, reply_allowed
from tapme.messaging.infrastructure.channels import ChannelOperations
from tapme.messaging.infrastructure.features import ChatFeatures
from tapme.messaging.infrastructure.folders import ChatFolders
from tapme.messaging.models import ChannelAccount, Conversation, ConversationRead, Message
from tapme.orders.models import OrderRecord
from tapme.shared.domain import Conflict, InvalidInput, NotFound


def reply_data(row):
    return {
        "id": str(row.id),
        "text": row.text[:500],
        "direction": row.direction,
        "sender": row.sender.get_full_name() or row.sender.username if row.sender else "",
        "kind": row.kind,
        "media_name": row.media_name,
    }


def message_data(row, replies=None):
    original = None
    if row.context_id:
        original = (
            replies.get(row.context_id)
            if replies is not None
            else row.conversation.messages.select_related("sender")
            .filter(external_id=row.context_id, direction__in=["in", "out"])
            .first()
        )
    return {
        "id": str(row.id),
        "request_id": str(row.request_id),
        "direction": row.direction,
        "text": row.text,
        "kind": row.kind,
        "status": row.status,
        "error": row.error,
        "sender": row.sender.get_full_name() or row.sender.username if row.sender else "",
        "happened_at": row.happened_at,
        "created_at": row.created_at,
        "media_url": f"/api/v1/businesses/{row.conversation.channel.business_id}/chats/{row.conversation_id}/messages/{row.id}/file/"
        if row.media_key
        else None,
        "automated": row.automated,
        "context_id": row.context_id,
        "external_id": row.external_id,
        "reply_to": reply_data(original) if original else None,
        "media_type": row.media_type,
        "media_name": row.media_name,
    }


def conversation_data(row, user_id):
    marker = ConversationRead.objects.filter(conversation=row, user_id=user_id).first()
    unread = row.messages.filter(
        direction="in", id__gt=marker.last_message_id if marker else 0
    ).count()
    reason = ""
    if row.channel.status != "active":
        reason = "WhatsApp не подключён. История доступна для просмотра."
    elif row.needs_customer_link:
        reason = "Этот номер найден у нескольких клиентов. Сначала выберите карточку клиента."
    elif row.opted_out:
        reason = "Клиент попросил не писать ему."
    elif row.mode == "closed":
        reason = "Диалог закрыт. Откройте его, чтобы ответить."
    elif not reply_allowed(row.last_inbound_at, timezone.now()):
        reason = "Прошло 24 часа после последнего сообщения клиента. Свободный ответ станет доступен, когда клиент снова напишет."
    return {
        "id": str(row.id),
        "customer_id": str(row.customer_id) if row.customer_id else None,
        "name": row.customer.name if row.customer else row.profile_name or row.phone,
        "phone": row.phone,
        "channel_phone": row.channel.display_phone,
        "provider_mode": row.channel.provider_mode,
        "preview": row.last_message_preview,
        "last_message_at": row.last_message_at,
        "last_inbound_at": row.last_inbound_at,
        "waiting_since": row.waiting_since,
        "unread": unread,
        "mode": row.mode,
        "version": row.version,
        "assigned_to": str(row.assigned_to_id) if row.assigned_to_id else None,
        "assigned_name": (row.assigned_to.get_full_name() or row.assigned_to.username)
        if row.assigned_to
        else "",
        "new_customer": row.customer_created and not row.customer_name_confirmed,
        "origin": row.customer.origin if row.customer else "",
        "needs_customer_link": row.needs_customer_link,
        "can_reply": not reason,
        "reply_reason": reason,
        "tags": row.customer.tags if row.customer else [],
        "folder_ids": [str(folder.id) for folder in row.folders.all()],
    }


class DjangoChatRepository(ChannelOperations, ChatFeatures, ChatFolders):
    def __init__(self, gateway, storage=None):
        self.gateway, self.storage = gateway, storage

    def run(self, operation, scope, **data):
        return getattr(self, operation)(scope, **data)

    def _conversation(self, scope, chat_id, lock=False):
        qs = Conversation.objects.filter(channel__business_id=scope.business_id)
        if lock:
            qs = qs.select_for_update(of=("self",))
        row = qs.select_related("channel", "customer", "assigned_to").filter(id=chat_id).first()
        if not row:
            raise NotFound("Диалог не найден.")
        return row

    def listing(self, scope, search="", category="all", limit=50, offset=0, folder_id=None):
        qs = (
            Conversation.objects.filter(channel__business_id=scope.business_id)
            .select_related("channel", "customer", "assigned_to")
            .prefetch_related("folders")
        )
        if folder_id:
            self._folder(scope, folder_id)
            qs = qs.filter(folders__id=folder_id)
        stats = {
            "all": qs.exclude(mode="closed").count(),
            "waiting": qs.filter(mode="human", waiting_since__isnull=False).count(),
            "mine": qs.filter(assigned_to_id=scope.user_id).exclude(mode="closed").count(),
            "closed": qs.filter(mode="closed").count(),
        }
        if category == "closed":
            qs = qs.filter(mode="closed")
        else:
            qs = qs.exclude(mode="closed")
        if category == "waiting":
            qs = qs.filter(waiting_since__isnull=False)
        if category == "mine":
            qs = qs.filter(assigned_to_id=scope.user_id)
        if search:
            qs = qs.filter(
                Q(customer__name__icontains=search)
                | Q(phone__icontains=search)
                | Q(profile_name__icontains=search)
            )
        qs = qs.order_by(F("waiting_since").asc(nulls_last=True), "-last_message_at", "id")
        return {
            "count": qs.count(),
            "stats": stats,
            "results": [conversation_data(r, scope.user_id) for r in qs[offset : offset + limit]],
        }

    def detail(self, scope, chat_id):
        row = self._conversation(scope, chat_id)
        result = conversation_data(row, scope.user_id)
        result["customer"] = None
        result["link_candidates"] = []
        if row.customer:
            orders = OrderRecord.objects.filter(
                business_id=scope.business_id,
                point_id__in=DjangoMembershipReader().point_ids(scope),
                customer_id=row.customer_id,
            ).exclude(status="cancelled")
            result["customer"] = {
                "notes": row.customer.notes,
                "created_at": row.customer.created_at,
                "consent": row.customer.consent,
                "orders_count": orders.count(),
                "dates": list(row.customer.dates.values("id", "label", "person", "month", "day")),
                "orders": [
                    {
                        "id": str(o.id),
                        "number": o.number,
                        "total": str(o.total),
                        "status": o.status,
                        "date": o.delivery_date,
                    }
                    for o in orders.order_by("-created_at")[:5]
                ],
            }
        if row.needs_customer_link:
            result["link_candidates"] = list(
                CustomerRecord.objects.filter(business_id=scope.business_id)
                .filter(Q(phone=row.phone) | Q(additional_phones__contains=[row.phone]))
                .values("id", "name", "phone")
            )
        result["staff"] = [
            {"id": str(m.user_id), "name": m.user.get_full_name() or m.user.username}
            for m in Membership.objects.filter(
                business_id=scope.business_id,
                is_active=True,
                user__is_active=True,
                role__in=["owner", "manager"],
            ).select_related("user")
        ]
        return result

    def messages(self, scope, chat_id, before=0, after=0, limit=50):
        chat = self._conversation(scope, chat_id)
        qs = chat.messages.select_related("sender", "conversation__channel")
        if before:
            qs = qs.filter(id__lt=before)
        if after:
            qs = qs.filter(id__gt=after)
        rows = list(qs.order_by("id" if after else "-id")[: limit + 1])
        more = len(rows) > limit
        rows = rows[:limit]
        if not after:
            rows.reverse()
        replies = {
            m.external_id: m
            for m in chat.messages.select_related("sender").filter(
                external_id__in={row.context_id for row in rows if row.context_id},
                direction__in=["in", "out"],
            )
        }
        return {"results": [message_data(m, replies) for m in rows], "has_more": more}

    @transaction.atomic
    def read(self, scope, chat_id, last_message_id):
        chat = self._conversation(scope, chat_id, lock=True)
        # Mark only the messages the browser actually displayed, never unseen arrivals.
        maximum = (
            chat.messages.filter(id__lte=last_message_id).aggregate(value=Max("id"))["value"] or 0
        )
        marker, _ = ConversationRead.objects.get_or_create(conversation=chat, user_id=scope.user_id)
        marker.last_message_id = max(marker.last_message_id, maximum)
        marker.save(update_fields=["last_message_id"])
        latest = (
            chat.messages.filter(direction="in", id__lte=maximum)
            .exclude(external_id=None)
            .order_by("-id")
            .first()
        )
        if latest:
            chat.provider_read_message_id = max(chat.provider_read_message_id, latest.id)
            chat.save(update_fields=["provider_read_message_id"])
        return {"ok": True}

    @transaction.atomic
    def start(self, scope, customer_id):
        customer = CustomerRecord.objects.filter(
            id=customer_id, business_id=scope.business_id
        ).first()
        channel = ChannelAccount.objects.filter(business_id=scope.business_id).first()
        if not customer:
            raise NotFound("Клиент не найден.")
        if not channel or channel.status != "active":
            raise InvalidInput("Сначала подключите WhatsApp в настройках каналов.")
        row, created = Conversation.objects.get_or_create(
            channel=channel, phone=customer.phone, defaults={"customer": customer}
        )
        if not created and row.customer_id != customer.id:
            raise Conflict("Этот номер связан с другой карточкой клиента. Проверьте связь в чате.")
        return conversation_data(row, scope.user_id)

    @transaction.atomic
    def update(self, scope, chat_id, version, **changes):
        row = self._conversation(scope, chat_id, lock=True)
        if row.version != version:
            raise Conflict("Диалог изменился в другой вкладке. Обновите и повторите.")
        if "assigned_to" in changes:
            user_id = changes["assigned_to"]
            if (
                user_id
                and not Membership.objects.filter(
                    business_id=scope.business_id,
                    user_id=user_id,
                    is_active=True,
                    user__is_active=True,
                    role__in=["owner", "manager"],
                ).exists()
            ):
                raise InvalidInput("Выберите действующего владельца или менеджера магазина.")
            row.assigned_to_id = user_id
        if "customer_name" in changes:
            if not row.customer_id:
                raise InvalidInput("Сначала привяжите клиента.")
            CustomerRecord.objects.filter(id=row.customer_id, business_id=scope.business_id).update(
                name=changes["customer_name"], version=F("version") + 1
            )
            row.customer_name_confirmed = True
        if "mode" in changes:
            row.mode = changes["mode"]
        if "customer_id" in changes:
            customer = (
                CustomerRecord.objects.filter(
                    business_id=scope.business_id, id=changes["customer_id"]
                )
                .filter(Q(phone=row.phone) | Q(additional_phones__contains=[row.phone]))
                .first()
            )
            if not row.needs_customer_link or not customer:
                raise InvalidInput("Выберите клиента, которому принадлежит этот номер.")
            row.customer = customer
            row.needs_customer_link = False
        row.version += 1
        row.save()
        return self.detail(scope, chat_id)

    def _reply_context(self, chat, reply_to_id):
        if reply_to_id is None:
            return ""
        original = chat.messages.filter(id=reply_to_id, direction__in=["in", "out"]).first()
        if not original:
            raise InvalidInput("Сообщение для ответа не найдено в этом диалоге.")
        if not original.external_id or original.status not in {
            "received",
            "sent",
            "delivered",
            "read",
        }:
            raise InvalidInput(
                "Ответ с цитатой доступен только для полученного или отправленного сообщения."
            )
        return original.external_id

    @transaction.atomic
    def send(self, scope, chat_id, text, request_id, reply_to_id=None):
        chat = self._conversation(scope, chat_id, lock=True)
        text = message_text(text)
        old = chat.messages.filter(request_id=request_id).first()
        if old:
            if (
                old.direction != "out"
                or old.kind != "text"
                or old.text != text
                or old.sender_id != scope.user_id
                or old.payload.get("reply_to_id") != (str(reply_to_id) if reply_to_id else None)
            ):
                raise Conflict("Этот запрос уже использован для другого сообщения.")
            return message_data(old)
        current = conversation_data(chat, scope.user_id)
        if not current["can_reply"]:
            raise InvalidInput(current["reply_reason"])
        context_id = self._reply_context(chat, reply_to_id)
        row = Message.objects.create(
            conversation=chat,
            direction="out",
            sender_id=scope.user_id,
            text=text,
            request_id=request_id,
            context_id=context_id,
            payload={"reply_to_id": str(reply_to_id)} if reply_to_id else {},
        )
        if not chat.assigned_to_id:
            chat.assigned_to_id = scope.user_id
        chat.last_message_at = row.created_at
        chat.last_message_preview = text[:160]
        chat.version += 1
        chat.save()
        self.assign_customer(scope, chat)
        return message_data(row)

    @transaction.atomic
    def retry(self, scope, chat_id, message_id):
        chat = self._conversation(scope, chat_id, lock=True)
        row = chat.messages.select_for_update().filter(id=message_id, direction="out").first()
        if not row:
            raise NotFound("Сообщение не найдено.")
        if row.status != "failed":
            raise Conflict(
                "Повтор доступен только для сообщения с подтверждённой ошибкой отправки."
            )
        current = conversation_data(chat, scope.user_id)
        if not current["can_reply"]:
            raise InvalidInput(current["reply_reason"])
        row.status, row.error, row.external_id = "queued", "", None
        row.delivery_key = uuid4()
        row.sender_id = scope.user_id
        row.save(update_fields=["status", "error", "external_id", "sender", "delivery_key"])
        return message_data(row)

    @transaction.atomic
    def attach(self, scope, chat_id, content, mime, name, text, request_id, reply_to_id=None):
        chat = self._conversation(scope, chat_id, lock=True)
        fingerprint = hashlib.sha256(content).hexdigest()
        old = chat.messages.filter(request_id=request_id).first()
        if old:
            if (
                old.payload.get("digest") != fingerprint
                or old.text != text
                or old.sender_id != scope.user_id
                or old.payload.get("reply_to_id") != (str(reply_to_id) if reply_to_id else None)
            ):
                raise Conflict("Этот запрос уже использован для другого вложения.")
            return message_data(old)
        current = conversation_data(chat, scope.user_id)
        if not current["can_reply"]:
            raise InvalidInput(current["reply_reason"])
        context_id = self._reply_context(chat, reply_to_id)
        if mime not in {"image/jpeg", "image/png", "image/webp", "application/pdf"}:
            raise InvalidInput("Прикрепите фотографию или PDF до 16 МБ (фото до 5 МБ).")
        key, stored_type = self.storage.save(
            f"{scope.business_id}/chats/{chat.id}/{uuid4().hex}", content, mime
        )
        if stored_type == "image/jpeg" and len(self.storage.read(key)) > 5 * 1024 * 1024:
            self.storage.delete(key)
            raise InvalidInput("Изображение после обработки превышает 5 МБ.")
        try:
            row = Message.objects.create(
                conversation=chat,
                direction="out",
                sender_id=scope.user_id,
                text=text,
                kind="image" if stored_type.startswith("image/") else "document",
                request_id=request_id,
                media_key=key,
                media_type=stored_type,
                media_name=name[:150],
                context_id=context_id,
                payload={
                    "digest": fingerprint,
                    **({"reply_to_id": str(reply_to_id)} if reply_to_id else {}),
                },
            )
            if not chat.assigned_to_id:
                chat.assigned_to_id = scope.user_id
            chat.last_message_at, chat.last_message_preview = (
                row.created_at,
                text[:160] or "Вложение",
            )
            chat.version += 1
            chat.save()
            self.assign_customer(scope, chat)
        except Exception:
            self.storage.delete(key)
            raise
        return message_data(row)

    def file(self, scope, chat_id, message_id):
        chat = self._conversation(scope, chat_id)
        row = chat.messages.filter(id=message_id).exclude(media_key="").first()
        if not row:
            raise NotFound("Вложение не найдено.")
        return {
            "content": self.storage.read(row.media_key),
            "mime": row.media_type,
            "name": row.media_name or "attachment",
        }
