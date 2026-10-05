from django.conf import settings
from django.db import models


class PaymentRecord(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    order = models.ForeignKey(
        "orders.OrderRecord", on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    kind = models.CharField(max_length=20)
    method = models.CharField(max_length=20)
    note = models.CharField(max_length=1000, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField()
    request_key = models.UUIDField()
    request_hash = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business", "request_key"], name="unique_payment_request"
            ),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="positive_payment"),
            models.CheckConstraint(
                condition=models.Q(kind__in=["payment", "refund"]), name="valid_payment_kind"
            ),
        ]
