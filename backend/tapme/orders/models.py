import uuid

from django.conf import settings
from django.db import models


class OfficeTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    point = models.ForeignKey("businesses.Shop", null=True, blank=True, on_delete=models.PROTECT)
    content = models.CharField(max_length=500)
    done = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class OrderCounter(models.Model):
    business = models.OneToOneField(
        "businesses.Business", primary_key=True, on_delete=models.PROTECT
    )
    value = models.PositiveIntegerField(default=0)


class OrderRecord(models.Model):
    point = models.ForeignKey("businesses.Shop", on_delete=models.PROTECT)
    prepayment_percent = models.PositiveSmallIntegerField(default=0, db_default=0)
    prepayment_required = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, db_default=0
    )
    payment_due_at = models.DateTimeField(null=True, blank=True)
    occasion = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=80, blank=True)
    relation = models.CharField(max_length=80, blank=True)
    id = models.UUIDField(primary_key=True, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    customer = models.ForeignKey("customers.CustomerRecord", on_delete=models.PROTECT)
    customer_name = models.CharField(max_length=150)
    customer_phone = models.CharField(max_length=16)
    recipient_name = models.CharField(max_length=150)
    recipient_phone = models.CharField(max_length=16, blank=True)
    fulfillment = models.CharField(max_length=20)
    delivery_date = models.DateField()
    window_start = models.TimeField()
    window_end = models.TimeField()
    address = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    card = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="new")
    version = models.PositiveIntegerField(default=1)
    florist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="florist_orders",
    )
    courier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="courier_orders",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=1000, blank=True)
    delivery_issue = models.CharField(max_length=1000, blank=True)
    public_token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField()
    request_key = models.UUIDField()
    request_hash = models.CharField(max_length=64)

    def save(self, *args, **kwargs):
        # Older internal callers may omit the point only for a single-point company.
        if not self.point_id:
            from tapme.businesses.models import Shop

            self.point = Shop.objects.get(business_id=self.business_id, active=True)
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business", "number"], name="unique_order_number_per_business"
            ),
            models.UniqueConstraint(
                fields=["business", "request_key"], name="unique_order_request_per_business"
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=0), name="order_total_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(window_end__gt=models.F("window_start")),
                name="order_window_increasing",
            ),
            models.CheckConstraint(
                condition=models.Q(fulfillment__in=["pickup", "courier"]), name="valid_fulfillment"
            ),
        ]
        indexes = [models.Index(fields=["business", "delivery_date", "created_at"])]


class OrderLineRecord(models.Model):
    order = models.ForeignKey(OrderRecord, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("catalog.ProductRecord", on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1, quantity__lte=999), name="valid_line_quantity"
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0), name="line_price_nonnegative"
            ),
            models.UniqueConstraint(fields=["order", "product"], name="unique_product_per_order"),
        ]


class OrderEvent(models.Model):
    order = models.ForeignKey(OrderRecord, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=40)
    created_at = models.DateTimeField()
    detail = models.TextField(blank=True)


class OrderDraft(models.Model):
    extraction_actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    extraction_state = models.JSONField(default=dict, db_default={})
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    conversation = models.ForeignKey("messaging.Conversation", on_delete=models.CASCADE)
    customer = models.ForeignKey("customers.CustomerRecord", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default="active")
    fields = models.JSONField(default=dict)
    field_meta = models.JSONField(default=dict)
    order = models.OneToOneField(OrderRecord, null=True, blank=True, on_delete=models.SET_NULL)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation"],
                condition=models.Q(status="active"),
                name="one_active_order_draft",
            ),
        ]
        indexes = [models.Index(fields=["business", "status", "updated_at"])]
