import hashlib
import hmac
import io
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from tapme.messaging.infrastructure.meta import decrypt, gateway_for
from tapme.messaging.infrastructure.processing import deliver, process_event
from tapme.messaging.models import ChannelAccount, Conversation, Message, WebhookEvent
from tapme.messaging.tasks import process_messages


@pytest.fixture
def pilot(setup, settings, tmp_path):
    settings.DEBUG = True
    settings.TAPME_META_MODE = "fake"
    settings.TAPME_SECRETS_KEY = Fernet.generate_key().decode()
    settings.STORAGES = {
        **settings.STORAGES,
        "photos": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": tmp_path},
        },
    }
    client = setup["client"]
    base = f"/api/v1/businesses/{setup['business'].id}"
    response = client.post(
        base + "/channels/whatsapp/",
        {
            "phone_number_id": "123456789",
            "waba_id": "987654321",
            "token": "private-token",
            "app_secret": "private-secret",
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    return setup, client, base, ChannelAccount.objects.get(business=setup["business"])


def incoming(client, base, phone="+996700000111", text="Нужен букет"):
    response = client.post(
        base + "/channels/whatsapp/simulate/",
        {"phone": phone, "name": "Айжан", "text": text},
        format="json",
    )
    assert response.status_code == 200, response.data
    for event in WebhookEvent.objects.filter(processed_at=None):
        process_event(event.digest)
    return Conversation.objects.get(phone=phone)


def test_connection_secrets_scoping_and_disconnect(pilot):
    setup, client, base, channel = pilot
    assert channel.token_encrypted != "private-token"
    assert decrypt(channel.app_secret_encrypted) == "private-secret"
    url = f"/api/v1/webhooks/meta/whatsapp/{channel.webhook_key}/"
    assert client.get(url, {"hub.mode": "subscribe", "hub.verify_token": "bad"}).status_code == 403
    assert (
        client.get(
            url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": channel.verify_token,
                "hub.challenge": "ok",
            },
        ).content
        == b"ok"
    )
    assert (
        client.post(
            url, b"{}", content_type="application/json", HTTP_X_HUB_SIGNATURE_256="sha256=bad"
        ).status_code
        == 401
    )
    assert not WebhookEvent.objects.exists()
    client.force_login(setup["manager"])
    result = client.get(base + "/channels/whatsapp/").data
    assert "verify_token" not in result and "webhook_path" not in result
    assert "private-token" not in str(result)
    assert client.post(base + "/channels/whatsapp/subscribe/", {}, format="json").status_code == 403
    client.force_login(setup["owner"])
    assert client.post(base + "/channels/whatsapp/subscribe/", {}, format="json").status_code == 200
    assert client.delete(base + "/channels/whatsapp/").status_code == 200
    channel.refresh_from_db()
    assert not channel.token_encrypted and not channel.app_secret_encrypted
    assert client.get(url).status_code == 404


def test_auto_reply_preserves_waiting_and_never_assigns(pilot):
    setup, client, base, channel = pilot
    chat = incoming(client, base)
    assert chat.customer.origin == "whatsapp" and chat.customer.code
    assert chat.customer_created and not chat.customer.consent
    auto = chat.messages.get(automated=True)
    deliver(auto.id, None)
    chat.refresh_from_db()
    assert chat.waiting_since and not chat.assigned_to_id and not chat.customer.responsible_id
    incoming(client, base)
    assert chat.messages.filter(automated=True).count() == 1
    response = client.patch(
        f"{base}/chats/{chat.id}/",
        {"version": Conversation.objects.get(id=chat.id).version, "customer_name": "Айжан Асанова"},
        format="json",
    )
    assert response.status_code == 200, response.data
    assert response.data["name"] == "Айжан Асанова" and not response.data["new_customer"]
    client.force_login(setup["manager"])
    request_id = str(uuid4())
    response = client.post(
        f"{base}/chats/{chat.id}/messages/",
        {"text": "Здравствуйте!", "request_id": request_id},
        format="json",
    )
    assert response.status_code == 200, response.data
    row = Message.objects.get(id=response.data["id"])
    deliver(row.id, None)
    chat.refresh_from_db()
    chat.customer.refresh_from_db()
    assert (
        chat.assigned_to_id == setup["manager"].id
        and chat.customer.responsible_id == setup["manager"].id
    )
    assert chat.waiting_since is None
    client.force_login(setup["owner"])
    incoming(client, base, text="Спасибо")
    client.force_login(setup["manager"])
    chat.refresh_from_db()
    assert chat.waiting_since
    assert client.get(base + "/chats/summary/?after=0").data["items"]


def test_closed_reply_is_separate_from_daytime_and_persisted_across_midnight(pilot, monkeypatch):
    setup, client, base, channel = pilot
    client.force_authenticate(setup["owner"])
    setup["business"].timezone = "Asia/Bishkek"
    setup["business"].save(update_fields=["timezone"])
    channel.autoreply = {
        "enabled": True,
        "start": "09:00",
        "end": "20:00",
        "open_text": "Открыто",
        "closed_text": "Закрыто",
    }
    channel.save(update_fields=["autoreply"])
    for instant, expected in [
        (datetime(2026, 10, 28, 13, 50, tzinfo=UTC), ["Открыто"]),
        (datetime(2026, 10, 28, 14, 0, tzinfo=UTC), ["Открыто", "Закрыто"]),
        (datetime(2026, 10, 28, 19, 27, tzinfo=UTC), ["Открыто", "Закрыто"]),
        (datetime(2026, 10, 29, 2, 59, tzinfo=UTC), ["Открыто", "Закрыто"]),
        (datetime(2026, 10, 29, 14, 0, tzinfo=UTC), ["Открыто", "Закрыто", "Закрыто"]),
    ]:
        monkeypatch.setattr(timezone, "now", lambda: instant)
        chat = incoming(client, base)
        assert (
            list(chat.messages.filter(automated=True).order_by("id").values_list("text", flat=True))
            == expected
        )
        assert chat.waiting_since and not chat.assigned_to_id
        assert chat.mode == "human"
    # Retried delivery of the same webhook must not create another reply.
    for event in WebhookEvent.objects.all():
        process_event(event.digest)
    assert chat.messages.filter(automated=True).count() == 3


def test_enabling_closed_reply_in_existing_chat_does_not_need_day_of_silence(pilot, monkeypatch):
    setup, client, base, channel = pilot
    setup["business"].timezone = "Asia/Bishkek"
    setup["business"].save(update_fields=["timezone"])
    channel.autoreply = {
        "enabled": False,
        "start": "09:00",
        "end": "20:00",
        "open_text": "Открыто",
        "closed_text": "Закрыто",
    }
    channel.save(update_fields=["autoreply"])
    monkeypatch.setattr(timezone, "now", lambda: datetime(2026, 10, 28, 16, 32, tzinfo=UTC))
    chat = incoming(client, base)
    assert not chat.messages.filter(automated=True).exists()
    channel.autoreply["enabled"] = True
    channel.save(update_fields=["autoreply"])
    monkeypatch.setattr(timezone, "now", lambda: datetime(2026, 10, 28, 19, 27, tzinfo=UTC))
    chat = incoming(client, base)
    assert chat.messages.get(automated=True).text == "Закрыто"
    incoming(client, base, text="Ещё вопрос")
    assert chat.messages.filter(automated=True).count() == 1


def test_reconnect_resets_checks_when_account_changes(pilot, monkeypatch):
    _, client, base, channel = pilot
    from tapme.messaging.infrastructure.meta import FakeGateway

    monkeypatch.setattr(
        FakeGateway,
        "inspect",
        lambda self, phone, token: {"id": phone, "display_phone_number": "+996700555010"},
    )
    channel.webhook_verified_at = channel.subscribed_at = channel.last_inbound_at = timezone.now()
    channel.save()
    old_key = channel.webhook_key
    response = client.post(
        base + "/channels/whatsapp/",
        {
            "phone_number_id": channel.phone_number_id,
            "waba_id": "999999999",
            "token": "new-token",
            "app_secret": "private-secret",
            "version": channel.version,
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    channel.refresh_from_db()
    assert channel.webhook_key != old_key
    assert channel.registered_at is None
    assert not any(
        response.data["checks"][key]
        for key in ["webhook_verified_at", "subscribed_at", "last_inbound_at"]
    )


def test_existing_phone_window_optout_and_fake_guard(pilot, settings):
    setup, client, base, channel = pilot
    chat = incoming(client, base, setup["customer"].phone)
    assert chat.customer_id == setup["customer"].id
    chat.last_inbound_at = timezone.now() - timedelta(hours=25)
    chat.save()
    assert (
        client.post(
            f"{base}/chats/{chat.id}/messages/",
            {"text": "Поздно", "request_id": str(uuid4())},
            format="json",
        ).status_code
        == 400
    )
    incoming(client, base, setup["customer"].phone, "стоп")
    assert not client.get(f"{base}/chats/{chat.id}/").data["can_reply"]
    settings.DEBUG = False
    assert (
        client.post(
            base + "/channels/whatsapp/simulate/",
            {"name": "Тест", "phone": "+996700000222", "text": "нет"},
            format="json",
        ).status_code
        == 400
    )
    settings.TAPME_META_MODE = "live"
    from tapme.messaging.domain import DeliveryRejected

    with pytest.raises(DeliveryRejected):
        gateway_for(channel)


def test_qr_snapshot_idempotency_and_quick_replies(pilot):
    setup, client, base, channel = pilot
    chat = incoming(client, base)
    image = io.BytesIO()
    Image.new("RGB", (50, 50), "white").save(image, "PNG")
    response = client.post(
        base + "/channels/payment-qr/",
        {
            "version": 1,
            "note": "Банк",
            "text": "Оплатите {сумма} сом, заказ {номер}",
            "file": SimpleUploadedFile("qr.png", image.getvalue(), content_type="image/png"),
        },
        format="multipart",
    )
    assert response.status_code == 200, response.data
    path = f"{base}/chats/{chat.id}/payment-qr/"
    payload = {"amount": "123.45", "request_id": str(uuid4())}
    first = client.post(path, payload, format="json")
    assert first.status_code == 200, first.data
    second = client.post(path, payload, format="json")
    assert second.data["id"] == first.data["id"]
    assert "123.45" in first.data["text"] and first.data["media_url"]
    assert (
        client.post(
            base + "/channels/payment-qr/",
            {"version": 2, "note": "", "text": "{сумма}", "remove": True},
            format="json",
        ).status_code
        == 200
    )
    assert client.get(first.data["media_url"]).status_code == 200
    reply = client.post(
        base + "/quick-replies/", {"title": "Привет", "text": "Здравствуйте"}, format="json"
    )
    assert reply.status_code == 200, reply.data
    assert len(client.get(base + "/quick-replies/").data) == 1
    assert client.patch(base + "/quick-replies/", {}, format="json").status_code == 405
    assert client.get(base + "/quick-replies/" + reply.data["id"] + "/").status_code == 405
    path = base + "/quick-replies/" + reply.data["id"] + "/"
    assert (
        client.patch(
            path, {"version": 1, "title": "Привет", "text": "Добрый день"}, format="json"
        ).status_code
        == 200
    )
    assert client.delete(path, {"version": 1}, format="json").status_code == 409
    client.force_login(setup["other_owner"])
    other = f"/api/v1/businesses/{setup['other_business'].id}"
    assert client.get(other + f"/chats/{chat.id}/payment-qr/").status_code == 404
    assert (
        client.patch(
            other + "/quick-replies/" + reply.data["id"] + "/",
            {"version": 2, "title": "нет", "text": "нет"},
            format="json",
        ).status_code
        == 404
    )


def test_receipts_retry_without_consuming_attempts_and_read(pilot):
    setup, client, base, channel = pilot
    chat = incoming(client, base)
    response = client.post(
        f"{base}/chats/{chat.id}/messages/",
        {"text": "Ответ", "request_id": str(uuid4())},
        format="json",
    )
    outgoing = Message.objects.get(id=response.data["id"])
    body = json.dumps(
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "metadata": {"phone_number_id": channel.phone_number_id},
                                "statuses": [{"id": "late-id", "status": "read"}],
                            },
                        }
                    ]
                }
            ],
        }
    ).encode()
    sig = "sha256=" + hmac.new(b"private-secret", body, hashlib.sha256).hexdigest()
    assert (
        client.post(
            f"/api/v1/webhooks/meta/whatsapp/{channel.webhook_key}/",
            body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig,
        ).status_code
        == 200
    )
    event = WebhookEvent.objects.filter(processed_at=None).get()
    for _ in range(6):
        process_messages()
    event.refresh_from_db()
    assert event.attempts == 0 and not event.processed_at
    outgoing.external_id = "late-id"
    outgoing.save()
    process_messages()
    outgoing.refresh_from_db()
    assert outgoing.status == "read"
    message = chat.messages.filter(direction="in").latest("id")
    assert (
        client.post(
            f"{base}/chats/{chat.id}/read/", {"last_message_id": message.id}, format="json"
        ).status_code
        == 200
    )
    process_messages()
    chat.refresh_from_db()
    assert chat.provider_read_sent_id == message.id


