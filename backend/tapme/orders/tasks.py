from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from tapme.messaging.models import Conversation, Message
from tapme.orders.infrastructure.repository import DjangoOrderRepository
from tapme.orders.models import OfficeTask, OrderDraft, OrderEvent, OrderRecord


@shared_task
def extract_order_drafts():
    from django.conf import settings

    from tapme.orders.infrastructure.extraction import process_draft

    if not settings.TAPME_AI_ENABLED:
        return
    for draft_id in (
        OrderDraft.objects.filter(status="active", extraction_actor__isnull=False)
        .values_list("id", flat=True)
        .iterator(chunk_size=100)
    ):
        process_draft(draft_id)


@shared_task
def maintain_order_drafts():
    from dataclasses import replace

    now = timezone.now()
    OrderDraft.objects.filter(status="active", updated_at__lt=now - timedelta(hours=72)).update(
        status="abandoned", version=F("version") + 1
    )
    for order_id, business_id in (
        OrderRecord.objects.filter(status="pending", payment_due_at__lte=now)
        .values_list("id", "business_id")
        .iterator(chunk_size=200)
    ):
        with transaction.atomic():
            draft = OrderDraft.objects.filter(order_id=order_id).first()
            if draft:
                # Inbound messages and conversion also lock the conversation first.
                Conversation.objects.select_for_update().get(id=draft.conversation_id)
            repository = DjangoOrderRepository()
            order = repository.lock(business_id, order_id)
            if order.status != "pending" or not order.payment_due_at or order.payment_due_at > now:
                continue
            # Before receipt review is implemented, any new image/document may be a receipt.
            possible_receipt = (
                draft
                and Message.objects.filter(
                    conversation_id=draft.conversation_id,
                    direction="in",
                    kind__in=["image", "document"],
                    created_at__gte=order.created_at,
                ).exists()
            )
            if order.paid_amount > 0 or possible_receipt:
                if not OrderEvent.objects.filter(
                    order_id=order.id, kind="payment_deadline_review"
                ).exists():
                    repository.event(
                        order,
                        order.created_by,
                        "payment_deadline_review",
                        "Срок оплаты прошёл; есть оплата или возможный чек. Требуется решение менеджера.",
                        now,
                    )
                    OfficeTask.objects.create(
                        business_id=business_id,
                        created_by_id=order.created_by,
                        content=f"Проверить оплату и срок заказа №{order.number}: есть платёж или вложение клиента",
                    )
                continue
            changed = replace(
                order,
                status="cancelled",
                version=order.version + 1,
                cancellation_reason="Не оплачен вовремя",
            )
            repository.save(
                changed,
                order.created_by,
                "cancelled",
                "Не оплачен вовремя · автоматическая отмена",
                now,
            )
            if draft:
                Message.objects.create(
                    conversation_id=draft.conversation_id,
                    direction="system",
                    kind="order",
                    status="received",
                    text=f"Заказ №{order.number} отменён: не оплачен вовремя",
                    payload={"order_id": str(order.id)},
                )
