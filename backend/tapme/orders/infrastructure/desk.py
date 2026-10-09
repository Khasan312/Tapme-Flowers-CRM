from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Case, Count, DecimalField, F, OuterRef, Q, Subquery, Sum, When
from django.db.models.functions import Coalesce

from tapme.businesses.models import Business
from tapme.feedback.models import FeedbackRecord
from tapme.orders.infrastructure.repository import DjangoOrderRepository, to_domain
from tapme.orders.models import OfficeTask, OrderRecord
from tapme.payments.models import PaymentRecord
from tapme.shared.domain import NotFound


class DjangoOrderDesk:
    def read(self, business_id, scope, day, search, status, limit, offset, now):
        local = now.astimezone(ZoneInfo(Business.objects.get(id=business_id).timezone))
        today, tomorrow = local.date(), local.date() + timedelta(days=1)
        balance = (
            PaymentRecord.objects.filter(order_id=OuterRef("id"), business_id=business_id)
            .values("order_id")
            .annotate(
                value=Sum(
                    Case(
                        When(kind="payment", then=F("amount")),
                        default=-F("amount"),
                        output_field=DecimalField(),
                    )
                )
            )
            .values("value")
        )
        all_orders = OrderRecord.objects.filter(business_id=business_id).annotate(
            balance=Coalesce(Subquery(balance), Decimal("0"), output_field=DecimalField())
        )
        filters = {
            "today": Q(delivery_date=today),
            "tomorrow": Q(delivery_date=tomorrow),
            "upcoming": Q(delivery_date__gt=today),
            "pickup": Q(fulfillment="pickup", delivery_date__gte=today),
            "unpaid": Q(balance__lt=F("total")) & ~Q(status__in=["done", "cancelled"]),
            "cancelled": Q(status="cancelled"),
            "all": Q(),
        }
        counts = {key: all_orders.filter(condition).count() for key, condition in filters.items()}
        query = (
            all_orders.filter(delivery_date=day)
            if scope == "date" and day
            else all_orders.filter(filters.get(scope, Q()))
        )
        if search:
            # Reuse the business-scoped search predicate, with no client-side truncation.
            query = query.filter(id__in=DjangoOrderRepository().search_ids(business_id, search))
        if status:
            if status == "courier":
                query = query.filter(fulfillment="courier")
            elif status == "build":
                query = query.filter(status__in=["new", "work"])
            elif status == "delivery":
                query = query.filter(status__in=["ready", "route"])
            elif status == "pickup":
                query = query.filter(fulfillment="pickup")
            else:
                query = query.filter(status=status)
        late = ~Q(status__in=["done", "cancelled"]) & (
            Q(delivery_date__lt=today)
            | Q(delivery_date=today, window_end__lt=local.time().replace(tzinfo=None))
        )
        summary = {
            "orders": query.count(),
            "done": query.filter(status="done").count(),
            "route": query.filter(status="route").count(),
            "build": query.filter(status__in=["new", "work"]).count(),
            "late": query.filter(late).count(),
            "total": str(
                query.exclude(status="cancelled").aggregate(value=Sum("total"))["value"]
                or Decimal("0.00")
            ),
        }
        tasks = []
        for order in (
            all_orders.exclude(status__in=["done", "cancelled"])
            .filter(
                Q(delivery_issue__gt="")
                | Q(florist_id=None)
                | Q(fulfillment="courier", courier_id=None)
                | Q(balance__lt=F("total"))
            )
            .order_by("delivery_date", "window_start")[:40]
        ):
            reason = order.delivery_issue or (
                "Назначить флориста"
                if not order.florist_id
                else "Назначить курьера"
                if order.fulfillment == "courier" and not order.courier_id
                else "Проверить оплату"
            )
            tasks.append(
                dict(
                    id=str(order.id),
                    order_id=str(order.id),
                    title=f"{reason} · №{order.number}",
                    subtitle=order.recipient_name,
                    tone="crit" if order.delivery_issue else "warn",
                )
            )
        for complaint in FeedbackRecord.objects.filter(
            business_id=business_id, kind="complaint", status="open"
        ).select_related("order")[:20]:
            tasks.insert(
                0,
                dict(
                    id=str(complaint.id),
                    order_id=str(complaint.order_id),
                    title=f"Разобрать жалобу · №{complaint.order.number}",
                    subtitle=complaint.message,
                    tone="crit",
                ),
            )
        calendar = list(
            query.values("delivery_date")
            .annotate(count=Count("id"), total=Sum("total"))
            .order_by("delivery_date")
        )
        return dict(
            count=summary["orders"],
            results=tuple(
                to_domain(row)
                for row in query.order_by(
                    "delivery_date", "window_start", "number"
                ).prefetch_related("lines", "payments")[offset : offset + limit]
            ),
            summary=summary,
            scopes=counts,
            tasks=tasks,
            calendar=calendar,
        )

    def notes(self, business_id):
        return list(
            OfficeTask.objects.filter(business_id=business_id, done=False)
            .order_by("created_at")
            .values("id", "content")
        )

    def add_note(self, scope, content):
        row = OfficeTask.objects.create(
            business_id=scope.business_id, created_by_id=scope.user_id, content=content
        )
        return dict(id=row.id, content=row.content)

    def complete_note(self, scope, note_id):
        if not OfficeTask.objects.filter(business_id=scope.business_id, id=note_id).update(
            done=True
        ):
            raise NotFound("Задача не найдена.")
