import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from tapme.reminders.domain import DEFAULT_TEMPLATE


def default_offsets():
    return [14, 7, 3, 1]


class ReminderSettings(models.Model):
    scenarios_initialized = models.BooleanField(default=False, db_default=False)
    min_days_between = models.PositiveSmallIntegerField(default=7, db_default=7)
    version = models.PositiveIntegerField(default=1)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    business = models.OneToOneField(
        "businesses.Business", primary_key=True, on_delete=models.CASCADE
    )
    enabled = models.BooleanField(default=True)
    offsets = models.JSONField(default=default_offsets)
    inactive_days = models.PositiveSmallIntegerField(default=90)
    start_hour = models.PositiveSmallIntegerField(default=9)
    end_hour = models.PositiveSmallIntegerField(default=20)
    templates = models.JSONField(default=dict)
    custom_templates = models.JSONField(default=list)
    template = models.TextField(default=DEFAULT_TEMPLATE)
    inactive_template = models.TextField(
        default="{name}, здравствуйте! Давно не выбирали цветы у нас. Подобрать букет для вас? {shop}"
    )


class ReminderScenario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=30)
    enabled = models.BooleanField(default=True)
    event_labels = models.JSONField(default=list)
    holiday_month = models.PositiveSmallIntegerField(default=3)
    holiday_day = models.PositiveSmallIntegerField(default=8)
    audience = models.CharField(max_length=30, default="consented_all")
    daily_cap = models.PositiveSmallIntegerField(default=40)
    sort = models.PositiveSmallIntegerField(default=0)
    archived = models.BooleanField(default=False)
    legacy_kind = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["sort", "id"]


class ReminderStep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scenario = models.ForeignKey(ReminderScenario, on_delete=models.CASCADE, related_name="steps")
    offset_days = models.PositiveSmallIntegerField()
    template = models.TextField()
    enabled = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)
    sort = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]


class ReminderRecord(models.Model):
    scenario = models.ForeignKey(ReminderScenario, null=True, on_delete=models.SET_NULL)
    step = models.ForeignKey(ReminderStep, null=True, on_delete=models.SET_NULL)
    event_date = models.DateField(null=True)
    occurrence_key = models.CharField(max_length=160, blank=True, default="", db_default="")
    sent_at = models.DateTimeField(null=True)
    order = models.ForeignKey("orders.OrderRecord", null=True, on_delete=models.SET_NULL)
    opt_out_at = models.DateTimeField(null=True)
    recovered = models.BooleanField(default=False)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    customer = models.ForeignKey(
        "customers.CustomerRecord", on_delete=models.CASCADE, related_name="reminders"
    )
    key = models.CharField(max_length=400)
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
