"""Manual Instagram Unified Login connection; credentials never leave the server."""

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from tapme.businesses.models import Business, Membership
from tapme.messaging.domain import DeliveryRejected, DeliveryUnknown
from tapme.messaging.infrastructure.meta import configured, decrypt, encrypt, gateway_for
from tapme.messaging.models import ChannelAccount, Message, webhook_token
from tapme.shared.domain import Conflict, InvalidInput, NotFound


class InstagramOperations:
    def instagram_channel(self, scope):
        row = ChannelAccount.objects.filter(business_id=scope.business_id, kind="instagram").first()
        owner = Membership.objects.filter(
            business_id=scope.business_id, user_id=scope.user_id, role="owner", is_active=True
        ).exists()
        result = {
            "configured": bool(configured()),
            "server_mode": settings.TAPME_META_MODE,
            "provider_mode": row.provider_mode if row else settings.TAPME_META_MODE,
            "simulator": settings.DEBUG and settings.TAPME_META_MODE == "fake",
            "status": row.status if row else "disconnected",
            "version": row.version if row else 0,
            "ig_user_id": row.ig_user_id if row else "",
            "ig_username": row.ig_username if row else "",
            "display_name": row.display_name if row else "",
            "display_phone": "",
            "connection_error": row.connection_error if row else "",
            "last_webhook_at": row.last_webhook_at if row else None,
            "checks": {
                key: bool(row and getattr(row, key))
                for key in [
                    "token_checked_at",
                    "webhook_verified_at",
                    "subscribed_at",
                    "last_inbound_at",
                ]
            },
        }
        result["checks"]["first_reply_sent"] = bool(
            row
            and Message.objects.filter(
                conversation__channel=row,
                direction="out",
                sender__isnull=False,
                status__in=["sent", "delivered", "read"],
            ).exists()
        )
        if owner:
            result["webhook_path"] = (
                f"/api/v1/webhooks/meta/instagram/{row.webhook_key}/" if row else ""
            )
            result["verify_token"] = (
                row.verify_token if row and row.status != "disconnected" else ""
            )
        return result

    def instagram_connect(self, scope, ig_user_id, token, app_secret, version):
        if not configured():
            raise InvalidInput("Настройте ключ шифрования и версию Meta API на сервере.")
        try:
            info = gateway_for(kind="instagram").inspect(ig_user_id, token)
        except (DeliveryRejected, DeliveryUnknown) as exc:
            raise InvalidInput(str(exc)) from None
        if str(info.get("id")) != ig_user_id or not info.get("username"):
            raise InvalidInput("Meta не подтвердила профессиональный аккаунт Instagram.")
        try:
            with transaction.atomic():
                Business.objects.select_for_update().get(id=scope.business_id)
                old = (
                    ChannelAccount.objects.select_for_update()
                    .filter(business_id=scope.business_id, kind="instagram")
                    .first()
                )
                if (old.version if old else 0) != version:
                    raise Conflict("Подключение изменилось. Обновите настройки.")
                if old and old.ig_user_id != ig_user_id:
                    raise Conflict(
                        "История относится к другому аккаунту Instagram. Подключите прежний аккаунт."
                    )
                if (
                    old
                    and old.provider_mode != settings.TAPME_META_MODE
                    and old.conversation_set.exists()
                ):
                    raise Conflict(
                        "Для реального подключения используйте магазин без тестовой переписки Instagram."
                    )
                reset = old and (
                    old.status == "disconnected"
                    or old.provider_mode != settings.TAPME_META_MODE
                    or not old.app_secret_encrypted
                    or decrypt(old.app_secret_encrypted) != app_secret
                )
                defaults = dict(
                    ig_user_id=ig_user_id,
                    ig_username=str(info["username"])[:150],
                    display_name=str(info.get("name") or info["username"])[:150],
                    display_phone="",
                    phone_number_id=None,
                    token_encrypted=encrypt(token),
                    app_secret_encrypted=encrypt(app_secret),
                    status="active",
                    provider_mode=settings.TAPME_META_MODE,
                    token_checked_at=timezone.now(),
                    connection_error="",
                    autoreply={"enabled": False},
                    version=old.version + 1 if old else 1,
                )
                if reset:
                    defaults.update(
                        webhook_key=webhook_token(),
                        verify_token=webhook_token(),
                        webhook_verified_at=None,
                        subscribed_at=None,
                        last_inbound_at=None,
                    )
                ChannelAccount.objects.update_or_create(
                    business_id=scope.business_id, kind="instagram", defaults=defaults
                )
        except IntegrityError:
            raise Conflict("Этот Instagram уже подключён к другому магазину.") from None
        return self.instagram_channel(scope)

    def instagram_action(self, scope, action):
        row = ChannelAccount.objects.filter(business_id=scope.business_id, kind="instagram").first()
        if not row or row.status != "active":
            raise NotFound("Сначала подключите Instagram.")
        try:
            gateway = gateway_for(row)
            token = decrypt(row.token_encrypted)
            if action == "subscribe":
                if not row.webhook_verified_at:
                    raise InvalidInput("Сначала подтвердите Callback URL в Meta.")
                gateway.subscribe(row.ig_user_id, token)
                changes = {"subscribed_at": timezone.now()}
            else:
                info = gateway.inspect(row.ig_user_id, token)
                if str(info.get("id")) != row.ig_user_id or not info.get("username"):
                    raise DeliveryRejected("Meta не подтвердила аккаунт Instagram.")
                changes = {
                    "token_checked_at": timezone.now(),
                    "ig_username": str(info["username"])[:150],
                }
        except (DeliveryRejected, DeliveryUnknown) as exc:
            ChannelAccount.objects.filter(id=row.id, version=row.version).update(
                connection_error=str(exc)[:300]
            )
            raise InvalidInput(str(exc)) from None
        if not ChannelAccount.objects.filter(
            id=row.id, version=row.version, status="active"
        ).update(**changes, connection_error=""):
            raise Conflict("Канал изменился во время проверки. Обновите настройки.")
        return self.instagram_channel(scope)

    @transaction.atomic
    def instagram_disconnect(self, scope):
        row = (
            ChannelAccount.objects.select_for_update()
            .filter(business_id=scope.business_id, kind="instagram")
            .first()
        )
        if row:
            row.token_encrypted = row.app_secret_encrypted = ""
            row.status = "disconnected"
            row.version += 1
            row.save(update_fields=["token_encrypted", "app_secret_encrypted", "status", "version"])
            Message.objects.filter(conversation__channel=row, status="queued").update(
                status="failed", error="Instagram отключён."
            )
        return self.instagram_channel(scope)
