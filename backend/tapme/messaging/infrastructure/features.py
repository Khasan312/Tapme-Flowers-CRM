from decimal import Decimal

from django.db import transaction
from django.db.models import Count, F, Q

from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.businesses.models import Shop
from tapme.customers.models import CustomerRecord
from tapme.messaging.infrastructure.queries import unread_messages
from tapme.messaging.models import Conversation, Message, QuickReply
from tapme.orders.models import OrderRecord
from tapme.shared.domain import Conflict, InvalidInput, NotFound


def quick_data(row):
    return {
        "id": str(row.id),
        "title": row.title,
        "text": row.text,
        "sort_order": row.sort,
        "version": row.version,
    }


class ChatFeatures:
    def assign_customer(self, scope, chat):
        if chat.customer_id:
            CustomerRecord.objects.filter(id=chat.customer_id, responsible=None).update(
                responsible_id=scope.user_id, version=F("version") + 1
            )

    def summary(self, scope, after=0):
        chats = Conversation.objects.filter(channel__business_id=scope.business_id).exclude(
            mode="closed"
        )
        eligible = chats.filter(Q(assigned_to_id=scope.user_id) | Q(assigned_to=None))
        incoming = Message.objects.filter(conversation__in=eligible, direction="in")
        latest = incoming.order_by("-id").first()
        items = (
            incoming.filter(id__gt=after)
            .select_related("conversation__customer", "conversation__channel")
            .order_by("-id")[:10]
        )
        unread = unread_messages(scope.user_id).filter(conversation__in=chats).count()
        return {
            "unread": unread,
            "unread_by_channel": dict(
                unread_messages(scope.user_id)
                .filter(conversation__in=chats)
                .order_by()
                .values("conversation__channel__kind")
                .annotate(total=Count("id"))
                .values_list("conversation__channel__kind", "total")
            ),
            "waiting": chats.filter(waiting_since__isnull=False).count(),
            "latest_inbound_id": str(latest.id) if latest else "0",
            "items": [
                {
                    "id": str(m.id),
                    "chat_id": str(m.conversation_id),
                    "channel_kind": m.conversation.channel.kind,
                    "name": m.conversation.customer.name
                    if m.conversation.customer
                    else m.conversation.profile_name or m.conversation.phone,
                    "text": m.text[:100],
                }
                for m in items
            ],
        }

    def quick_replies(self, scope):
        return [
            quick_data(row)
            for row in QuickReply.objects.filter(business_id=scope.business_id).order_by(
                "sort", "title", "id"
            )
        ]

    @transaction.atomic
    def save_quick_reply(self, scope, title, text, reply_id=None, version=None, sort_order=0):
        if reply_id:
            row = (
                QuickReply.objects.select_for_update()
                .filter(id=reply_id, business_id=scope.business_id)
                .first()
            )
            if not row:
                raise NotFound("Быстрый ответ не найден.")
            if row.version != version:
                raise Conflict("Ответ уже изменён. Обновите список.")
            row.version += 1
        else:
            row = QuickReply(business_id=scope.business_id, created_by_id=scope.user_id)
        row.title, row.text, row.sort = title, text, sort_order
        row.save()
        return quick_data(row)

    @transaction.atomic
    def delete_quick_reply(self, scope, reply_id, version):
        row = (
            QuickReply.objects.select_for_update()
            .filter(id=reply_id, business_id=scope.business_id)
            .first()
        )
        if not row:
            raise NotFound("Быстрый ответ не найден.")
        if row.version != version:
            raise Conflict("Ответ изменён в другой вкладке.")
        row.delete()
        return {"ok": True}

    def payment_options(self, scope, chat_id):
        chat = self._conversation(scope, chat_id)
        orders = (
            OrderRecord.objects.filter(
                business_id=scope.business_id,
                point_id__in=DjangoMembershipReader().point_ids(scope),
                customer_id=chat.customer_id,
            )
            .exclude(status__in=["cancelled", "delivered"])
            .prefetch_related("payments")
            .order_by("-created_at")
            if chat.customer_id
            else []
        )
        result = []
        for order in orders:
            paid = sum(
                (p.amount if p.kind == "payment" else -p.amount for p in order.payments.all()),
                Decimal("0"),
            )
            due = max(Decimal("0"), order.total - paid)
            if due:
                result.append({"id": str(order.id), "number": order.number, "amount": str(due)})
        return {**self.payment(scope), "orders": result[:20]}

    @transaction.atomic
    def send_payment(self, scope, chat_id, amount, request_id, order_id=None):
        from tapme.messaging.infrastructure.repository import message_data

        chat = self._conversation(scope, chat_id, lock=True)
        old = chat.messages.filter(request_id=request_id).first()
        marker = {"amount": str(amount), "order_id": str(order_id) if order_id else None}
        if old:
            if old.payload.get("payment") != marker or old.sender_id != scope.user_id:
                raise Conflict("Этот запрос уже использован для другого сообщения.")
            return message_data(old)
        number = "—"
        if order_id:
            order = OrderRecord.objects.filter(
                id=order_id,
                business_id=scope.business_id,
                point_id__in=DjangoMembershipReader().point_ids(scope),
                customer_id=chat.customer_id,
            ).first()
            if not order or not chat.customer_id:
                raise InvalidInput("Выберите заказ этого клиента.")
            shop = Shop.objects.select_for_update().get(
                id=order.point_id, business_id=scope.business_id
            )
            number = str(order.number)
        else:
            shop = self.payment_shop(scope, lock=True)
        if not shop.payment_qr_key:
            raise InvalidInput("Для выбранной точки ещё не загружен QR в настройках каналов.")
        text = shop.payment_message.replace("{номер}", number).replace("{сумма}", str(amount))
        result = self.attach(
            scope,
            chat_id,
            self.storage.read(shop.payment_qr_key),
            "image/jpeg",
            "payment-qr.jpg",
            text[:1024],
            request_id,
        )
        row = Message.objects.get(id=result["id"])
        row.payload["payment"] = marker
        row.save(update_fields=["payload"])
        return result
