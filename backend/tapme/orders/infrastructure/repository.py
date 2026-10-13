import re
from dataclasses import fields
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models import Q

from tapme.businesses.application.contracts import Role
from tapme.businesses.models import Membership
from tapme.orders.domain import Fulfillment, Order, OrderLine
from tapme.orders.models import OrderCounter, OrderEvent, OrderLineRecord, OrderRecord
from tapme.payments.infrastructure.repository import DjangoPaymentRepository
from tapme.shared.domain import NotFound, Page


def to_domain(row):
    values = {
        field.name: getattr(row, "created_by_id" if field.name == "created_by" else field.name)
        for field in fields(Order)
        if field.name not in {"lines", "fulfillment", "paid_amount"}
    }
    return Order(
        **values,
        fulfillment=Fulfillment(row.fulfillment),
        paid_amount=sum(
            (p.amount if p.kind == "payment" else -p.amount for p in row.payments.all()),
            Decimal("0.00"),
        ),
        lines=tuple(
            OrderLine(line.product_id, line.name, line.unit_price, line.quantity)
            for line in row.lines.all()
        ),
    )


class DjangoOrderRepository:
    def lock_staff(self, business_id, user_id):
        Membership.objects.select_for_update().filter(
            business_id=business_id, user_id=user_id
        ).first()

    def lock_business(self, business_id):
        OrderCounter.objects.get_or_create(business_id=business_id)
        OrderCounter.objects.select_for_update().get(business_id=business_id)

    def next_number(self, business_id):
        counter = OrderCounter.objects.get(business_id=business_id)
        counter.value += 1
        counter.save(update_fields=["value"])
        return counter.value

    def by_request(self, business_id, key):
        row = (
            OrderRecord.objects.filter(business_id=business_id, request_key=key)
            .prefetch_related("lines", "payments")
            .first()
        )
        return to_domain(row) if row else None

    def add(self, order):
        values = {
            field.name: getattr(order, field.name)
            for field in fields(Order)
            if field.name not in {"lines", "paid_amount"}
        }
        values["created_by_id"] = values.pop("created_by")
        row = OrderRecord.objects.create(**values, total=order.total)
        OrderLineRecord.objects.bulk_create(
            [
                OrderLineRecord(
                    order=row,
                    product_id=line.product_id,
                    name=line.name,
                    unit_price=line.unit_price,
                    quantity=line.quantity,
                    position=index,
                )
                for index, line in enumerate(order.lines)
            ]
        )
        OrderEvent.objects.create(
            order=row, actor_id=order.created_by, kind="created", created_at=order.created_at
        )

    def get(self, business_id, order_id):
        row = (
            OrderRecord.objects.filter(business_id=business_id, id=order_id)
            .prefetch_related("lines", "payments")
            .first()
        )
        if row is None:
            raise NotFound("Заказ не найден.")
        return to_domain(row)

    def list(self, business_id, day, limit, offset, search="", status="", customer_id=None):
        query = OrderRecord.objects.filter(business_id=business_id)
        if day:
            query = query.filter(delivery_date=day)
        if status:
            query = query.filter(status=status)
        if customer_id:
            query = query.filter(customer_id=customer_id)
        if search:
            query = query.filter(id__in=self.search_ids(business_id, search))
        query = query.order_by("-created_at", "-id").prefetch_related("lines", "payments")
        return Page(tuple(to_domain(row) for row in query[offset : offset + limit]), query.count())

    def search_ids(self, business_id, search):
        query = OrderRecord.objects.filter(business_id=business_id)
        if search:
            match = (
                Q(customer_name__icontains=search)
                | Q(customer_phone__icontains=search)
                | Q(recipient_name__icontains=search)
                | Q(recipient_phone__icontains=search)
                | Q(address__icontains=search)
                | Q(lines__name__icontains=search)
            )
            digits = re.sub(r"\D", "", search)
            if len(digits) >= 3:
                match |= Q(customer_phone__contains=digits) | Q(recipient_phone__contains=digits)
            number = search.upper().removeprefix("TF-").lstrip("№# ")
            if number.isdigit() and len(number) < 10:
                match |= Q(number=int(number))
            try:
                match |= Q(id=UUID(search)) | Q(customer_id=UUID(search))
            except ValueError:
                pass
            query = query.filter(match).distinct()
        return query.values("id")

    def lock(self, business_id, order_id):
        row = (
            OrderRecord.objects.select_for_update()
            .filter(business_id=business_id, id=order_id)
            .first()
        )
        if row is None:
            raise NotFound("Заказ не найден.")
        return to_domain(row)

    def save(self, order, actor_id, kind, detail, now):
        values = {
            f.name: getattr(order, f.name)
            for f in fields(Order)
            if f.name not in {"lines", "id", "created_by", "paid_amount"}
        }
        OrderRecord.objects.filter(business_id=order.business_id, id=order.id).update(
            **values, total=order.total
        )
        OrderLineRecord.objects.filter(order_id=order.id).delete()
        OrderLineRecord.objects.bulk_create(
            [
                OrderLineRecord(
                    order_id=order.id,
                    product_id=line.product_id,
                    name=line.name,
                    unit_price=line.unit_price,
                    quantity=line.quantity,
                    position=i,
                )
                for i, line in enumerate(order.lines)
            ]
        )
        self.event(order, actor_id, kind, detail, now)

    def event(self, order, actor_id, kind, detail, now):
        OrderEvent.objects.create(
            order_id=order.id, actor_id=actor_id, kind=kind, detail=detail, created_at=now
        )

    def tasks(self, scope, role, day, limit, offset):
        query = OrderRecord.objects.filter(business_id=scope.business_id)
        if role == Role.FLORIST:
            query = query.filter(Q(florist_id=scope.user_id) | Q(florist_id=None, status="new"))
        elif role == Role.COURIER:
            query = query.filter(courier_id=scope.user_id)
        else:
            query = query.filter(fulfillment="courier")
        if day:
            query = query.filter(delivery_date=day)
        query = query.order_by("delivery_date", "window_start", "number").prefetch_related(
            "lines", "payments"
        )
        return Page(tuple(to_domain(r) for r in query[offset : offset + limit]), query.count())

    def history(self, business_id, order_id):
        return list(
            OrderEvent.objects.filter(order__business_id=business_id, order_id=order_id)
            .order_by("created_at", "id")
            .values("id", "kind", "detail", "created_at", "actor__username")
        )


class DjangoUnitOfWork:
    def after_commit(self, callback):
        transaction.on_commit(callback, robust=True)

    def __enter__(self):
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        self.orders = DjangoOrderRepository()
        self.payments = DjangoPaymentRepository()
        from tapme.orders.infrastructure.delivery import DjangoDeliverySlots

        self.delivery = DjangoDeliverySlots()
        from tapme.media.infrastructure.repository import DjangoPhotoRepository

        self.photos = DjangoPhotoRepository()
        return self

    def __exit__(self, kind, error, traceback):
        self._atomic.__exit__(kind, error, traceback)