def test_settings_version_and_role_guards(pilot):
    setup, client, base, channel = pilot
    data = {**channel.autoreply, "version": channel.version, "enabled": False}
    assert (
        client.post(base + "/channels/whatsapp/autoreply/", data, format="json").status_code == 200
    )
    assert (
        client.post(base + "/channels/whatsapp/autoreply/", data, format="json").status_code == 409
    )
    client.force_login(setup["florist"])
    for path in ["chats/", "chats/summary/", "quick-replies/", "channels/payment-qr/"]:
        assert client.get(base + "/" + path).status_code == 403


def test_autoreply_daytime_cooldown(pilot, monkeypatch):
    setup, client, base, channel = pilot
    setup["business"].timezone = "Asia/Bishkek"
    setup["business"].save(update_fields=["timezone"])
    monkeypatch.setattr(timezone, "now", lambda: datetime(2026, 10, 29, 9, 0, tzinfo=UTC))
    client.force_login(setup["owner"])
    channel.autoreply = {
        "enabled": True,
        "start": "09:00",
        "end": "20:00",
        "open_text": "Открыто: {магазин}",
        "closed_text": "Закрыто: {магазин}",
    }
    channel.save()
    chat = incoming(client, base)
    assert chat.messages.get(automated=True).text == "Открыто: Первый магазин"
    chat.last_inbound_at = timezone.now() - timedelta(hours=25)
    chat.autoreplied_at = timezone.now() - timedelta(hours=11)
    chat.save()
    incoming(client, base)
    assert chat.messages.filter(automated=True).count() == 1
    chat.last_inbound_at = timezone.now() - timedelta(hours=25)
    chat.autoreplied_at = timezone.now() - timedelta(hours=13)
    chat.save()
    incoming(client, base)
    assert chat.messages.filter(automated=True).count() == 2


