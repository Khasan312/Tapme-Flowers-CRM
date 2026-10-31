import hashlib
import hmac
import json
from datetime import timedelta
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from django.db import transaction
from django.utils import timezone

from tapme.customers.models import CustomerRecord
from tapme.messaging.domain import DeliveryRejected, DeliveryUnknown
from tapme.messaging.infrastructure.meta import MetaGateway, encrypt
from tapme.messaging.infrastructure.processing import (
    deliver,
    delivery_status,
    process_event,
    receive,
)
from tapme.messaging.models import ChannelAccount, Conversation, Message, WebhookEvent


@pytest.fixture
def config(settings):
    settings.TAPME_META_MODE = "live"
    settings.META_APP_SECRET = "test-app-secret"
    settings.META_WEBHOOK_VERIFY_TOKEN = "test-verify-token"
    settings.META_GRAPH_VERSION = "v23.0"
    settings.TAPME_SECRETS_KEY = Fernet.generate_key().decode()


@pytest.fixture
def channel(setup, config):
    return ChannelAccount.objects.create(
        business=setup["business"],
        phone_number_id="123456789",
        display_phone="+996555555555",
        display_name="Магазин",
        token_encrypted=encrypt("test-token"),
    )


@pytest.fixture
def chat(channel, setup):
    return Conversation.objects.create(
        channel=channel,
        customer=setup["customer"],
        phone=setup["customer"].phone,
        last_inbound_at=timezone.now(),
        waiting_since=timezone.now(),
    )


def payload(channel, phone="996555123456", mid="wamid.in", text="Здравствуйте"):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": channel.phone_number_id},
                            "contacts": [{"wa_id": phone, "profile": {"name": "Айжан"}}],
                            "messages": [
                                {
                                    "id": mid,
                                    "from": phone,
                                    "type": "text",
                                    "text": {"body": text},
                                    "timestamp": str(int(timezone.now().timestamp())),
                                }
                            ],
                        },
                    }
                ]
            }
        ],
    }


def accept(data):
    body = json.dumps(data).encode()
    signature = "sha256=" + hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()
    assert receive(body, signature)
    event = WebhookEvent.objects.get(digest=hashlib.sha256(body).hexdigest())
    process_event(event.digest)
    return event


def test_webhook_signature_verified_before_dedupe_and_get_challenge(setup, channel):
    client = setup["client"]
    url = "/api/v1/webhooks/meta/whatsapp/"
    client.logout()
    assert (
        client.get(
            url, {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "123"}
        ).status_code
        == 403
    )
    assert (
        client.get(
            url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "test-verify-token",
                "hub.challenge": "123",
            },
        ).content
        == b"123"
    )
    data = payload(channel)
    body = json.dumps(data).encode()
    assert client.post(url, body, content_type="application/json").status_code == 401
    assert not WebhookEvent.objects.exists()
    assert (
        client.get(
            url, {"hub.mode": "subscribe", "hub.verify_token": "неверный", "hub.challenge": "123"}
        ).status_code
        == 403
    )
    sig = "sha256=" + hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()
    assert (
        client.post(
            url, body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=sig
        ).status_code
        == 200
    )
    assert Message.objects.count() == 0  # Inbox is committed before asynchronous processing.
    process_event(WebhookEvent.objects.get().digest)
    accept(data)
    assert Message.objects.count() == 1
    assert Conversation.objects.get().customer == setup["customer"]


def test_inbound_creates_client_without_consent_and_matches_additional_phone(setup, channel):
    accept(payload(channel, phone="996700000001"))
    customer = CustomerRecord.objects.get(phone="+996700000001")
    assert customer.name == "Айжан" and not customer.consent and customer.source == "WhatsApp"
    customer.additional_phones = ["+996700000002"]
    customer.save()
    accept(payload(channel, phone="996700000002", mid="two"))
    assert Conversation.objects.get(phone="+996700000002").customer == customer


