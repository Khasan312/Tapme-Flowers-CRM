from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from tapme.messaging.infrastructure.meta import decrypt, gateway_for
from tapme.messaging.infrastructure.processing import (
    PendingReceipt,
    deliver,
    delivery_status,
    fetch_attachment,
    process_event,
)
from tapme.messaging.infrastructure.storage import DjangoAttachmentStorage
from tapme.messaging.models import Conversation, Message, WebhookEvent


@shared_task
def process_messages():
    # Database inbox/outbox survives Redis failures and worker restarts.
    for key in (
        WebhookEvent.objects.filter(processed_at=None, attempts__lt=5)
        .order_by("received_at")
        .values_list("digest", flat=True)[:100]
    ):
        try:
            process_event(key)
        except PendingReceipt:
            continue
        except Exception:
            WebhookEvent.objects.filter(digest=key).update(
                attempts=F("attempts") + 1,
                error="Не удалось обработать событие. Требуется проверка сервера.",
            )
    Message.objects.filter(
        status="sending", sending_at__lt=timezone.now() - timedelta(minutes=2)
    ).update(
        status="unknown",
        error="Отправка прервалась. Ожидаем подтверждения WhatsApp; автоматического повтора не будет.",
    )
    for message_id in (
        Message.objects.filter(status="queued").order_by("id").values_list("id", flat=True)[:100]
    ):
        deliver(message_id, None, DjangoAttachmentStorage())
    for message_id in (
        Message.objects.filter(
            direction="in",
            kind__in=["image", "document", "video", "audio", "sticker"],
            media_key="",
        )
        .filter(Q(payload__download_attempts__isnull=True) | Q(payload__download_attempts__lt=3))
        .order_by("id")
        .values_list("id", flat=True)[:10]
    ):
        fetch_attachment(message_id, None, DjangoAttachmentStorage())
    WebhookEvent.objects.filter(
        processed_at__isnull=False, received_at__lt=timezone.now() - timedelta(days=30)
    ).delete()

    for chat in (
        Conversation.objects.filter(channel__status="active")
        .exclude(provider_read_message_id=0)
        .exclude(provider_read_message_id=F("provider_read_sent_id"))
        .select_related("channel")[:100]
    ):
        try:
            gateway_for(chat.channel).mark_read(
                chat.channel.phone_number_id,
                decrypt(chat.channel.token_encrypted),
                Message.objects.get(
                    id=chat.provider_read_message_id, conversation=chat
                ).external_id,
            )
            Conversation.objects.filter(
                id=chat.id, provider_read_sent_id__lt=chat.provider_read_message_id
            ).update(provider_read_sent_id=chat.provider_read_message_id)
        except Exception:
            continue  # Read receipts are idempotent and can be retried on the next tick.
    if settings.TAPME_META_MODE == "fake":
        for row in Message.objects.filter(
            conversation__channel__provider_mode="fake",
            status__in=["sent", "delivered"],
            sending_at__lt=timezone.now() - timedelta(seconds=1),
        ).select_related("conversation__channel")[:100]:
            with transaction.atomic():
                delivery_status(
                    row.conversation.channel,
                    {
                        "id": row.external_id,
                        "status": "read" if row.status == "delivered" else "delivered",
                    },
                )
