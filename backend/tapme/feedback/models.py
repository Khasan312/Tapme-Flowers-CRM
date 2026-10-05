import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class FeedbackRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    order = models.ForeignKey(
        "orders.OrderRecord", on_delete=models.CASCADE, related_name="feedback"
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20)
    message = models.TextField()
    rating = models.PositiveSmallIntegerField(null=True)
    status = models.CharField(max_length=20, default="open")
    outcome = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True)
