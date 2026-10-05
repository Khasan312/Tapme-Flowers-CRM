from dataclasses import asdict, fields
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum

from tapme.payments.domain import Payment
from tapme.payments.models import PaymentRecord
from tapme.shared.domain import Conflict


def to_domain(row):
    return Payment(**{f.name: getattr(row, f.name) for f in fields(Payment)})


class DjangoPaymentRepository:
    def balance(self, business_id, order_id):
        rows = (
            PaymentRecord.objects.filter(business_id=business_id, order_id=order_id)
            .values("kind")
            .annotate(total=Sum("amount"))
        )
        return sum(
            (r["total"] * (1 if r["kind"] == "payment" else -1) for r in rows), Decimal("0.00")
        )

    def by_request(self, business_id, key):
        row = PaymentRecord.objects.filter(business_id=business_id, request_key=key).first()
        return to_domain(row) if row else None

    def add(self, payment):
        try:
            with transaction.atomic():
                PaymentRecord.objects.create(**asdict(payment))
        except IntegrityError:
            raise Conflict("Ключ операции уже использован. Обновите историю оплат.") from None

    def list(self, business_id, order_id):
        return tuple(
            to_domain(r)
            for r in PaymentRecord.objects.filter(
                business_id=business_id, order_id=order_id
            ).order_by("created_at", "id")
        )
