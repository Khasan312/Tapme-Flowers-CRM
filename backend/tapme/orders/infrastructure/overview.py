from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Sum
from django.utils import timezone

from tapme.businesses.models import Business
from tapme.feedback.models import FeedbackRecord
from tapme.orders.application.overview import delivered_on_time
from tapme.orders.models import OrderRecord
from tapme.payments.models import PaymentRecord
from tapme.reminders.models import ReminderRecord


class DjangoOverviewReader:
    def overview(self, business_id, day):
        orders = OrderRecord.objects.filter(business_id=business_id)
        if day:
            orders = orders.filter(delivery_date=day)
        payments = PaymentRecord.objects.filter(
            business_id=business_id, order_id__in=orders.values("id")
        )
        zone = Business.objects.get(id=business_id).timezone
        delivered = list(
            orders.filter(
                fulfillment="courier", status="done", completed_at__isnull=False
            ).values_list("completed_at", "delivery_date", "window_end")
        )
        return dict(
            pending=OrderRecord.objects.filter(business_id=business_id, status="pending").count(),
            deliveries=orders.filter(fulfillment="courier")
            .exclude(status__in=["pending", "cancelled"])
            .count(),
            reminders=ReminderRecord.objects.filter(
                business_id=business_id,
                state="wait",
                due_date__lte=day or timezone.now().astimezone(ZoneInfo(zone)).date(),
            ).count(),
            deliveries_completed=len(delivered),
            deliveries_on_time=sum(
                delivered_on_time(completed, day, end, zone) for completed, day, end in delivered
            ),
            orders=orders.count(),
            completed=orders.filter(status="done").count(),
            in_progress=orders.exclude(status__in=["pending", "done", "cancelled"]).count(),
            total=orders.exclude(status__in=["pending", "cancelled"]).aggregate(total=Sum("total"))[
                "total"
            ]
            or Decimal(0),
            payments=payments.filter(kind="payment").aggregate(total=Sum("amount"))["total"]
            or Decimal(0),
            refunds=payments.filter(kind="refund").aggregate(total=Sum("amount"))["total"]
            or Decimal(0),
            complaints=FeedbackRecord.objects.filter(
                business_id=business_id,
                order_id__in=orders.values("id"),
                kind="complaint",
                status="open",
            ).count(),
        )
