from datetime import timedelta
from io import BytesIO, StringIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone
from PIL import Image

from tapme.businesses.models import Membership
from tapme.catalog.infrastructure.repository import DjangoProductRepository
from tapme.catalog.models import ProductRecord
from tapme.media.management.commands import export_photos, import_photos
from tapme.shared.domain import Conflict


@pytest.fixture(autouse=True)
def photo_storage(settings, tmp_path):
    settings.STORAGES = {
        **settings.STORAGES,
        "photos": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path)},
        },
    }


def picture(color="pink"):
    out = BytesIO()
    Image.new("RGB", (40, 30), color).save(out, "PNG")
    return SimpleUploadedFile("bouquet.png", out.getvalue(), "image/png")


def test_product_photo_create_replace_preserve_remove_and_archive(setup, base):
    c = setup["client"]
    response = c.post(
        base + "/products/",
        {"name": "Нежность", "price": "2500", "photo": picture()},
        format="multipart",
    )
    assert response.status_code == 201, response.data
    p = response.json()
    url = base + f"/products/{p['id']}/"
    first = c.get(p["photo_url"])
    assert first.status_code == 200
    assert first["Content-Type"] == "image/jpeg" and first["Cache-Control"] == "private, no-store"
    assert Image.open(BytesIO(first.content)).size == (40, 30)
    row = ProductRecord.objects.get(id=p["id"])
    old_key = row.photo_key
    # Existing JSON price/archive clients preserve the photo when the field is absent.
    response = c.put(
        url,
        {"name": "Нежность новая", "price": "2700", "version": 1, "active": False},
        format="json",
    )
    assert response.status_code == 200, response.data
    row.refresh_from_db()
    assert row.photo_key == old_key
    assert c.get(base + "/products/", {"include_hidden": True}).json()["count"] == 2
    response = c.put(
        url,
        {"name": row.name, "price": "2700", "version": 2, "active": True, "photo": picture("blue")},
        format="multipart",
    )
    assert response.status_code == 200, response.data
    assert c.get(response.json()["photo_url"]).content != first.content
    row.refresh_from_db()
    assert row.photo_key != old_key
    response = c.put(
        url, {"name": row.name, "price": "2700", "version": 3, "remove_photo": True}, format="json"
    )
    assert response.status_code == 200 and response.json()["photo_url"] == ""
    assert c.get(p["photo_url"]).status_code == 404


def test_invalid_upload_and_conflict_never_change_product_or_leave_new_file(
    setup, base, tmp_path, monkeypatch
):
    c = setup["client"]
    product = setup["product"]
    url = base + f"/products/{product.id}/"
    values = {"name": "Новое имя", "price": "20", "version": 1}
    invalid = c.put(
        url, {**values, "photo": SimpleUploadedFile("bad.jpg", b"bad")}, format="multipart"
    )
    assert invalid.status_code == 400
    for extra in ({"remove_photo": True}, {"version": 2}):
        result = c.put(url, {**values, **extra, "photo": picture()}, format="multipart")
        assert result.status_code == (409 if "version" in extra else 400)
    large = SimpleUploadedFile("large.jpg", b"x" * (10 * 1024 * 1024 + 1))
    assert c.put(url, {**values, "photo": large}, format="multipart").status_code == 400

    def raced(*args):
        raise Conflict("Позиция уже изменена.")

    monkeypatch.setattr(DjangoProductRepository, "save", raced)
    assert c.put(url, {**values, "photo": picture()}, format="multipart").status_code == 409
    product.refresh_from_db()
    assert product.name == "Букет" and product.photo_key == "" and product.version == 1
    assert list(tmp_path.rglob("*.jpg")) == []
    monkeypatch.setattr(DjangoProductRepository, "add", raced)
    assert (
        c.post(
            base + "/products/",
            {"name": "Не сохранится", "price": "10", "photo": picture()},
            format="multipart",
        ).status_code
        == 409
    )
    assert list(tmp_path.rglob("*.jpg")) == []


def test_florist_sees_reference_photo_but_cannot_edit_price_or_read_another_shop(
    setup, base, payload
):
    c = setup["client"]
    p = setup["product"]
    url = base + f"/products/{p.id}/"
    result = c.put(
        url,
        {"name": p.name, "price": str(p.price), "version": 1, "photo": picture()},
        format="multipart",
    )
    assert result.status_code == 200, result.data
    image_url = result.json()["photo_url"]
    order = c.post(base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    assert order.status_code == 201, order.data
    assert order.json()["lines"][0]["photo_url"] == image_url
    c.force_login(setup["florist"])
    task = c.get(base + "/tasks/").json()["results"][0]
    assert task["items"] == [{"name": p.name, "quantity": 2, "photo_url": image_url}]
    assert c.get(image_url).status_code == 200
    assert c.get(base + "/products/").status_code == 403
    assert c.put(url, {"name": "Нет", "price": "0", "version": 2}, format="json").status_code == 403
    c.force_login(setup["other_owner"])
    assert c.get(image_url).status_code == 403
    foreign_path = image_url.replace(str(setup["business"].id), str(setup["other_business"].id))
    assert c.get(foreign_path).status_code == 404
    c.force_login(setup["florist"])
    Membership.objects.filter(business=setup["business"], user=setup["florist"]).update(
        is_active=False
    )
    assert c.get(image_url).status_code == 403
    c.logout()
    assert c.get(image_url).status_code == 403


def test_catalog_photo_backup_restore_and_cleanup_protects_archived_reference(
    setup, base, monkeypatch, tmp_path
):
    c = setup["client"]
    p = setup["product"]
    response = c.put(
        base + f"/products/{p.id}/",
        {"name": p.name, "price": str(p.price), "version": 1, "active": False, "photo": picture()},
        format="multipart",
    )
    assert response.status_code == 200, response.data
    p.refresh_from_db()
    storage = storages["photos"]
    original = storage.open(p.photo_key, "rb").read()
    archive = BytesIO()
    monkeypatch.setattr(
        export_photos, "sys", SimpleNamespace(stdout=SimpleNamespace(buffer=archive))
    )
    call_command("export_photos", stdout=StringIO())
    storage.delete(p.photo_key)
    monkeypatch.setattr(
        import_photos,
        "sys",
        SimpleNamespace(stdin=SimpleNamespace(buffer=BytesIO(archive.getvalue()))),
    )
    call_command("import_photos", apply=True, stdout=StringIO())
    assert storage.open(p.photo_key, "rb").read() == original
    # Simulate both the referenced photo and a superseded upload being old enough to collect.
    orphan = tmp_path / "orphan.jpg"
    orphan.write_bytes(b"old file")
    monkeypatch.setattr(
        storage, "get_modified_time", lambda key: timezone.now() - timedelta(days=2)
    )
    call_command("cleanup_orphan_photos", apply=True, stdout=StringIO())
    assert storage.exists(p.photo_key) and not orphan.exists()
