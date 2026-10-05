import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from tapme.reminders.domain import DEFAULT_TEMPLATE


def default_offsets():
    return [14, 7, 3, 1]


class ReminderSettings(models.Model):
    business = models.OneToOneField(
        "businesses.Business", primary_key=True, on_delete=models.CASCADE
    )
    enabled = models.BooleanField(default=True)
    offsets = models.JSONField(default=default_offsets)
    inactive_days = models.PositiveSmallIntegerField(default=90)
    start_hour = models.PositiveSmallIntegerField(default=9)
    end_hour = models.PositiveSmallIntegerField(default=20)
    templates = models.JSONField(default=dict)
    template = models.TextField(default=DEFAULT_TEMPLATE)
    inactive_template = models.TextField(
        default="{name}, здравствуйте! Давно не выбирали цветы у нас. Подобрать букет для вас? {shop}"
    )


class ReminderRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    customer = models.ForeignKey(
        "customers.CustomerRecord", on_delete=models.CASCADE, related_name="reminders"
    )
    key = models.CharField(max_length=200)
    event = models.CharField(max_length=200)
    person = models.CharField(max_length=150, blank=True)
    due_date = models.DateField()
    state = models.CharField(max_length=20, default="wait")
    message = models.TextField(blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    acted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "key"], name="unique_reminder_key")
        ]
        indexes = [models.Index(fields=["business", "state", "due_date"])]
