from io import BytesIO
from uuid import uuid4

import pytest
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from PIL import Image

from config import composition
from tapme.accounts.models import User
from tapme.businesses.application.contracts import Scope
from tapme.businesses.models import Membership
from tapme.media.models import PhotoRecord
from tapme.orders.models import OrderEvent, OrderRecord


@pytest.fixture
def photo_order(setup, base, payload, settings, tmp_path):
    settings.STORAGES = {
        **settings.STORAGES,
        "photos": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path)},
        },
    }
    client = setup["client"]
    response = client.post(
        base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    )
    assert response.status_code == 201
    order = response.json()
    courier = User.objects.create_user(username="photo_courier")
    Membership.objects.create(business=setup["business"], user=courier, role="courier")
    OrderRecord.objects.filter(id=order["id"]).update(florist=setup["florist"], courier=courier)
    setup["courier"] = courier
    url = base + f"/orders/{order['id']}/photos/"
    picture = BytesIO()
    Image.new("RGB", (12, 12), "purple").save(picture, "PNG")
    photos = {}
    for kind in ("bouquet", "delivery"):
        response = client.post(
            url,
            {"kind": kind, "file": SimpleUploadedFile("photo.png", picture.getvalue())},
            format="multipart",
        )
        assert response.status_code == 201
        photos[kind] = PhotoRecord.objects.get(id=response.json()["id"])
    return order, url, photos


@pytest.mark.parametrize(
    "role,kind,allowed",
    [
        ("owner", "bouquet", True),
        ("owner", "delivery", True),
        ("manager", "bouquet", True),
        ("manager", "delivery", True),
        ("florist", "bouquet", True),
        ("florist", "delivery", False),
        ("courier", "bouquet", False),
        ("courier", "delivery", True),
    ],
)
def test_delete_photo_by_role(
    setup, photo_order, django_capture_on_commit_callbacks, role, kind, allowed
):
    order, url, photos = photo_order
    client = setup["client"]
    client.force_login(setup[role])
    photo = photos[kind]
    file_url = url + str(photo.id) + "/"
    info = next(p for p in client.get(url).json() if p["id"] == str(photo.id))
    assert info["can_delete"] is allowed
    with django_capture_on_commit_callbacks(execute=True):
        response = client.delete(file_url)
    assert response.status_code == (204 if allowed else 403)
    assert PhotoRecord.objects.filter(id=photo.id).exists() is (not allowed)
    assert storages["photos"].exists(photo.key) is (not allowed)
    assert client.get(file_url).status_code == (404 if allowed else 200)
    remaining = photos["delivery" if kind == "bouquet" else "bouquet"]
    assert client.get(url + str(remaining.id) + "/").status_code == 200
    assert OrderRecord.objects.get(id=order["id"]).version == order["version"]
    events = OrderEvent.objects.filter(order_id=order["id"], kind="photo_deleted")
    assert events.count() == int(allowed)
    if allowed:
        assert events.get().actor_id == setup[role].id
        assert client.delete(file_url).status_code == 404
        assert events.count() == 1


def test_photo_delete_scope_and_reassignment(setup, base, payload, photo_order):
    order, url, photos = photo_order
    client = setup["client"]
    photo = photos["bouquet"]
    file_url = url + str(photo.id) + "/"
    other_order = client.post(
        base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    ).json()
    assert (
        client.delete(base + f"/orders/{other_order['id']}/photos/{photo.id}/").status_code == 404
    )
    client.force_login(setup["other_owner"])
    assert client.delete(file_url).status_code == 403
    foreign_url = file_url.replace(str(setup["business"].id), str(setup["other_business"].id))
    assert client.delete(foreign_url).status_code == 404
    client.force_login(setup["florist"])
    assert client.get(url).json()[0]["can_delete"] is True
    OrderRecord.objects.filter(id=order["id"]).update(florist=None)
    assert client.get(url).json()[0]["can_delete"] is False
    assert client.delete(file_url).status_code == 403
    Membership.objects.filter(user=setup["florist"]).update(is_active=False)
    assert client.delete(file_url).status_code == 403
    client.logout()
    assert client.delete(file_url).status_code in (401, 403)
    assert PhotoRecord.objects.filter(id=photo.id).exists()
    assert storages["photos"].exists(photo.key)


def test_cancelled_order_photos_are_retained(setup, photo_order):
    order, url, photos = photo_order
    OrderRecord.objects.filter(id=order["id"]).update(status="cancelled")
    client = setup["client"]
    assert all(not p["can_delete"] for p in client.get(url).json())
    assert client.delete(url + str(photos["bouquet"].id) + "/").status_code == 400
    assert PhotoRecord.objects.filter(order_id=order["id"]).count() == 2


def test_photo_file_survives_outer_rollback(setup, photo_order, django_capture_on_commit_callbacks):
    _, _, photos = photo_order
    photo = photos["bouquet"]
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with pytest.raises(RuntimeError), transaction.atomic():
            composition.photos().delete(
                Scope(setup["owner"].id, setup["business"].id), photo.order_id, photo.id
            )
            assert not PhotoRecord.objects.filter(id=photo.id).exists()
            assert storages["photos"].exists(photo.key)
            raise RuntimeError("Rollback the enclosing transaction")
    assert callbacks == []
    assert PhotoRecord.objects.filter(id=photo.id).exists()
    assert storages["photos"].exists(photo.key)
    assert not OrderEvent.objects.filter(order_id=photo.order_id, kind="photo_deleted").exists()


def test_storage_cleanup_failure_leaves_photo_inaccessible(
    setup, photo_order, django_capture_on_commit_callbacks, monkeypatch
):
    _, url, photos = photo_order
    photo = photos["bouquet"]

    def fail_delete(key):
        raise OSError("Storage unavailable")

    monkeypatch.setattr(storages["photos"], "delete", fail_delete)
    with django_capture_on_commit_callbacks(execute=True):
        response = setup["client"].delete(url + str(photo.id) + "/")
    assert response.status_code == 204
    assert not PhotoRecord.objects.filter(id=photo.id).exists()
    assert setup["client"].get(url + str(photo.id) + "/").status_code == 404
    assert storages["photos"].exists(photo.key)  # Orphan cleanup can retry this file.