def test_ambiguous_phone_requires_manual_link_without_exposing_unrelated_client(
    setup, channel, base
):
    one = setup["customer"]
    one.additional_phones = ["+996700000003"]
    one.save()
    two = CustomerRecord.objects.create(
        business=setup["business"],
        name="Другой",
        phone="+996700000004",
        additional_phones=["+996700000003"],
    )
    accept(payload(channel, phone="996700000003"))
    row = Conversation.objects.get()
    assert row.customer_id is None and row.needs_customer_link
    client = setup["client"]
    url = base + f"/chats/{row.id}/"
    data = client.get(url).json()
    assert data["customer"] is None and len(data["link_candidates"]) == 2
    assert (
        client.patch(
            url,
            {"version": row.version, "customer_id": str(setup["other_customer"].id)},
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.patch(
            url, {"version": row.version, "customer_id": str(two.id)}, format="json"
        ).status_code
        == 200
    )
    row.refresh_from_db()
    assert row.customer == two


def test_send_idempotency_window_and_permissions(setup, chat, base):
    c = setup["client"]
    url = base + f"/chats/{chat.id}/messages/"
    data = {"text": "Добрый день", "request_id": str(uuid4())}
    first = c.post(url, data, format="json")
    assert first.status_code == 200, first.content
    assert c.post(url, data, format="json").json()["id"] == first.json()["id"]
    assert Message.objects.count() == 1
    assert c.post(url, {**data, "text": "Другой текст"}, format="json").status_code == 409
    chat.last_inbound_at = timezone.now() - timedelta(hours=24)
    chat.save()
    assert (
        c.post(url, {"text": "Поздно", "request_id": str(uuid4())}, format="json").status_code
        == 400
    )
    for user in [setup["florist"], setup["other_owner"]]:
        c.force_login(user)
        assert c.get(url).status_code == 403
        assert c.post(url, data, format="json").status_code == 403
    c.force_login(setup["owner"])
    assert c.get(base + f"/chats/{uuid4()}/").status_code == 404


class Gateway:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def send(self, phone_id, token, data):
        self.calls.append(data)
        if self.error:
            raise self.error
        return "wamid.out"


def queued(setup, chat):
    return Message.objects.create(
        conversation=chat, direction="out", text="Ответ", sender=setup["owner"]
    )


def test_quoted_reply_delivery_idempotency_and_old_page_preview(setup, chat, base):
    original = Message.objects.create(
        conversation=chat,
        direction="in",
        status="received",
        external_id="wamid.original",
        text="Нужен белый букет",
    )
    url = base + f"/chats/{chat.id}/messages/"
    data = {"request_id": str(uuid4()), "text": "Да, приготовим", "reply_to_id": original.id}
    response = setup["client"].post(url, data, format="json")
    assert response.status_code == 200
    result = response.json()
    assert result["context_id"] == original.external_id
    assert result["reply_to"]["id"] == str(original.id)
    assert setup["client"].post(url, data, format="json").json()["id"] == result["id"]
    assert (
        setup["client"].post(url, {**data, "reply_to_id": None}, format="json").status_code == 409
    )
    gateway = Gateway()
    deliver(result["id"], gateway)
    deliver(result["id"], gateway)
    assert len(gateway.calls) == 1
    assert gateway.calls[0]["context"] == {"message_id": "wamid.original"}
    # The original can be outside the latest message page; its quote still renders.
    page = setup["client"].get(url, {"limit": 1}).json()
    assert len(page["results"]) == 1
    assert page["results"][0]["reply_to"]["text"] == "Нужен белый букет"
    # Replying to our own confirmed message also uses its provider ID.
    own_reply = setup["client"].post(
        url,
        {"request_id": str(uuid4()), "text": "Уточнение", "reply_to_id": result["id"]},
        format="json",
    )
    assert own_reply.status_code == 200
    assert own_reply.json()["context_id"] == "wamid.out"


@pytest.mark.parametrize(
    "source",
    ["another_chat", "another_business", "system", "queued", "missing_provider_id", "missing"],
)
def test_quoted_reply_rejects_inaccessible_or_unsent_source(setup, chat, base, source):
    other_channel = ChannelAccount.objects.create(
        business=setup["other_business"], phone_number_id="999999999"
    )
    other_chat = Conversation.objects.create(
        channel=chat.channel if source == "another_chat" else other_channel, phone="+996555111222"
    )
    original = Message.objects.create(
        conversation=other_chat if source in {"another_chat", "another_business"} else chat,
        direction="system" if source == "system" else "out" if source == "queued" else "in",
        status="queued" if source == "queued" else "received",
        external_id=None if source == "missing_provider_id" else "wamid.source",
        text="Приватный текст",
    )
    if source == "missing":
        source_id = original.id
        original.delete()
    else:
        source_id = original.id
    response = setup["client"].post(
        base + f"/chats/{chat.id}/messages/",
        {"text": "Ответ", "request_id": str(uuid4()), "reply_to_id": source_id},
        format="json",
    )
    assert response.status_code == 400
    assert "Приватный текст" not in str(response.json())
    assert not chat.messages.filter(text="Ответ").exists()


def test_reply_preview_is_scoped_and_reply_preserves_permissions(setup, chat, base):
    secret_chat = Conversation.objects.create(channel=chat.channel, phone="+996555111222")
    Message.objects.create(
        conversation=secret_chat, direction="in", external_id="wamid.secret", text="Чужая цитата"
    )
    row = Message.objects.create(
        conversation=chat,
        direction="in",
        status="received",
        external_id="wamid.reply",
        context_id="wamid.secret",
        text="Привет",
    )
    url = base + f"/chats/{chat.id}/messages/"
    assert setup["client"].get(url).json()["results"][0]["reply_to"] is None
    data = {"request_id": str(uuid4()), "text": "Ответ", "reply_to_id": row.id}
    setup["client"].force_login(setup["florist"])
    assert setup["client"].post(url, data, format="json").status_code == 403
    setup["client"].force_login(setup["owner"])
    chat.last_inbound_at = timezone.now() - timedelta(days=2)
    chat.save(update_fields=["last_inbound_at"])
    assert setup["client"].post(url, data, format="json").status_code == 400


def test_attachment_reply_and_retry_keep_context(setup, chat, base, settings, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from tapme.messaging.infrastructure.storage import DjangoAttachmentStorage

    settings.STORAGES = {
        **settings.STORAGES,
        "photos": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": tmp_path},
        },
    }
    original = Message.objects.create(
        conversation=chat,
        direction="in",
        status="received",
        external_id="wamid.photo-question",
        text="Покажите состав",
    )
    key = str(uuid4())

    def send(reply_id):
        return setup["client"].post(
            base + f"/chats/{chat.id}/attachments/",
            {
                "file": SimpleUploadedFile(
                    "bouquet.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"
                ),
                "request_id": key,
                "text": "Состав",
                "reply_to_id": reply_id,
            },
            format="multipart",
        )

    response = send(original.id)
    assert response.status_code == 200
    result = response.json()
    assert send(original.id).json()["id"] == result["id"]
    assert send(original.id + 999).status_code == 409
    assert len([path for path in tmp_path.rglob("*") if path.is_file()]) == 1

    class FilesGateway(Gateway):
        def upload(self, *args):
            return "media-id"

    storage = DjangoAttachmentStorage()
    deliver(result["id"], FilesGateway(DeliveryRejected("Отказ")), storage)
    assert (
        setup["client"].post(base + f"/chats/{chat.id}/messages/{result['id']}/retry/").status_code
        == 200
    )
    gateway = FilesGateway()
    deliver(result["id"], gateway, storage)
    assert gateway.calls[0]["context"] == {"message_id": original.external_id}
    assert gateway.calls[0]["document"]["caption"] == "Состав"


def test_outbox_delivers_once_and_delivery_receipts_never_regress(setup, chat):
    row = queued(setup, chat)
    gateway = Gateway()
    deliver(row.id, gateway)
    deliver(row.id, gateway)
    assert len(gateway.calls) == 1
    assert gateway.calls[0]["biz_opaque_callback_data"] == str(row.delivery_key)
    for status in ["read", "sent", "delivered", "failed"]:
        with transaction.atomic():
            delivery_status(chat.channel, {"id": "wamid.out", "status": status})
    row.refresh_from_db()
    assert row.status == "read"
    chat.refresh_from_db()
    assert chat.waiting_since is None


def test_lost_response_is_not_resent_and_callback_can_reconcile(setup, chat, base):
    row = queued(setup, chat)
    gateway = Gateway(DeliveryUnknown("Timeout"))
    deliver(row.id, gateway)
    deliver(row.id, gateway)
    row.refresh_from_db()
    assert row.status == "unknown" and len(gateway.calls) == 1
    assert (
        setup["client"].post(base + f"/chats/{chat.id}/messages/{row.id}/retry/").status_code == 409
    )
    from django.db import transaction

    with transaction.atomic():
        delivery_status(
            chat.channel,
            {
                "id": "late-wamid",
                "status": "delivered",
                "biz_opaque_callback_data": str(row.delivery_key),
                "recipient_id": chat.phone.lstrip("+"),
            },
        )
    row.refresh_from_db()
    assert row.status == "delivered" and row.external_id == "late-wamid"


def test_rejected_message_can_be_retried_but_worker_rechecks_access(setup, chat, base):
    row = queued(setup, chat)
    deliver(row.id, Gateway(DeliveryRejected("Отказ")))
    url = base + f"/chats/{chat.id}/messages/{row.id}/retry/"
    assert setup["client"].post(url).status_code == 200
    setup["owner"].is_active = False
    setup["owner"].save()
    gateway = Gateway()
    deliver(row.id, gateway)
    row.refresh_from_db()
    assert row.status == "failed" and not gateway.calls


def test_missing_local_attachment_fails_before_any_provider_call(setup, chat):
    from tapme.shared.domain import NotFound

    class MissingStorage:
        def read(self, key):
            raise NotFound("Вложение не найдено.")

    class FilesGateway(Gateway):
        def upload(self, *args):
            pytest.fail("Missing file must never be uploaded")

    row = queued(setup, chat)
    row.media_key, row.media_type, row.kind = "missing.jpg", "image/jpeg", "image"
    row.save()
    gateway = FilesGateway()
    deliver(row.id, gateway, MissingStorage())
    row.refresh_from_db()
    assert row.status == "failed" and not gateway.calls


def test_unread_per_employee_marks_only_visible_messages(setup, chat, base):
    one = Message.objects.create(
        conversation=chat, direction="in", text="Первое", status="received"
    )
    two = Message.objects.create(
        conversation=chat, direction="in", text="Второе", status="received"
    )
    c = setup["client"]
    assert c.get(base + f"/chats/{chat.id}/").json()["unread"] == 2
    assert (
        c.post(
            base + f"/chats/{chat.id}/read/", {"last_message_id": one.id}, format="json"
        ).status_code
        == 200
    )
    assert c.get(base + f"/chats/{chat.id}/").json()["unread"] == 1
    c.force_login(setup["manager"])
    assert c.get(base + f"/chats/{chat.id}/").json()["unread"] == 2
    assert c.get(base + f"/chats/{chat.id}/messages/?before={two.id}").json()["results"][0][
        "id"
    ] == str(one.id)


def test_manual_assignment_version_and_optout(setup, channel, base):
    accept(payload(channel, text="Стоп"))
    chat = Conversation.objects.get()
    c = setup["client"]
    url = base + f"/chats/{chat.id}/"
    assert not c.get(url).json()["can_reply"]
    data = {"version": chat.version, "assigned_to": str(setup["manager"].id)}
    assert c.patch(url, data, format="json").status_code == 200
    assert c.patch(url, data, format="json").status_code == 409
    chat.refresh_from_db()
    assert (
        c.patch(
            url,
            {"version": chat.version, "assigned_to": str(setup["other_owner"].id)},
            format="json",
        ).status_code
        == 400
    )


def test_channel_credentials_hidden_encrypted_and_owner_only(setup, base, config, monkeypatch):
    monkeypatch.setattr(
        MetaGateway,
        "inspect",
        lambda self, phone_id, token: {
            "id": phone_id,
            "display_phone_number": "+996555000000",
            "verified_name": "Магазин",
        },
    )
    c = setup["client"]
    url = base + "/channels/whatsapp/"
    data = {"phone_number_id": "123456789", "token": "sensitive-token"}
    c.force_login(setup["manager"])
    assert c.post(url, data, format="json").status_code == 403
    c.force_login(setup["owner"])
    assert c.post(url, data, format="json").status_code == 200
    assert b"sensitive-token" not in c.get(url).content
    assert ChannelAccount.objects.get().token_encrypted != data["token"]
    assert c.delete(url).status_code == 200
    assert ChannelAccount.objects.get().token_encrypted == ""


def test_disconnected_channel_does_not_import_messages(setup, channel):
    channel.status = "disconnected"
    channel.save()
    accept(payload(channel))
    assert not Message.objects.exists()


def test_photo_upload_idempotency_private_access_and_local_backup_reference(
    setup, chat, base, settings, tmp_path
):
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    from tapme.media.infrastructure.references import photo_is_referenced, photo_keys

    settings.STORAGES = {
        **settings.STORAGES,
        "photos": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": tmp_path},
        },
    }
    out = BytesIO()
    Image.new("RGB", (20, 20), "purple").save(out, format="PNG")
    content = out.getvalue()
    key = str(uuid4())

    def send():
        return setup["client"].post(
            base + f"/chats/{chat.id}/attachments/",
            {
                "file": SimpleUploadedFile("bouquet.png", content, content_type="image/png"),
                "request_id": key,
                "text": "Букет готов",
            },
            format="multipart",
        )

    first = send()
    assert first.status_code == 200, first.content
    assert send().json()["id"] == first.json()["id"]
    row = Message.objects.get()
    assert row.media_type == "image/jpeg" and photo_is_referenced(row.media_key)
    assert row.media_key in list(photo_keys(chat.channel.business_id))
    response = setup["client"].get(first.json()["media_url"])
    assert response.status_code == 200 and response["Cache-Control"] == "private, no-store"
    assert len(list(tmp_path.rglob("*.jpg"))) == 1
    setup["client"].force_login(setup["other_owner"])
    assert setup["client"].get(first.json()["media_url"]).status_code == 403


