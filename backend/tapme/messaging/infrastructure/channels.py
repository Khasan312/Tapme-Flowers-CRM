from uuid import uuid4

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.businesses.models import Business, Membership, Shop
from tapme.messaging.domain import DeliveryRejected, DeliveryUnknown
from tapme.messaging.infrastructure.meta import configured, decrypt, encrypt, gateway_for
from tapme.messaging.models import ChannelAccount, Message
from tapme.shared.domain import Conflict, InvalidInput, NotFound


class ChannelOperations:
    def _channel(self, scope):
        row = ChannelAccount.objects.filter(business_id=scope.business_id).first()
        if not row:
            raise NotFound("Сначала подключите номер WhatsApp.")
        return row

    def channel(self, scope):
        row = ChannelAccount.objects.filter(business_id=scope.business_id).first()
        owner = Membership.objects.filter(
            business_id=scope.business_id, user_id=scope.user_id, role="owner", is_active=True
        ).exists()
        shop = Shop.objects.filter(business_id=scope.business_id, is_primary=True).first()
        result = {
            "configured": bool(configured()),
            "provider_mode": row.provider_mode if row else settings.TAPME_META_MODE,
            "server_mode": settings.TAPME_META_MODE,
            "simulator": settings.DEBUG and settings.TAPME_META_MODE == "fake",
            "status": row.status if row else "disconnected",
            "version": row.version if row else 0,
            "display_name": row.display_name if row else "",
            "display_phone": row.display_phone if row else "",
            "phone_number_id": row.phone_number_id if row else "",
            "waba_id": row.waba_id if row else "",
            "last_webhook_at": row.last_webhook_at if row else None,
            "quality_rating": row.quality_rating if row else "",
            "connection_error": row.connection_error if row else "",
            "autoreply": row.autoreply if row else None,
            "checks": {
                key: bool(row and getattr(row, key))
                for key in [
                    "token_checked_at",
                    "registered_at",
                    "webhook_verified_at",
                    "subscribed_at",
                    "last_inbound_at",
                ]
            },
            "main_phone": (shop.whatsapp or shop.phone) if shop else "",
            "payment": self.payment(scope),
        }
        if owner:
            result["webhook_path"] = (
                f"/api/v1/webhooks/meta/whatsapp/{row.webhook_key}/" if row else ""
            )
            result["verify_token"] = (
                row.verify_token if row and row.status != "disconnected" else ""
            )
        return result

    def connect(self, scope, phone_number_id, token, waba_id="", app_secret="", version=None):
        if not configured():
            raise InvalidInput("Настройте TAPME_SECRETS_KEY и версию Meta API на сервере.")
        if bool(waba_id) != bool(app_secret):
            raise InvalidInput("Укажите WhatsApp Business Account ID и App Secret вместе.")
        if not app_secret and not settings.META_APP_SECRET:
            raise InvalidInput("Укажите App Secret приложения магазина.")
        try:
            info = self.gateway.inspect(phone_number_id, token)
            if waba_id:
                self.gateway.verify_account(phone_number_id, waba_id, token)
        except (DeliveryRejected, DeliveryUnknown) as exc:
            raise InvalidInput(str(exc)) from None
        if str(info.get("id")) != phone_number_id or not info.get("display_phone_number"):
            raise InvalidInput("Meta не подтвердила этот номер.")
        try:
            with transaction.atomic():
                Business.objects.select_for_update().get(id=scope.business_id)
                old = (
                    ChannelAccount.objects.select_for_update()
                    .filter(business_id=scope.business_id)
                    .first()
                )
                if old and old.phone_number_id != phone_number_id:
                    raise Conflict(
                        "У магазина есть история другого номера. Подключите прежний номер."
                    )
                if old and old.version != version:
                    raise Conflict("Подключение изменилось в другой вкладке. Обновите настройки.")
                if (
                    old
                    and old.provider_mode != settings.TAPME_META_MODE
                    and old.conversation_set.exists()
                ):
                    raise Conflict(
                        "История относится к другому режиму. Для реального подключения используйте отдельный магазин без тестовой переписки."
                    )
                changed_secret = (
                    old
                    and app_secret
                    and (
                        not old.app_secret_encrypted
                        or decrypt(old.app_secret_encrypted) != app_secret
                    )
                )
                defaults = dict(
                    phone_number_id=phone_number_id,
                    waba_id=waba_id,
                    display_phone=str(info["display_phone_number"])[:40],
                    display_name=str(info.get("verified_name", "WhatsApp"))[:150],
                    token_encrypted=encrypt(token),
                    app_secret_encrypted=encrypt(app_secret) if app_secret else "",
                    status="active",
                    provider_mode=settings.TAPME_META_MODE,
                    token_checked_at=timezone.now(),
                    registered_at=(
                        timezone.now() if info.get("platform_type") == "CLOUD_API" else None
                    ),
                    quality_rating=str(info.get("quality_rating", ""))[:30],
                    connection_error="",
                    version=(old.version + 1) if old else 1,
                )
                if old and (
                    changed_secret
                    or old.waba_id != waba_id
                    or old.provider_mode != settings.TAPME_META_MODE
                    or old.status == "disconnected"
                ):
                    from tapme.messaging.models import webhook_token

                    defaults.update(
                        webhook_key=webhook_token(),
                        verify_token=webhook_token(),
                        webhook_verified_at=None,
                        subscribed_at=None,
                        last_inbound_at=None,
                    )
                ChannelAccount.objects.update_or_create(
                    business_id=scope.business_id, defaults=defaults
                )
        except IntegrityError:
            raise Conflict("Этот номер уже подключён к другому магазину.") from None
        return self.channel(scope)

    @transaction.atomic
    def disconnect(self, scope):
        row = (
            ChannelAccount.objects.select_for_update().filter(business_id=scope.business_id).first()
        )
        if row:
            row.token_encrypted = row.app_secret_encrypted = ""
            row.status = "disconnected"
            row.version += 1
            row.save(update_fields=["token_encrypted", "app_secret_encrypted", "status", "version"])
            Message.objects.filter(conversation__channel=row, status="queued").update(
                status="failed", error="Канал отключён."
            )
        return self.channel(scope)

    def channel_action(self, scope, action, pin=""):
        row = self._channel(scope)
        if row.status == "disconnected":
            raise InvalidInput("Канал отключён.")
        try:
            gateway = gateway_for(row)
            token = decrypt(row.token_encrypted)
            if action == "register":
                gateway.register(row.phone_number_id, token, pin)
                changes = {"registered_at": timezone.now()}
            elif action == "subscribe":
                if not row.waba_id:
                    raise InvalidInput("Укажите WhatsApp Business Account ID в подключении.")
                gateway.subscribe(row.waba_id, token)
                changes = {"subscribed_at": timezone.now()}
            else:
                info = gateway.inspect(row.phone_number_id, token)
                if str(info.get("id")) != row.phone_number_id:
                    raise DeliveryRejected("Meta вернула другой номер.")
                if row.waba_id:
                    gateway.verify_account(row.phone_number_id, row.waba_id, token)
                changes = {
                    "token_checked_at": timezone.now(),
                    "quality_rating": str(info.get("quality_rating", ""))[:30],
                }
                if info.get("platform_type") == "CLOUD_API":
                    changes["registered_at"] = timezone.now()
        except (DeliveryRejected, DeliveryUnknown) as exc:
            ChannelAccount.objects.filter(id=row.id, version=row.version).update(
                connection_error=str(exc)[:300]
            )
            raise InvalidInput(str(exc)) from None
        updated = ChannelAccount.objects.filter(
            id=row.id, version=row.version, status="active"
        ).update(**changes, connection_error="")
        if not updated:
            raise Conflict("Канал изменился во время проверки. Обновите страницу.")
        return self.channel(scope)

    @transaction.atomic
    def save_autoreply(self, scope, version, **data):
        row = ChannelAccount.objects.select_for_update().get(id=self._channel(scope).id)
        if row.version != version:
            raise Conflict("Настройки изменены в другой вкладке. Обновите страницу.")
        if data["start"] == data["end"]:
            raise InvalidInput("Начало и конец рабочих часов должны различаться.")
        row.autoreply = data
        row.version += 1
        row.save(update_fields=["autoreply", "version"])
        return self.channel(scope)

    def payment_shop(self, scope, lock=False):
        points = DjangoMembershipReader().points(scope)
        if lock:
            points = points.select_for_update()
        shop = (
            points.filter(id=scope.point_id).first()
            if scope.point_id
            else points.filter(is_primary=True).first()
        )
        if not shop:
            raise NotFound("Выберите доступную точку для оплаты.")
        return shop

    def payment(self, scope):
        shop = self.payment_shop(scope)
        return {
            "version": shop.payment_version if shop else 0,
            "note": shop.payment_note if shop else "",
            "text": shop.payment_message if shop else "",
            "image_url": f"/api/v1/businesses/{scope.business_id}/channels/payment-qr/?point={shop.id}"
            if shop and shop.payment_qr_key
            else None,
        }

    @transaction.atomic
    def save_payment(self, scope, version, note, text, content=None, mime="", remove=False):
        shop = self.payment_shop(scope, lock=True)
        if version != shop.payment_version:
            raise Conflict("QR или подпись изменены в другой вкладке. Обновите настройки.")
        old = shop.payment_qr_key
        key = None
        if content is not None:
            if len(content) > 5 * 1024 * 1024 or mime not in {
                "image/jpeg",
                "image/png",
                "image/webp",
            }:
                raise InvalidInput("Загрузите QR в PNG/JPEG/WebP до 5 МБ.")
            key, _ = self.storage.save(f"{scope.business_id}/payment/{uuid4().hex}", content, mime)
            shop.payment_qr_key = key
        elif remove:
            shop.payment_qr_key = ""
        shop.payment_note, shop.payment_message = note, text
        shop.payment_version += 1
        try:
            shop.save(
                update_fields=[
                    "payment_qr_key",
                    "payment_note",
                    "payment_message",
                    "payment_version",
                ]
            )
        except Exception:
            if key:
                self.storage.delete(key)
            raise
        if old and old != shop.payment_qr_key:
            transaction.on_commit(lambda: self.storage.delete(old), robust=True)
        return self.payment(scope)

    def payment_file(self, scope):
        shop = self.payment_shop(scope)
        if not shop.payment_qr_key:
            raise NotFound("QR пока не загружен.")
        return {
            "content": self.storage.read(shop.payment_qr_key),
            "mime": "image/jpeg",
            "name": "payment-qr.jpg",
        }

    def simulate(self, scope, phone, text, name):
        from tapme.messaging.infrastructure.simulation import simulate

        return simulate(self._channel(scope), phone, text, name)

    def simulate_verify(self, scope):
        from django.test import RequestFactory

        from tapme.messaging.api import whatsapp_webhook

        row = self._channel(scope)
        if not settings.DEBUG or settings.TAPME_META_MODE != "fake" or row.provider_mode != "fake":
            raise InvalidInput("Симулятор доступен только в режиме разработки.")
        response = whatsapp_webhook(
            RequestFactory().get(
                "/",
                {
                    "hub.mode": "subscribe",
                    "hub.verify_token": row.verify_token,
                    "hub.challenge": "verified",
                },
            ),
            row.webhook_key,
        )
        if response.status_code != 200:
            raise InvalidInput("Проверка вебхука не прошла.")
        return self.channel(scope)
