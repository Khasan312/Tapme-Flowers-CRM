from django.conf import settings
from django.db import models


class PlatformEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="platform_events"
    )
    action = models.CharField(
        max_length=30,
        choices=[
            ("business_created", "Магазин подключён"),
            ("owner_password_reset", "Доступ владельца восстановлен"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
