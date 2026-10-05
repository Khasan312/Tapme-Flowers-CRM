from io import BytesIO, StringIO
from types import SimpleNamespace
from uuid import uuid4

from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

from tapme.media.management.commands import export_photos, import_photos
from tapme.media.models import PhotoRecord


def test_private_photo_backup_and_restore_with_same_keys(
    setup, base, payload, settings, tmp_path, monkeypatch
):
    settings.STORAGES = {
        **settings.STORAGES,
        "photos": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path)},
        },
    }
    client = setup["client"]
    order = client.post(
        base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    ).json()
    picture = BytesIO()
    Image.new("RGB", (12, 12), "purple").save(picture, "PNG")
    response = client.post(
        base + f"/orders/{order['id']}/photos/",
        {
            "kind": "bouquet",
            "file": SimpleUploadedFile("bouquet.png", picture.getvalue()),
        },
        format="multipart",
    )
    assert response.status_code == 201
    key = PhotoRecord.objects.get().key
    storage = storages["photos"]
    with storage.open(key, "rb") as source:
        original = source.read()
    archive = BytesIO()
    monkeypatch.setattr(
        export_photos, "sys", SimpleNamespace(stdout=SimpleNamespace(buffer=archive))
    )
    call_command("export_photos", stdout=StringIO())
    storage.delete(key)

    def restore(apply=False):
        monkeypatch.setattr(
            import_photos,
            "sys",
            SimpleNamespace(stdin=SimpleNamespace(buffer=BytesIO(archive.getvalue()))),
        )
        call_command("import_photos", apply=apply, stdout=StringIO())

    restore()
    assert not storage.exists(key)
    restore(True)
    restore(True)
    with storage.open(key, "rb") as source:
        assert source.read() == original
    assert len(list(tmp_path.rglob("*.jpg"))) == 1
