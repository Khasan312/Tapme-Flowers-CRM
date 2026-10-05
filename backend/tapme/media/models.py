from django.conf import settings
from django.db import models


class PhotoRecord(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    order = models.ForeignKey("orders.OrderRecord", on_delete=models.CASCADE, related_name="photos")
    key = models.CharField(max_length=400, unique=True)
    kind = models.CharField(max_length=20)
    created_at = models.DateTimeField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