def test_scoped_webhook_cannot_route_payload_to_other_business(pilot):
    setup, client, base, channel = pilot
    from tapme.messaging.infrastructure.meta import encrypt

    other = ChannelAccount.objects.create(
        business=setup["other_business"],
        phone_number_id="111111111",
        waba_id="222222222",
        display_phone="+996700999999",
        token_encrypted=encrypt("other-token"),
        app_secret_encrypted=encrypt("other-secret"),
        provider_mode="fake",
    )
    body = json.dumps(
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "metadata": {"phone_number_id": other.phone_number_id},
                                "messages": [
                                    {
                                        "id": "forged",
                                        "type": "text",
                                        "from": "996700000555",
                                        "timestamp": str(int(timezone.now().timestamp())),
                                        "text": {"body": "Wrong channel"},
                                    }
                                ],
                            },
                        }
                    ]
                }
            ],
        }
    ).encode()
    signature = "sha256=" + hmac.new(b"private-secret", body, hashlib.sha256).hexdigest()
    url = f"/api/v1/webhooks/meta/whatsapp/{channel.webhook_key}/"
    assert (
        client.post(
            url, body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=signature
        ).status_code
        == 200
    )
    event = WebhookEvent.objects.get()
    process_event(event.digest)
    assert not Conversation.objects.exists()
    assert (
        client.post(
            f"/api/v1/webhooks/meta/whatsapp/{other.webhook_key}/",
            body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        ).status_code
        == 401
    )


