from django.db.models import Max, Sum

from tapme.customers.infrastructure.repository import DjangoCustomerRepository
from tapme.feedback.models import FeedbackRecord
from tapme.orders.models import OrderRecord
from tapme.reminders.models import ReminderRecord


class DjangoActivityReader:
    def get(self, business_id, customer_id):
        DjangoCustomerRepository().get(business_id, customer_id)
        orders = OrderRecord.objects.filter(
            business_id=business_id, customer_id=customer_id
        ).order_by("-created_at")
        feedback = FeedbackRecord.objects.filter(
            business_id=business_id, order__customer_id=customer_id
        ).order_by("-created_at")
        messages = ReminderRecord.objects.filter(
            business_id=business_id, customer_id=customer_id
        ).order_by("-created_at")
        return dict(
            order_count=orders.count(),
            total=str(
                orders.exclude(status="cancelled").aggregate(value=Sum("total"))["value"] or 0
            ),
            last_order=orders.aggregate(value=Max("delivery_date"))["value"],
            orders=list(
                orders.values("id", "number", "status", "total", "delivery_date", "recipient_name")[
                    :50
                ]
            ),
            feedback=list(
                feedback.values(
                    "id", "message", "kind", "rating", "status", "outcome", "created_at"
                )[:50]
            ),
            reminders=list(
                messages.values("id", "state", "event", "message", "acted_at", "due_date")[:50]
            ),
        )
