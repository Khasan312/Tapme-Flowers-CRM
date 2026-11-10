from uuid import uuid4

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tapme.businesses.application.contracts import Scope
from tapme.messaging.infrastructure.repository import DjangoChatRepository
from tapme.messaging.models import ChannelAccount, Conversation, ConversationRead, Message


def test_chat_listing_queries_do_not_grow_with_the_number_of_chats(setup):
    channel = ChannelAccount.objects.create(
        business=setup["business"], phone_number_id="performance"
    )
    Conversation.objects.bulk_create(
        [Conversation(channel=channel, phone=f"+996555{i:06d}") for i in range(50)]
    )
    scope = Scope(setup["owner"].id, setup["business"].id)
    with CaptureQueriesContext(connection) as queries:
        result = DjangoChatRepository(None).listing(scope)
    assert len(result["results"]) == 50
    assert len(queries) <= 6, f"50 chats required {len(queries)} SQL queries"
    print(f"50-chat listing: {len(queries)} SQL queries")


@pytest.fixture
def performance_chat(setup):
    channel = ChannelAccount.objects.create(business=setup["business"], phone_number_id="sync")
    return Conversation.objects.create(
        channel=channel, customer=setup["customer"], phone="+996555123456"
    )


def test_bulk_unread_counts_preserve_user_scope_and_pagination(setup, performance_chat):
    chat = performance_chat
    first = Message.objects.create(
        conversation=chat, direction="in", text="Один", status="received"
    )
    second = Message.objects.create(
        conversation=chat, direction="in", text="Два", status="received"
    )
    Message.objects.create(conversation=chat, direction="out", text="Ответ", status="sent")
    ConversationRead.objects.create(
        conversation=chat, user=setup["owner"], last_message_id=first.id
    )
    ConversationRead.objects.create(
        conversation=chat, user=setup["manager"], last_message_id=second.id
    )
    repo = DjangoChatRepository(None)
    scope = Scope(setup["owner"].id, setup["business"].id)
    assert repo.listing(scope)["results"][0]["unread"] == 1
    assert repo.listing(Scope(setup["manager"].id, scope.business_id))["results"][0]["unread"] == 0
    ConversationRead.objects.filter(user=setup["owner"]).delete()
    assert repo.listing(scope)["results"][0]["unread"] == 2
    assert repo.summary(scope)["unread"] == 2
    assert repo.listing(scope, offset=50)["results"] == []


def test_unchanged_message_window_avoids_full_history_queries(setup, performance_chat, base):
    chat = performance_chat
    Message.objects.bulk_create(
        [
            Message(
                conversation=chat,
                direction="in",
                text="Длинное сообщение " * 100,
                status="received",
            )
            for _ in range(60)
        ]
    )
    repo = DjangoChatRepository(None)
    scope = Scope(setup["owner"].id, setup["business"].id)
    original = repo.messages(scope, chat.id)
    assert len(original["results"]) == 50 and original["has_more"]
    with CaptureQueriesContext(connection) as queries:
        current = repo.messages(scope, chat.id, cursor=original["cursor"])
    assert current["unchanged"] and current["results"] == [] and current["has_more"]
    assert current["conversation_cursor"] == original["conversation_cursor"]
    assert len(queries) == 2
    url = f"{base}/chats/{chat.id}/messages/"
    assert setup["client"].get(url, {"cursor": "invalid"}).status_code == 400
    assert setup["client"].get(url, {"cursor": original["cursor"]}).data["unchanged"]
    chat.mode = "closed"
    chat.version += 1
    chat.save()
    current = repo.messages(scope, chat.id, cursor=original["cursor"])
    assert (
        current["unchanged"] and current["conversation_cursor"] != original["conversation_cursor"]
    )


def test_message_cursor_detects_new_messages_status_and_download_changes(setup, performance_chat):
    repo = DjangoChatRepository(None)
    scope = Scope(setup["owner"].id, setup["business"].id)
    chat = performance_chat
    cursor = repo.messages(scope, chat.id)["cursor"]
    message = Message.objects.create(
        conversation=chat, direction="out", text="Фото", kind="image", status="queued"
    )
    for status in ["queued", "sending", "sent", "delivered", "read"]:
        message.status = status
        message.save()
        result = repo.messages(scope, chat.id, cursor=cursor)
        assert not result["unchanged"] and result["results"][-1]["status"] == status
        cursor = result["cursor"]
    message.media_key = "test/photo.jpg"
    message.media_type = "image/jpeg"
    message.save()
    result = repo.messages(scope, chat.id, cursor=cursor)
    assert not result["unchanged"] and result["results"][-1]["media_url"]
    empty_page = repo.messages(scope, chat.id, after=message.id)
    assert empty_page["results"] == [] and not empty_page["has_more"]


def test_cursor_includes_quoted_source_outside_page_and_preserves_access(
    setup, performance_chat, base
):
    chat = performance_chat
    original = Message.objects.create(
        conversation=chat,
        direction="in",
        text="Оригинал",
        external_id="original",
        status="received",
    )
    Message.objects.bulk_create(
        [
            Message(conversation=chat, direction="in", text="Сообщение", status="received")
            for _ in range(51)
        ]
    )
    Message.objects.create(
        conversation=chat, direction="out", text="Ответ", context_id="original", status="sent"
    )
    repo = DjangoChatRepository(None)
    scope = Scope(setup["owner"].id, setup["business"].id)
    first = repo.messages(scope, chat.id)
    assert first["results"][-1]["reply_to"]["text"] == "Оригинал"
    assert repo.messages(scope, chat.id, cursor=first["cursor"])["unchanged"]
    original.text = "Уточнённый оригинал"
    original.save()
    result = repo.messages(scope, chat.id, cursor=first["cursor"])
    assert not result["unchanged"] and result["results"][-1]["reply_to"]["text"] == original.text
    url = f"{base}/chats/{uuid4()}/messages/"
    assert setup["client"].get(url, {"cursor": first["cursor"]}).status_code == 404
    setup["client"].force_login(setup["other_owner"])
    assert (
        setup["client"]
        .get(f"{base}/chats/{chat.id}/messages/", {"cursor": first["cursor"]})
        .status_code
        == 403
    )


def test_repeated_read_marker_does_not_write_again(setup, performance_chat):
    chat = performance_chat
    message = Message.objects.create(
        conversation=chat,
        direction="in",
        text="Прочитано",
        status="received",
        external_id="read-test",
    )
    repo = DjangoChatRepository(None)
    scope = Scope(setup["owner"].id, setup["business"].id)
    repo.read(scope, chat.id, message.id)
    with CaptureQueriesContext(connection) as queries:
        assert repo.read(scope, chat.id, message.id) == {"ok": True}
    assert not any(q["sql"].lstrip().startswith(("UPDATE", "INSERT")) for q in queries)
    new = Message.objects.create(
        conversation=chat, direction="in", text="Ещё не показано", status="received"
    )
    repo.read(scope, chat.id, message.id)
    assert repo.listing(scope)["results"][0]["unread"] == 1
    assert ConversationRead.objects.get(user=setup["owner"]).last_message_id < new.id
