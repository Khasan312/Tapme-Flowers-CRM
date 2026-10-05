from django.db import transaction
from django.utils import timezone

from tapme.businesses.models import Shop
from tapme.feedback.infrastructure.repository import DjangoFeedbackRepository
from tapme.feedback.models import FeedbackRecord
from tapme.orders.infrastructure.repository import DjangoOrderRepository
from tapme.orders.models import OrderRecord
from tapme.shared.domain import Conflict, InvalidInput, NotFound


class DjangoPublicOrderRepository:
    def set_token(self, scope, order_id, digest):
        with transaction.atomic():
            order = DjangoOrderRepository().lock(scope.business_id, order_id)
            OrderRecord.objects.filter(id=order.id, business_id=scope.business_id).update(
                public_token_hash=digest
            )
            DjangoOrderRepository().event(
                order,
                scope.user_id,
                "public_link",
                "Ссылка отозвана" if not digest else "Выпущена новая ссылка",
                timezone.now(),
            )

    def get_public(self, digest):
        row = OrderRecord.objects.filter(public_token_hash=digest).first()
        if row is None:
            raise NotFound("Ссылка недействительна или отозвана.")
        shop = Shop.objects.get(business_id=row.business_id)
        return dict(
            number=row.number,
            status=row.status,
            delivery_date=row.delivery_date,
            window_start=row.window_start,
            window_end=row.window_end,
            fulfillment=row.fulfillment,
            shop_name=shop.name,
            shop_phone=shop.phone,
            can_review=row.status == "done"
            and not FeedbackRecord.objects.filter(order=row, actor=None).exists(),
        )

    def feedback(self, digest, message, rating):
        with transaction.atomic():
            row = OrderRecord.objects.select_for_update().filter(public_token_hash=digest).first()
            if row is None:
                raise NotFound("Ссылка недействительна или отозвана.")
            if row.status != "done":
                raise InvalidInput("Отзыв доступен после вручения.")
            if FeedbackRecord.objects.filter(order=row, actor=None).exists():
                raise Conflict("Спасибо, отзыв уже записан.")
            DjangoFeedbackRepository().create(
                row.business_id,
                row.id,
                None,
                "complaint" if rating <= 2 else "review",
                message or f"Оценка {rating}/5",
                rating,
            )