def test_payment_qr_is_in_backup_reference_list(pilot, monkeypatch):
    from types import SimpleNamespace
    from zipfile import ZipFile

    from django.core.files.storage import storages
    from django.core.management import call_command

    from tapme.businesses.models import Shop
    from tapme.media.infrastructure.references import photo_is_referenced, photo_keys
    from tapme.media.management.commands import export_photos

    _, client, base, _ = pilot
    picture = io.BytesIO()
    Image.new("RGB", (50, 50), "black").save(picture, "PNG")
    response = client.post(
        base + "/channels/payment-qr/",
        {
            "version": 1,
            "note": "QR",
            "text": "{сумма}",
            "file": SimpleUploadedFile("qr.png", picture.getvalue(), content_type="image/png"),
        },
        format="multipart",
    )
    assert response.status_code == 200
    key = Shop.objects.exclude(payment_qr_key="").get().payment_qr_key
    assert key in photo_keys() and photo_is_referenced(key)
    output = io.BytesIO()
    monkeypatch.setattr(
        export_photos, "sys", SimpleNamespace(stdout=SimpleNamespace(buffer=output))
    )
    call_command("export_photos", stdout=io.StringIO())
    with ZipFile(io.BytesIO(output.getvalue())) as archive:
        assert key in archive.namelist()
        with storages["photos"].open(key) as file:
            assert archive.read(key) == file.read()


