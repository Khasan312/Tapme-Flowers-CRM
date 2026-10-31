import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from tapme.businesses.models import Business, Membership
from tapme.customers.models import CustomerRecord
from tapme.messaging.domain import DeliveryRejected, DeliveryUnknown, automatic_reply, reply_allowed
from tapme.messaging.infrastructure.meta import decrypt, gateway_for
from tapme.messaging.models import ChannelAccount, Conversation, Message, WebhookEvent
from tapme.shared.domain import InvalidInput, NotFound


def receive(body, signature, channel=None):
    secret = decrypt(channel.app_secret_encrypted) if channel else settings.META_APP_SECRET
    if not secret:
        raise InvalidInput("Канал не настроен.")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected.encode(), (signature or "").encode()):
        return False
    payload = json.loads(body)
    if not isinstance(payload, dict) or payload.get("object") != (
        "instagram" if channel and channel.kind == "instagram" else "whatsapp_business_account"
    ):
        raise ValueError("Unexpected object")
    WebhookEvent.objects.get_or_create(
        digest=hashlib.sha256((str(channel.id).encode() if channel else b"") + body).hexdigest(),
        defaults={"payload": payload, "channel": channel},
    )
    return True


def instant(value):
    try:
        result = datetime.fromtimestamp(int(value), tz=UTC)
        # Signed webhooks still need sane timestamps for the reply-window calculation.
        return min(result, timezone.now())
    except (ValueError, TypeError, OverflowError, OSError):
        return timezone.now() - timedelta(days=2)


def incoming(channel, data, names):
    external = str(data.get("id", ""))[:500]
    sender = str(data.get("from", ""))
    if not external or not sender.isdecimal() or not 8 <= len(sender) <= 15:
        return
    phone = "+" + sender
    chat, _ = Conversation.objects.get_or_create(channel=channel, phone=phone)
    chat = Conversation.objects.select_for_update().get(id=chat.id)
    if chat.messages.filter(external_id=external).exists():
        return
    previous_inbound = chat.last_inbound_at
    had_messages = chat.messages.exists()
    if not chat.customer_id and not chat.needs_customer_link:
        Business.objects.select_for_update().get(id=channel.business_id)
        matches = list(
            CustomerRecord.objects.filter(business_id=channel.business_id).filter(
                Q(phone=phone) | Q(additional_phones__contains=[phone])
            )[:2]
        )
        if len(matches) == 1:
            chat.customer = matches[0]
        elif len(matches) > 1:
            chat.needs_customer_link = True
        else:
            chat.customer = CustomerRecord.objects.create(
                business_id=channel.business_id,
                phone=phone,
                name=names.get(sender, phone)[:150],
                source="WhatsApp",
                origin="whatsapp",
                consent=False,
            )
            chat.customer_created = True
    kind = str(data.get("type", "unsupported"))[:30]
    content = data.get(kind) or {}
    text = ""
    if kind == "text":
        text = str(content.get("body", ""))[:4096]
    elif kind in {"image", "document", "video", "audio", "sticker"}:
        text = str(content.get("caption", ""))[:4096]
    elif kind == "interactive":
        answer = content.get("button_reply") or content.get("list_reply") or {}
        text = str(answer.get("title", ""))[:4096]
    elif kind == "button":
        text = str(content.get("text", ""))[:4096]
    elif kind == "location":
        text = f"Местоположение: {content.get('name', '')} {content.get('address', '')} ({content.get('latitude', '')}, {content.get('longitude', '')})"[
            :4096
        ]
    elif kind == "reaction":
        text = "Реакция: " + str(content.get("emoji", "снята"))
    elif kind == "contacts" and isinstance(content, list):
        text = (
            "Контакты: "
            + "; ".join(
                str(c.get("name", {}).get("formatted_name", "Контакт"))
                + " "
                + ", ".join(str(p.get("phone", "")) for p in c.get("phones", []))
                for c in content
            )[:4000]
        )
        content = {"contacts": content}
    if not text:
        text = {
            "image": "Фотография",
            "document": "Документ",
            "audio": "Голосовое сообщение",
            "video": "Видео",
            "sticker": "Стикер",
            "contacts": "Контакт",
            "reaction": "Реакция",
        }.get(kind, "Сообщение неподдерживаемого типа")
    when = instant(data.get("timestamp"))
    Message.objects.create(
        conversation=chat,
        external_id=external,
        direction="in",
        kind=kind,
        text=text,
        payload=content,
        status="received",
        happened_at=when,
        context_id=str((data.get("context") or {}).get("id", ""))[:500],
    )
    chat.profile_name = names.get(sender, chat.profile_name)[:150]
    chat.last_inbound_at = max(chat.last_inbound_at or when, when)
    if not had_messages or when >= chat.last_message_at:
        chat.last_message_at = when
        chat.last_message_preview = text[:160]
    chat.mode = "human"
    chat.waiting_since = chat.waiting_since or timezone.now()
    # An explicit refusal is never turned into marketing consent by receiving a message.
    if text.strip().casefold() in {"стоп", "stop", "отписаться", "не пишите", "не пишите мне"}:
        chat.opted_out = True
        if chat.customer_id:
            customer = CustomerRecord.objects.select_for_update().get(id=chat.customer_id)
            customer.consent = False
            customer.version += 1
            customer.save(update_fields=["consent", "version"])
    chat.version += 1
    chat.save()
    channel.last_inbound_at = timezone.now()
    channel.save(update_fields=["last_inbound_at"])
    # Shared-app legacy channels keep their previous behavior.
    if channel.app_secret_encrypted and not chat.opted_out and not chat.needs_customer_link:
        answer = automatic_reply(
            channel.autoreply,
            now=timezone.now(),
            received_at=when,
            previous_inbound=previous_inbound,
            last_reply=chat.autoreplied_at,
            business_timezone=channel.business.timezone,
            business_name=channel.business.name,
        )
        if answer:
            Message.objects.create(conversation=chat, direction="out", text=answer, automated=True)
            chat.autoreplied_at = timezone.now()
            chat.save(update_fields=["autoreplied_at"])


