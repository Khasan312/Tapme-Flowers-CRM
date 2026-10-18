import uuid

from django.conf import settings
from django.db import models

from tapme.businesses.application.contracts import Role


class Business(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    currency = models.CharField(max_length=3, default="KGS")
    timezone = models.CharField(max_length=60, default="Asia/Bishkek")

    def __str__(self):
        return self.name


def default_windows():
    return [
        {"start": "10:00", "end": "12:00"},
        {"start": "12:00", "end": "14:00"},
        {"start": "14:00", "end": "16:00"},
        {"start": "16:00", "end": "18:00"},
    ]


class Shop(models.Model):
    version = models.PositiveIntegerField(default=1)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.OneToOneField(Business, on_delete=models.PROTECT, related_name="shop")
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=500, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    city = models.CharField(max_length=100, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    opening_hours = models.CharField(max_length=150, blank=True)
    pickup_unlimited = models.BooleanField(default=True)
    enforce_capacity = models.BooleanField(default=False)
    delivery_windows = models.JSONField(default=default_windows)
    payment_qr_key = models.CharField(max_length=500, blank=True, default="", db_default="")
    payment_note = models.CharField(max_length=150, blank=True, default="", db_default="")
    payment_message = models.CharField(
        max_length=1024,
        default="Заказ №{номер} · к оплате {сумма} сом. Пришлите, пожалуйста, скриншот оплаты",
        db_default="Заказ №{номер} · к оплате {сумма} сом. Пришлите, пожалуйста, скриншот оплаты",
    )
    payment_version = models.PositiveIntegerField(default=1, db_default=1)


class Membership(models.Model):
    business = models.ForeignKey(Business, on_delete=models.PROTECT, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=[(r.value, r.name) for r in Role])
    is_active = models.BooleanField(default=True)
    phone = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "user"], name="unique_business_member"),
            models.CheckConstraint(
                condition=models.Q(role__in=[r.value for r in Role]), name="valid_member_role"
            ),
        ]