def test_unread_is_separate_from_waiting(pilot):
    _, client, base, _ = pilot
    chat = incoming(client, base)
    summary = client.get(base + "/chats/summary/").data
    assert summary["waiting"] == 1 and summary["unread"] == 1
    client.post(
        f"{base}/chats/{chat.id}/read/",
        {"last_message_id": chat.messages.filter(direction="in").get().id},
        format="json",
    )
    summary = client.get(base + "/chats/summary/").data
    assert summary["waiting"] == 1 and summary["unread"] == 0


def test_webhook_rejections_cannot_exhaust_signed_delivery_limit(pilot, monkeypatch, settings):
    from tapme.messaging.api import WebhookThrottle

    _, client, _, channel = pilot
    monkeypatch.setattr(WebhookThrottle, "rate", "2/min")
    settings.TRUST_PROXY = True
    headers = {"REMOTE_ADDR": "192.0.2.77", "HTTP_X_TAPME_CLIENT_IP": "198.51.100.7"}
    url = f"/api/v1/webhooks/meta/whatsapp/{channel.webhook_key}/"
    missing = "/api/v1/webhooks/meta/whatsapp/unknown/"
    assert client.get(missing, **headers).status_code == 404
    assert client.get(url, **headers).status_code == 403
    response = client.get(url, **headers)
    assert response.status_code == 429 and response["Retry-After"]
    assert (
        client.get(url, **{**headers, "HTTP_X_TAPME_CLIENT_IP": "198.51.100.8"}).status_code == 403
    )

    body = b'{"object":"whatsapp_business_account","entry":[]}'
    signature = "sha256=" + hmac.new(b"private-secret", body, hashlib.sha256).hexdigest()

    def send(signature):
        return client.post(
            url,
            body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
            **headers,
        )

    assert send("sha256=bad").status_code == 429
    assert not WebhookEvent.objects.exists()
    assert send(signature).status_code == 200
    assert send(signature).status_code == 200
    assert send(signature).status_code == 429
    assert WebhookEvent.objects.count() == 1
