from django.db import transaction
from django.utils import timezone

from tapme.feedback.models import FeedbackRecord
from tapme.orders.infrastructure.repository import DjangoOrderRepository
from tapme.shared.domain import NotFound


class DjangoFeedbackRepository:
    def list(self, business_id, order_id):
        DjangoOrderRepository().get(business_id, order_id)
        return list(
            FeedbackRecord.objects.filter(business_id=business_id, order_id=order_id)
            .order_by("-created_at")
            .values()
        )

    def create(self, business_id, order_id, actor_id, kind, message, rating):
        with transaction.atomic():
            order = DjangoOrderRepository().lock(business_id, order_id)
            row = FeedbackRecord.objects.create(
                business_id=business_id,
                order_id=order_id,
                actor_id=actor_id,
                kind=kind,
                message=message,
                rating=rating,
                status="open" if kind == "complaint" else "resolved",
            )
            if actor_id:
                DjangoOrderRepository().event(order, actor_id, kind, message, timezone.now())
        return FeedbackRecord.objects.filter(id=row.id).values().get()

    def resolve(self, business_id, feedback_id, outcome, actor_id):
        with transaction.atomic():
            row = (
                FeedbackRecord.objects.select_for_update()
                .filter(business_id=business_id, id=feedback_id)
                .first()
            )
            if row is None:
                raise NotFound("Обращение не найдено.")
            row.status, row.outcome, row.resolved_at = "resolved", outcome, timezone.now()
            row.save(update_fields=["status", "outcome", "resolved_at"])
            order = DjangoOrderRepository().get(business_id, row.order_id)
            DjangoOrderRepository().event(
                order, actor_id, "complaint_resolved", outcome, timezone.now()
            )
