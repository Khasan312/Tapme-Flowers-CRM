from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Count, DecimalField, IntegerField, Max, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce

from tapme.businesses.models import Business
from tapme.customers.infrastructure.repository import DjangoCustomerRepository
from tapme.customers.models import CustomerRecord
from tapme.orders.models import OrderRecord
from tapme.reminders.domain import event_day


class DjangoDirectoryReader:
    def list(self, business_id, search, group, limit, offset, now):
        today = now.astimezone(ZoneInfo(Business.objects.get(id=business_id).timezone)).date()
        orders = (
            OrderRecord.objects.filter(business_id=business_id, customer_id=OuterRef("id"))
            .exclude(status="cancelled")
            .values("customer_id")
            .annotate(count=Count("id"), total=Sum("total"), last=Max("delivery_date"))
        )
        query = (
            DjangoCustomerRepository()
            .search(business_id, search)
            .annotate(
                order_count=Coalesce(
                    Subquery(orders.values("count")), 0, output_field=IntegerField()
                ),
                total=Coalesce(
                    Subquery(orders.values("total")), Decimal("0"), output_field=DecimalField()
                ),
                last_order=Subquery(orders.values("last")),
            )
        )
        if group == "vip":
            query = query.filter(tags__contains=["VIP"])
        elif group == "corp":
            query = query.filter(tags__contains=["Корпоративный"])
        elif group == "vip_corp":
            query = query.filter(tags__contains=["VIP", "Корпоративный"])
        elif group == "new":
            query = query.filter(created_at__gte=now - timedelta(days=30))
        elif group == "lapsed":
            query = query.filter(last_order__lte=today - timedelta(days=90))
        count = query.count()
        rows = []
        for c in query.order_by("-created_at", "id").prefetch_related("recipients", "dates")[
            offset : offset + limit
        ]:
            dates = sorted([(event_day(today, d.month, d.day), d.label) for d in c.dates.all()])
            rows.append(
                dict(
                    id=c.id,
                    code=c.code,
                    name=c.name,
                    phone=c.phone,
                    additional_phones=c.additional_phones,
                    source=c.source,
                    tags=c.tags,
                    consent=c.consent,
                    recipients=[dict(name=r.name, relation=r.relation) for r in c.recipients.all()],
                    next_date=dict(label=dates[0][1], days=(dates[0][0] - today).days)
                    if dates
                    else None,
                    order_count=c.order_count,
                    total=str(c.total),
                    last_order=c.last_order,
                    days_since=(today - c.last_order).days if c.last_order else None,
                )
            )
        all_customers = CustomerRecord.objects.filter(business_id=business_id)
        return dict(
            count=count,
            results=rows,
            total_count=all_customers.count(),
            consent_count=all_customers.filter(consent=True).count(),
        )
