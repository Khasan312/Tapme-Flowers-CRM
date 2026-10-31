from datetime import timedelta

from django.utils import timezone

from tapme.messaging.infrastructure.processing import PendingReceipt, instant
from tapme.messaging.models import ChannelAccount, Conversation, Message


def instagram_incoming(channel, event, received_at):
    message = event.get("message") or {}
    echo = message.get("is_echo") is True
    sender = str((event.get("sender") or {}).get("id", ""))
    recipient = str((event.get("recipient") or {}).get("id", ""))
    peer = recipient if echo else sender
    if (
        (sender if echo else recipient) != channel.ig_user_id
        or not peer.isdecimal()
        or not 1 <= len(peer) <= 80
        or peer == channel.ig_user_id
    ):
        return
    external = str(message.get("mid", ""))
    if not external or len(external) > 500:
        return
    existing = Message.objects.filter(conversation__channel=channel, external_id=external).first()
    if existing:
        if message.get("is_deleted"):
            existing.text = "Сообщение удалено в Instagram"
            existing.save(update_fields=["text"])
        return
    if (
        echo
        and Message.objects.filter(
            conversation__channel=channel,
            conversation__external_user_id=peer,
            external_id=None,
            direction="out",
            status__in=["sending", "unknown"],
        ).exists()
    ):
        # HTTP response may still assign this mid to an outgoing CRM message.
        if received_at > timezone.now() - timedelta(minutes=5):
            raise PendingReceipt
        # An ambiguous send cannot safely be correlated by text. Keep its
        # unknown status rather than importing a possible duplicate as a new send.
        return
    chat, _ = Conversation.objects.get_or_create(
        channel=channel,
        external_user_id=peer,
        defaults={"phone": "", "profile_name": "Instagram · " + peer[-6:]},
    )
    chat = Conversation.objects.select_for_update().get(id=chat.id)
    had_messages = chat.messages.exists()
    text = str(message.get("text") or "")[:4096]
    if not text:
        text = (
            "Вложение Instagram — откройте его в приложении Instagram"
            if message.get("attachments")
            else "Сообщение Instagram неподдерживаемого типа"
        )
    if message.get("is_deleted"):
        text = "Сообщение удалено в Instagram"
    try:
        when = instant(int(event.get("timestamp")) // 1000)
    except (TypeError, ValueError):
        when = instant(None)
    Message.objects.create(
        conversation=chat,
        external_id=external,
        direction="out" if echo else "in",
        kind="text" if message.get("text") else "unsupported",
        text=text,
        payload=message,
        status="sent" if echo else "received",
        happened_at=when,
        context_id=str((message.get("reply_to") or {}).get("mid", ""))[:500],
    )
    if not had_messages or when >= chat.last_message_at:
        chat.last_message_at = when
        chat.last_message_preview = text[:160]
    if not echo:
        chat.last_inbound_at = max(chat.last_inbound_at or when, when)
        chat.waiting_since = chat.waiting_since or timezone.now()
        chat.mode = "human"
        if text.strip().casefold() in {"стоп", "stop", "отписаться", "не пишите", "не пишите мне"}:
            chat.opted_out = True
        channel.last_inbound_at = timezone.now()
        channel.save(update_fields=["last_inbound_at"])
    chat.version += 1
    chat.save()


def process_instagram(event):
    channel = (
        ChannelAccount.objects.select_for_update()
        .filter(id=event.channel_id, kind="instagram", status="active")
        .first()
    )
    if not channel:
        return
    for entry in event.payload.get("entry", []):
        if str(entry.get("id")) != channel.ig_user_id:
            continue
        for item in entry.get("messaging", []):
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("message"), dict):
                instagram_incoming(channel, item, event.received_at)
            elif isinstance(item.get("read"), dict):
                peer = str((item.get("sender") or {}).get("id", ""))
                if str((item.get("recipient") or {}).get("id", "")) != channel.ig_user_id:
                    continue
                qs = Message.objects.filter(
                    conversation__channel=channel,
                    conversation__external_user_id=peer,
                    direction="out",
                    status__in=["sent", "delivered", "unknown"],
                )
                mid = str(item["read"].get("mid", ""))
                if mid:
                    qs.filter(external_id=mid).update(status="read", error="")
                # Without a message ID, never guess which messages were read.
        channel.last_webhook_at = timezone.now()
        channel.save(update_fields=["last_webhook_at"])
