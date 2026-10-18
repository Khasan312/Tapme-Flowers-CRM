"""Owner-only fake events travel through the same authenticated webhook inbox."""

import hashlib
import hmac
import json
from uuid import uuid4

from django.conf import settings
from django.test import RequestFactory
from django.utils import timezone

from tapme.messaging.infrastructure.meta import decrypt
from tapme.shared.domain import InvalidInput


def simulate(channel, phone, text, name):
    if (
        not settings.DEBUG
        or settings.TAPME_META_MODE != "fake"
        or channel.provider_mode != "fake"
        or channel.status != "active"
    ):
        raise InvalidInput(
            "Симулятор доступен только для активного тестового канала в режиме разработки."
        )
    from tapme.messaging.api import whatsapp_webhook

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": channel.waba_id,
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": channel.phone_number_id},
                            "contacts": [{"wa_id": phone.lstrip("+"), "profile": {"name": name}}],
                            "messages": [
                                {
                                    "id": "wamid.sim." + uuid4().hex,
                                    "from": phone.lstrip("+"),
                                    "timestamp": str(int(timezone.now().timestamp())),
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    body = json.dumps(payload).encode()
    signature = (
        "sha256="
        + hmac.new(decrypt(channel.app_secret_encrypted).encode(), body, hashlib.sha256).hexdigest()
    )
    response = whatsapp_webhook(
        RequestFactory().post(
            "/", body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=signature
        ),
        channel.webhook_key,
    )
    if response.status_code != 200:
        raise InvalidInput("Не удалось принять тестовое сообщение.")
    return {"ok": True}