def test_incoming_attachment_saved_without_exposing_provider_url(setup, chat, settings, tmp_path):
    from tapme.messaging.infrastructure.processing import fetch_attachment
    from tapme.messaging.infrastructure.storage import DjangoAttachmentStorage

    settings.STORAGES = {
        **settings.STORAGES,
        "photos": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": tmp_path},
        },
    }
    row = Message.objects.create(
        conversation=chat,
        direction="in",
        kind="document",
        text="Чек",
        status="received",
        payload={"id": "123", "filename": "receipt.pdf"},
    )

    class Files:
        def download(self, *args):
            return b"%PDF-1.4\nexample", "application/pdf"

    fetch_attachment(row.id, Files(), DjangoAttachmentStorage())
    row.refresh_from_db()
    assert row.media_key and row.media_type == "application/pdf" and not row.error
    fetch_attachment(row.id, Files(), DjangoAttachmentStorage())
    assert len([p for p in tmp_path.rglob("*") if p.is_file()]) == 1


@pytest.mark.parametrize(
    "metadata",
    [
        {"url": "https://example.org/private"},
        {"url": "https://lookaside.fbsbx.com:invalid/private"},
        {"url": "https://lookaside.fbsbx.com/private", "file_size": "invalid"},
    ],
)
def test_meta_media_rejects_untrusted_url_without_forwarding_token(config, monkeypatch, metadata):
    gateway = MetaGateway()
    monkeypatch.setattr(
        gateway,
        "_request",
        lambda *a, **kw: {**metadata, "mime_type": "image/jpeg"},
    )
    with pytest.raises(DeliveryRejected):
        gateway.download("12345", "secret-token", "123")


