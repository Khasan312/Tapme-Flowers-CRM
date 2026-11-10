from uuid import uuid4

import pytest
from django.utils import timezone

from tapme.messaging.models import ChannelAccount, ChatFolder, Conversation, Message


@pytest.fixture
def folder_chat(setup):
    channel = ChannelAccount.objects.create(
        business=setup["business"],
        phone_number_id="folder-test",
        display_phone="+996555000001",
        display_name="Папки",
        token_encrypted="",
        provider_mode="fake",
    )
    return Conversation.objects.create(
        channel=channel,
        customer=setup["customer"],
        phone=setup["customer"].phone,
        last_inbound_at=timezone.now(),
        waiting_since=timezone.now(),
        assigned_to=setup["owner"],
    )


def create(client, base, name):
    response = client.post(base + "/chat-folders/", {"name": name}, format="json")
    assert response.status_code == 200, response.data
    return response.data


def test_shared_folder_crud_multi_membership_and_safe_delete(setup, base, folder_chat):
    client = setup["client"]
    first = create(client, base, "  Клиенты  ")
    second = create(client, base, "Ждём оплату")
    url = f"{base}/chats/{folder_chat.id}/"
    message = Message.objects.create(
        conversation=folder_chat, direction="in", text="Тест", status="received"
    )
    response = client.put(
        url + "folders/", {"version": 1, "folder_ids": [first["id"], second["id"]]}, format="json"
    )
    assert response.status_code == 200
    assert set(response.data["folder_ids"]) == {first["id"], second["id"]}
    assert response.data["version"] == 2
    assert client.get(base + "/chat-folders/").data["results"][0]["count"] == 1
    # A second manager sees the same organization, persisted on the server.
    client.force_login(setup["manager"])
    assert len(client.get(base + "/chat-folders/").data["results"]) == 2
    renamed = client.patch(
        f"{base}/chat-folders/{first['id']}/",
        {"name": "Постоянные клиенты", "version": 1},
        format="json",
    )
    assert renamed.status_code == 200
    conflict = client.delete(f"{base}/chat-folders/{first['id']}/", {"version": 1}, format="json")
    assert conflict.status_code == 409
    deleted = client.delete(f"{base}/chat-folders/{first['id']}/", {"version": 2}, format="json")
    assert deleted.status_code == 200
    assert Conversation.objects.filter(id=folder_chat.id).exists()
    assert Message.objects.filter(id=message.id).exists()
    assert client.get(url).data["folder_ids"] == [second["id"]]
    assert client.get(base + "/chats/").data["count"] == 1


def test_folder_filter_stats_archive_and_remove_membership(setup, base, folder_chat):
    client = setup["client"]
    folder = create(client, base, "Клиенты")
    folder_chat.folders.add(folder["id"])
    closed = Conversation.objects.create(
        channel=folder_chat.channel, phone="+996555000009", mode="closed"
    )
    closed.folders.add(folder["id"])
    Conversation.objects.create(channel=folder_chat.channel, phone="+996555000008")
    data = client.get(base + "/chats/", {"folder_id": folder["id"]}).data
    assert data["count"] == 1
    assert data["stats"] == {"all": 1, "waiting": 1, "mine": 1, "closed": 1}
    assert client.get(base + "/chats/", {"folder_id": folder["id"], "category": "closed"}).data[
        "results"
    ][0]["id"] == str(closed.id)
    assert (
        client.get(base + "/chats/", {"folder_id": folder["id"], "search": "несуществующий"}).data[
            "count"
        ]
        == 0
    )
    assert client.get(base + "/chat-folders/").data == {
        "all_count": 2,
        "results": [{**folder, "count": 1, "total": 2}],
    }
    url = f"{base}/chats/{folder_chat.id}/folders/"
    assert client.put(url, {"version": 999, "folder_ids": []}, format="json").status_code == 409
    assert client.put(url, {"version": 1, "folder_ids": []}, format="json").status_code == 200
    assert client.get(base + "/chats/", {"folder_id": folder["id"]}).data["count"] == 0
    assert client.get(base + "/chats/").data["count"] == 2


def test_folder_tenant_role_and_membership_isolation(setup, base, folder_chat):
    client = setup["client"]
    foreign = ChatFolder.objects.create(
        business=setup["other_business"], name="Чужая", name_key="чужая"
    )
    own = create(client, base, "Своя")
    assert client.get(base + "/chat-folders/").data["results"] == [own]
    foreign_url = f"{base}/chat-folders/{foreign.id}/"
    assert (
        client.patch(foreign_url, {"version": 1, "name": "Взлом"}, format="json").status_code == 404
    )
    assert client.delete(foreign_url, {"version": 1}, format="json").status_code == 404
    assert client.get(base + "/chats/", {"folder_id": str(foreign.id)}).status_code == 404
    assert (
        client.put(
            f"{base}/chats/{folder_chat.id}/folders/",
            {"version": 1, "folder_ids": [own["id"], str(foreign.id)]},
            format="json",
        ).status_code
        == 400
    )
    folder_chat.refresh_from_db()
    assert folder_chat.version == 1 and folder_chat.folders.count() == 0
    client.force_login(setup["other_owner"])
    assert client.get(base + "/chat-folders/").status_code == 403
    client.force_login(setup["florist"])
    assert (
        client.post(base + "/chat-folders/", {"name": "Нельзя"}, format="json").status_code == 403
    )


def test_folder_validation_duplicates_and_quota(setup, base, folder_chat):
    client = setup["client"]
    create(client, base, "Клиенты")
    for name in ["кЛИЕНТЫ", "  ", "a" * 41]:
        assert (
            client.post(base + "/chat-folders/", {"name": name}, format="json").status_code == 400
        )
    second = create(client, base, "Ждём оплату")
    assert (
        client.patch(
            f"{base}/chat-folders/{second['id']}/", {"version": 1, "name": "КЛИЕНТЫ"}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"{base}/chat-folders/{second['id']}/", {"name": "Название"}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"{base}/chats/{folder_chat.id}/folders/",
            {"version": 1, "folder_ids": [str(uuid4())]},
            format="json",
        ).status_code
        == 400
    )
    ChatFolder.objects.bulk_create(
        [
            ChatFolder(business=setup["business"], name=f"Папка {i}", name_key=f"папка {i}")
            for i in range(28)
        ]
    )
    assert (
        client.post(base + "/chat-folders/", {"name": "Лишняя"}, format="json").status_code == 400
    )
