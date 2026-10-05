import uuid

from django.db import models


class ProductRecord(models.Model):
    active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="product_price_nonnegative"
            )
        ]
        indexes = [models.Index(fields=["business", "name", "id"])]
