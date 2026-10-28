import hashlib
import hmac
import json
from datetime import timedelta
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from django.utils import timezone

from tapme.messaging.infrastructure.meta import InstagramGateway, decrypt
from tapme.messaging.infrastructure.processing import PendingReceipt, deliver, process_event
from tapme.messaging.models import ChannelAccount, ChatFolder, Conversation, Message, WebhookEvent


@pytest.fixture
def instagram(setup, settings):
    settings.DEBUG = True
    settings.TAPME_META_MODE = "fake"
    settings.TAPME_SECRETS_KEY = Fernet.generate_key().decode()
    client = setup["client"]
    base = f"/api/v1/businesses/{setup['business'].id}"
    response = client.post(
        base + "/channels/instagram/",
        {
            "ig_user_id": "17841441378837829",
            "token": "private-ig-token",
            "app_secret": "private-ig-secret",
            "version": 0,
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    channel = ChannelAccount.objects.get(business=setup["business"], kind="instagram")
    return setup, client, base, channel


def post_event(client, channel, event, entry_id=None):
    body = json.dumps(
        {
            "object": "instagram",
            "entry": [{"id": entry_id or channel.ig_user_id, "messaging": [event]}],
        }
    ).encode()
    signature = "sha256=" + hmac.new(b"private-ig-secret", body, hashlib.sha256).hexdigest()
    response = client.post(
        f"/api/v1/webhooks/meta/instagram/{channel.webhook_key}/",
        body,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=signature,
    )
    assert response.status_code == 200, response.content
    row = WebhookEvent.objects.latest("received_at")
    process_event(row.digest)
    return row


def incoming(client, channel, mid="mid.in.1", peer="98888888888888888"):
    post_event(
        client,
        channel,
        {
            "sender": {"id": peer},
            "recipient": {"id": channel.ig_user_id},
            "timestamp": int(timezone.now().timestamp() * 1000),
            "message": {"mid": mid, "text": "Здравствуйте! Нужен букет"},
        },
    )
    return Conversation.objects.get(channel=channel, external_user_id=peer)


def test_connection_is_separate_and_secrets_are_private(instagram):
    setup, client, base, channel = instagram
    wa = client.post(
        base + "/channels/whatsapp/",
        {
            "phone_number_id": "123456789",
            "waba_id": "987654321",
            "token": "wa-token",
            "app_secret": "wa-secret",
        },
        format="json",
    )
    assert wa.status_code == 200, wa.data
    assert ChannelAccount.objects.filter(business=setup["business"]).count() == 2
    assert channel.phone_number_id is None and channel.display_phone == ""
    assert decrypt(channel.token_encrypted) == "private-ig-token"
    result = client.get(base + "/channels/instagram/").data
    assert "private-ig-token" not in str(result) and "private-ig-secret" not in str(result)
    assert "token_encrypted" not in result
    client.force_login(setup["manager"])
    result = client.get(base + "/channels/instagram/").data
    assert "verify_token" not in result and "webhook_path" not in result
    for method, path in [
        (client.post, ""),
        (client.delete, ""),
        (client.post, "/check"),
        (client.post, "/subscribe"),
    ]:
        assert (
            method(
                base + "/channels/instagram" + path + "/",
                {
                    "ig_user_id": channel.ig_user_id,
                    "token": "private-ig-token",
                    "app_secret": "private-ig-secret",
                    "version": channel.version,
                }
                if method == client.post and not path
                else {},
                format="json",
            ).status_code
            == 403
        )
    client.force_login(setup["other_owner"])
    assert client.get(base + "/channels/instagram/").status_code == 403


def test_webhook_signature_channel_routing_and_verification(instagram):
    _, client, base, channel = instagram
    path = f"/api/v1/webhooks/meta/instagram/{channel.webhook_key}/"
    assert (
        client.get(path, {"hub.mode": "subscribe", "hub.verify_token": "wrong"}).status_code == 403
    )
    assert (
        client.post(
            path, b"{}", content_type="application/json", HTTP_X_HUB_SIGNATURE_256="sha256=invalid"
        ).status_code
        == 401
    )
    assert not WebhookEvent.objects.exists()
    assert client.get(path.replace("instagram", "whatsapp")).status_code == 404
    assert (
        client.post(base + "/channels/instagram/subscribe/", {}, format="json").status_code == 400
    )
    response = client.get(
        path,
        {
            "hub.mode": "subscribe",
            "hub.verify_token": channel.verify_token,
            "hub.challenge": "challenge",
        },
    )
    assert response.content == b"challenge"
    assert (
        client.post(base + "/channels/instagram/subscribe/", {}, format="json").status_code == 200
    )
    channel.refresh_from_db()
    assert channel.webhook_verified_at and channel.subscribed_at


def test_inbound_dedupe_identity_lists_and_folders(instagram):
    setup, client, base, channel = instagram
    chat = incoming(client, channel)
    incoming(client, channel)
    second = incoming(client, channel, "mid.in.2", "97777777777777777")
    assert chat.phone == second.phone == "" and not chat.customer_id
    assert chat.messages.count() == 1 and not chat.messages.filter(automated=True).exists()
    assert client.get(base + "/chats/").data["count"] == 0
    response = client.get(base + "/chats/?channel_kind=instagram").data
    assert response["count"] == 2 and response["results"][0]["channel_kind"] == "instagram"
    assert all(row["external_user_id"] and row["phone"] == "" for row in response["results"])
    folder = ChatFolder.objects.create(
        business=setup["business"], name="Клиенты", name_key="клиенты"
    )
    folder.conversations.add(chat)
    assert (
        client.get(base + "/chat-folders/?channel_kind=instagram").data["results"][0]["count"] == 1
    )
    assert client.get(base + "/chat-folders/").data["results"][0]["count"] == 0
    summary = client.get(base + "/chats/summary/").data
    assert summary["unread_by_channel"]["instagram"] == 2
    assert summary["items"][0]["channel_kind"] == "instagram"


def test_foreign_entry_or_recipient_does_not_create_chat(instagram):
    _, client, _, channel = instagram
    event = {
        "sender": {"id": "98888888888888888"},
        "recipient": {"id": channel.ig_user_id},
        "message": {"mid": "mid.other", "text": "test"},
    }
    post_event(client, channel, event, entry_id="9999999999")
    event["recipient"]["id"] = "9999999999"
    post_event(client, channel, event)
    assert not Conversation.objects.exists()


def test_send_reply_and_echo_are_one_message(instagram):
    _, client, base, channel = instagram
    chat = incoming(client, channel)
    original = chat.messages.get()
    request_id = str(uuid4())
    payload = {"text": "Здравствуйте!", "request_id": request_id, "reply_to_id": original.id}
    response = client.post(f"{base}/chats/{chat.id}/messages/", payload, format="json")
    assert response.status_code == 200, response.data
    assert (
        client.post(f"{base}/chats/{chat.id}/messages/", payload, format="json").data["id"]
        == response.data["id"]
    )
    row = Message.objects.get(id=response.data["id"])

    class Capture:
        def send(self, account_id, token, body):
            assert account_id == channel.ig_user_id
            assert body == {
                "recipient": {"id": chat.external_user_id},
                "message": {"text": payload["text"]},
                "reply_to": {"mid": original.external_id},
            }
            assert "messaging_product" not in body and "to" not in body
            return "mid.out.1"

    deliver(row.id, Capture())
    post_event(
        client,
        channel,
        {
            "sender": {"id": channel.ig_user_id},
            "recipient": {"id": chat.external_user_id},
            "timestamp": int(timezone.now().timestamp() * 1000),
            "message": {"mid": "mid.out.1", "text": payload["text"], "is_echo": True},
        },
    )
    assert chat.messages.filter(direction="out").count() == 1
    post_event(
        client,
        channel,
        {
            "sender": {"id": chat.external_user_id},
            "recipient": {"id": channel.ig_user_id},
            "read": {"mid": "mid.out.1"},
        },
    )
    row.refresh_from_db()
    assert row.status == "read"
    assert client.get(base + "/channels/instagram/").data["checks"]["first_reply_sent"]


def test_text_limit_customer_link_and_tenant_boundaries(instagram):
    setup, client, base, channel = instagram
    chat = incoming(client, channel)
    response = client.post(
        f"{base}/chats/{chat.id}/messages/",
        {"text": "я" * 501, "request_id": str(uuid4())},
        format="json",
    )
    assert response.status_code == 400 and "1000" in str(response.data)
    response = client.patch(
        f"{base}/chats/{chat.id}/",
        {"version": chat.version, "customer_id": str(setup["other_customer"].id)},
        format="json",
    )
    assert response.status_code == 400
    response = client.patch(
        f"{base}/chats/{chat.id}/",
        {"version": chat.version, "customer_id": str(setup["customer"].id)},
        format="json",
    )
    assert response.status_code == 200, response.data
    chat.refresh_from_db()
    assert chat.customer_id == setup["customer"].id and chat.phone == ""
    client.force_login(setup["other_owner"])
    assert client.get(f"{base}/chats/{chat.id}/").status_code == 403


def test_disconnect_preserves_history_and_rejects_queued_send(instagram):
    _, client, base, channel = instagram
    chat = incoming(client, channel)
    row = Message.objects.create(conversation=chat, direction="out", text="test")
    assert client.delete(base + "/channels/instagram/").status_code == 200
    channel.refresh_from_db()
    row.refresh_from_db()
    assert (
        not channel.token_encrypted and not channel.app_secret_encrypted and row.status == "failed"
    )
    assert Conversation.objects.filter(id=chat.id).exists() and chat.messages.count() == 2
    assert client.get(f"{base}/chats/{chat.id}/").data["can_reply"] is False
    assert client.get(f"/api/v1/webhooks/meta/instagram/{channel.webhook_key}/").status_code == 404


def test_gateway_uses_instagram_contract(monkeypatch):
    calls = []

    def capture(self, path, token, payload=None):
        calls.append((path, payload))
        return {"id": "12345", "username": "flowers", "success": True, "message_id": "mid.123"}

    monkeypatch.setattr(InstagramGateway, "_request", capture)
    gateway = InstagramGateway()
    assert gateway.inspect("12345", "token")["username"] == "flowers"
    gateway.subscribe("12345", "token")
    assert (
        gateway.send("12345", "token", {"recipient": {"id": "67890"}, "message": {"text": "Hi"}})
        == "mid.123"
    )
    assert calls[1] == ("12345/subscribed_apps", {"subscribed_fields": "messages,messaging_seen"})


def test_echo_waits_for_in_flight_response(instagram):
    _, client, _, channel = instagram
    chat = incoming(client, channel)
    row = Message.objects.create(conversation=chat, direction="out", text="Ответ", status="sending")
    with pytest.raises(PendingReceipt):
        post_event(
            client,
            channel,
            {
                "sender": {"id": channel.ig_user_id},
                "recipient": {"id": chat.external_user_id},
                "timestamp": int(timezone.now().timestamp() * 1000),
                "message": {"mid": "mid.race", "is_echo": True, "text": "Ответ"},
            },
        )
    row.external_id = "mid.race"
    row.status = "sent"
    row.save()
    process_event(WebhookEvent.objects.latest("received_at").digest)
    assert chat.messages.filter(direction="out").count() == 1


def test_instagram_draft_uses_linked_customer_and_preserves_source(instagram):
    from tapme.orders.models import OrderRecord

    setup, client, base, channel = instagram
    chat = incoming(client, channel)
    url = f"{base}/chats/{chat.id}/order-draft/"
    assert client.post(url, {}, format="json").status_code == 400
    chat.customer = setup["customer"]
    chat.save(update_fields=["customer"])
    response = client.post(url, {}, format="json")
    assert response.status_code == 200, response.data
    draft = response.data["draft"]
    assert draft["fields"]["recipient_phone"] == setup["customer"].phone
    fields = {
        **draft["fields"],
        "items": [{"kind": "product", "product_id": str(setup["product"].id), "quantity": 1}],
        "date": (timezone.now() + timedelta(days=5)).date().isoformat(),
        "window": {"start": "10:00", "end": "12:00"},
        "fulfillment": "pickup",
    }
    response = client.put(
        url, {"draft_id": draft["id"], "version": draft["version"], "fields": fields}, format="json"
    )
    assert response.status_code == 200, response.data
    draft = response.data["draft"]
    response = client.post(
        url + "convert/", {"draft_id": draft["id"], "version": draft["version"]}, format="json"
    )
    assert response.status_code == 200, response.data
    order = OrderRecord.objects.get(customer=setup["customer"])
    assert order.source == "instagram"
