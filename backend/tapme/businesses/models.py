import uuid

from django.conf import settings
from django.db import models

from tapme.businesses.application.contracts import Role


class Business(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    currency = models.CharField(max_length=3, default="KGS")
    timezone = models.CharField(max_length=60, default="Asia/Bishkek")

    class Meta:
        permissions = [("manage_platform", "Manage TapMe companies and initial owner access")]

    def __str__(self):
        return self.name

    @property
    def shop(self):
        """Compatibility for single-shop management commands."""
        return self.points.get(is_primary=True)


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
    business = models.ForeignKey(Business, on_delete=models.PROTECT, related_name="points")
    is_primary = models.BooleanField(default=True, db_default=True)
    active = models.BooleanField(default=True, db_default=True)
    short_name = models.CharField(max_length=40, default="Основная", db_default="Основная")
    sort = models.PositiveIntegerField(default=0, db_default=0)
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

    class Meta:
        ordering = ["sort", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["business"], condition=models.Q(is_primary=True), name="one_primary_point"
            ),
            models.CheckConstraint(
                condition=models.Q(is_primary=False) | models.Q(active=True),
                name="primary_point_active",
            ),
        ]


class Membership(models.Model):
    business = models.ForeignKey(Business, on_delete=models.PROTECT, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=[(r.value, r.name) for r in Role])
    is_active = models.BooleanField(default=True)
    phone = models.CharField(max_length=40, blank=True)
    points = models.ManyToManyField(Shop, through="MembershipPoint", related_name="memberships")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "user"], name="unique_business_member"),
            models.CheckConstraint(
                condition=models.Q(role__in=[r.value for r in Role]), name="valid_member_role"
            ),
        ]


class MembershipPoint(models.Model):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE)
    point = models.ForeignKey(Shop, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["membership", "point"], name="unique_membership_point")
        ]