class PendingReceipt(Exception):
    pass


def delivery_status(channel, data):
    external = str(data.get("id", ""))[:500]
    status = data.get("status")
    if not external or status not in {"sent", "delivered", "read", "failed"}:
        return
    qs = Message.objects.select_for_update().filter(conversation__channel=channel, direction="out")
    row = qs.filter(external_id=external).first()
    if not row and data.get("biz_opaque_callback_data"):
        try:
            correlation = UUID(data["biz_opaque_callback_data"])
        except (ValueError, TypeError, AttributeError):
            return
        row = qs.filter(
            delivery_key=correlation, conversation__phone="+" + str(data.get("recipient_id", ""))
        ).first()
    if not row:
        return False
    ranks = {
        "queued": 0,
        "sending": 1,
        "unknown": 1,
        "failed": 1,
        "sent": 2,
        "delivered": 3,
        "read": 4,
    }
    if status == "failed" and row.status in {"delivered", "read"}:
        return
    if status != "failed" and ranks[status] < ranks[row.status]:
        return
    row.external_id = external
    row.status = status
    row.error = "WhatsApp сообщил об ошибке доставки." if status == "failed" else ""
    row.save(update_fields=["external_id", "status", "error"])
    if status != "failed" and not row.automated:
        Conversation.objects.filter(
            id=row.conversation_id, waiting_since__lte=row.created_at
        ).update(waiting_since=None)
    return True


@transaction.atomic
def process_event(digest):
    event = WebhookEvent.objects.select_for_update().get(digest=digest)
    if event.processed_at:
        return
    if event.payload.get("object") == "instagram":
        from tapme.messaging.infrastructure.instagram_events import process_instagram

        process_instagram(event)
        event.processed_at = timezone.now()
        event.error = ""
        event.save(update_fields=["processed_at", "error"])
        return
    for entry in event.payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue
            value = change.get("value", {})
            accounts = (
                ChannelAccount.objects.filter(id=event.channel_id)
                if event.channel_id
                else ChannelAccount.objects.filter(app_secret_encrypted="")
            )
            channel = (
                accounts.select_for_update()
                .filter(
                    kind="whatsapp",
                    phone_number_id=value.get("metadata", {}).get("phone_number_id"),
                    status="active",
                )
                .first()
            )
            if not channel:
                continue
            names = {
                c.get("wa_id"): str(c.get("profile", {}).get("name", ""))
                for c in value.get("contacts", [])
            }
            for message in value.get("messages", []):
                incoming(channel, message, names)
            for status in value.get("statuses", []):
                if delivery_status(
                    channel, status
                ) is False and timezone.now() - event.received_at < timedelta(minutes=5):
                    raise PendingReceipt
            channel.last_webhook_at = timezone.now()
            channel.save(update_fields=["last_webhook_at"])
    event.processed_at = timezone.now()
    event.error = ""
    event.save(update_fields=["processed_at", "error"])