def test_old_attempt_receipt_cannot_change_retried_message(setup, chat, base):
    row = queued(setup, chat)
    old_key = str(row.delivery_key)
    deliver(row.id, Gateway(DeliveryRejected("Rejected")))
    assert (
        setup["client"].post(base + f"/chats/{chat.id}/messages/{row.id}/retry/").status_code == 200
    )
    with transaction.atomic():
        delivery_status(
            chat.channel,
            {
                "id": "old-wamid",
                "status": "failed",
                "biz_opaque_callback_data": old_key,
                "recipient_id": chat.phone.lstrip("+"),
            },
        )
    row.refresh_from_db()
    assert row.status == "queued" and str(row.delivery_key) != old_key


def test_periodic_worker_downloads_first_attachment_without_attempt_counter(
    setup, chat, settings, tmp_path, monkeypatch
):
    from tapme.messaging.tasks import process_messages

    settings.STORAGES = {
        **settings.STORAGES,
        "photos": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": tmp_path},
        },
    }
    row = Message.objects.create(
        conversation=chat,
        direction="in",
        kind="document",
        text="Чек",
        status="received",
        payload={"id": "123", "filename": "receipt.pdf"},
    )
    monkeypatch.setattr(
        MetaGateway, "download", lambda *args: (b"%PDF-1.4\ntest", "application/pdf")
    )
    process_messages()
    row.refresh_from_db()
    assert row.media_key
