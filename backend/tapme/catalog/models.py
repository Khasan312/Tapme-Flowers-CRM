import uuid

from django.db import models


class ProductRecord(models.Model):
    system_kind = models.CharField(max_length=30, blank=True, default="", db_default="")
    active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    photo_key = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business", "system_kind"],
                condition=~models.Q(system_kind=""),
                name="unique_system_product",
            ),
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="product_price_nonnegative"
            ),
        ]
        indexes = [models.Index(fields=["business", "name", "id"])]