def deliver(message_id, gateway, storage=None):
    with transaction.atomic():
        row = (
            Message.objects.select_for_update(of=("self",))
            .select_related("conversation__channel")
            .get(id=message_id)
        )
        if row.status != "queued":
            return
        chat, channel = row.conversation, row.conversation.channel
        error = ""
        if channel.status != "active" or not channel.token_encrypted:
            error = "Канал отключён."
        elif (
            not row.automated
            and not Membership.objects.filter(
                user_id=row.sender_id,
                business_id=channel.business_id,
                is_active=True,
                user__is_active=True,
                role__in=["owner", "manager"],
            ).exists()
        ):
            error = "У сотрудника больше нет доступа к отправке."
        elif chat.opted_out or chat.needs_customer_link or chat.mode == "closed":
            error = "Отправка в этот диалог приостановлена."
        elif not reply_allowed(chat.last_inbound_at, timezone.now()):
            error = "Окно ответа 24 часа истекло. Дождитесь нового сообщения клиента."
        if error:
            row.status, row.error = "failed", error
            row.save(update_fields=["status", "error"])
            return
        try:
            token = decrypt(channel.token_encrypted)
        except InvalidInput as exc:
            row.status, row.error = "failed", str(exc)
            row.save(update_fields=["status", "error"])
            return
        row.status, row.sending_at = "sending", timezone.now()
        row.save(update_fields=["status", "sending_at"])
    payload = {
        "messaging_product": "whatsapp",
        "to": chat.phone.lstrip("+"),
        "type": "text",
        "text": {"body": row.text, "preview_url": False},
        "biz_opaque_callback_data": str(row.delivery_key),
    }
    if row.context_id:
        payload["context"] = {"message_id": row.context_id}
    try:
        if gateway is None:
            gateway = gateway_for(channel)
        if row.media_key and channel.kind == "instagram":
            raise DeliveryRejected(
                "Вложения Instagram пока отправляются через приложение Instagram."
            )
        if row.media_key:
            try:
                media_id = gateway.upload(
                    channel.phone_number_id, token, storage.read(row.media_key), row.media_type
                )
            except (DeliveryUnknown, InvalidInput, NotFound, OSError):
                # Media upload alone does not send anything to the customer.
                raise DeliveryRejected(
                    "Не удалось загрузить вложение в WhatsApp. Можно повторить."
                ) from None
            payload.pop("text")
            payload["type"] = row.kind
            payload[row.kind] = {"id": media_id, **({"caption": row.text} if row.text else {})}
            if row.kind == "document":
                payload[row.kind]["filename"] = row.media_name
        if channel.kind == "instagram":
            if row.media_key or len(row.text.encode("utf-8")) > 1000:
                raise DeliveryRejected("Instagram: отправьте текст длиной до 1000 байт UTF-8.")
            payload = {"recipient": {"id": chat.external_user_id}, "message": {"text": row.text}}
            if row.context_id:
                payload["reply_to"] = {"mid": row.context_id}
        external = gateway.send(
            channel.ig_user_id if channel.kind == "instagram" else channel.phone_number_id,
            token,
            payload,
        )
        status, error = "sent", ""
    except DeliveryRejected as exc:
        status, error, external = "failed", str(exc), None
    except (DeliveryUnknown, OSError):
        status, error, external = (
            "unknown",
            "Не удалось подтвердить отправку. Автоматического повтора не будет.",
            None,
        )
    with transaction.atomic():
        current = Message.objects.select_for_update().get(id=message_id)
        # A delivery webhook may arrive before the HTTP response.
        if current.status in {"sending", "unknown"}:
            current.status, current.error = status, error
            current.external_id = external
            current.save(update_fields=["status", "error", "external_id"])
        if status == "sent" and not row.automated:
            Conversation.objects.filter(id=chat.id, waiting_since__lte=row.created_at).update(
                waiting_since=None
            )


@transaction.atomic
def fetch_attachment(message_id, gateway, storage):
    row = (
        Message.objects.select_for_update(of=("self",))
        .select_related("conversation__channel")
        .get(id=message_id)
    )
    if row.media_key or row.payload.get("download_attempts", 0) >= 3:
        return
    channel = row.conversation.channel
    if channel.status != "active":
        return
    try:
        if gateway is None:
            gateway = gateway_for(channel)
        content, mime = gateway.download(
            channel.phone_number_id,
            decrypt(channel.token_encrypted),
            str(row.payload.get("id", "")),
        )
        key, mime = storage.save(
            f"{channel.business_id}/chats/{row.conversation_id}/{row.request_id}", content, mime
        )
        row.media_key, row.media_type = key, mime
        row.media_name = str(row.payload.get("filename", "Вложение"))[:150]
        row.error = ""
    except (DeliveryRejected, DeliveryUnknown, InvalidInput, OSError):
        row.payload["download_attempts"] = row.payload.get("download_attempts", 0) + 1
        row.error = "Вложение пока недоступно. Поддерживаются фото, PDF, аудио и MP4 до 16 МБ."
    row.save(update_fields=["media_key", "media_type", "media_name", "error", "payload"])
