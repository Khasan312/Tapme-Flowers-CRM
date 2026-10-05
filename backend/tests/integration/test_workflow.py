from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from config import composition
from tapme.accounts.models import User
from tapme.businesses.application.contracts import Scope
from tapme.businesses.models import Membership
from tapme.customers.models import ImportantDateRecord
from tapme.payments.models import PaymentRecord
from tapme.reminders.domain import ReminderRules
from tapme.shared.domain import InvalidInput


def post(client, url, data, expected=200, **kwargs):
    response = client.post(url, data, format="json", **kwargs)
    assert response.status_code == expected, response.data
    return response.json() if expected != 204 else None


def create(setup, base, payload):
    return post(setup["client"], base + "/orders/", payload, 201, HTTP_IDEMPOTENCY_KEY=str(uuid4()))


def test_full_order_roles_and_conflicts(setup, base, payload):
    c = setup["client"]
    courier = User.objects.create_user(username="courier")
    Membership.objects.create(business=setup["business"], user=courier, role="courier")
    order = create(setup, base, payload)
    url = base + f"/orders/{order['id']}"
    post(c, url + "/transition/", {"version": 1, "status": "ready"}, 400)
    post(
        c,
        url + "/assignment/",
        {"version": 1, "florist_id": str(setup["other_owner"].id), "courier_id": None},
        400,
    )
    order = post(
        c,
        url + "/assignment/",
        {"version": 1, "florist_id": str(setup["florist"].id), "courier_id": str(courier.id)},
    )
    c.force_login(setup["florist"])
    task = c.get(base + "/tasks/").json()["results"][0]
    assert not {"customer_phone", "total", "address"} & task.keys()
    post(c, url + "/transition/", {"version": 1, "status": "work"}, 409)
    order = post(c, url + "/transition/", {"version": order["version"], "status": "work"})
    post(
        c,
        url + "/transition/",
        {"version": order["version"], "status": "cancelled", "reason": "Нет"},
        403,
    )
    order = post(c, url + "/transition/", {"version": order["version"], "status": "ready"})
    c.force_login(courier)
    task = c.get(base + "/tasks/").json()["results"][0]
    assert task["address"] == payload["address"] and "customer_phone" not in task
    order = post(c, url + "/transition/", {"version": order["version"], "status": "route"})
    order = post(
        c, url + "/delivery-issue/", {"version": order["version"], "detail": "Не дозвонился"}
    )
    order = post(c, url + "/transition/", {"version": order["version"], "status": "done"})
    assert order["status"] == "done"
    c.force_login(setup["other_owner"])
    assert c.get(base + "/tasks/").status_code == 403


def test_payments_refunds_idempotency_and_edit(setup, base, payload):
    c = setup["client"]
    order = create(setup, base, payload)
    url = base + f"/orders/{order['id']}"
    data = dict(amount="2000.00", kind="payment", method="cash", note="")
    key = str(uuid4())
    payment = post(c, url + "/payments/", data, 201, HTTP_IDEMPOTENCY_KEY=key)
    assert post(c, url + "/payments/", data, 201, HTTP_IDEMPOTENCY_KEY=key)["id"] == payment["id"]
    post(c, url + "/payments/", {**data, "amount": "1.00"}, 409, HTTP_IDEMPOTENCY_KEY=key)
    post(c, url + "/payments/", data, 400, HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    edited = {
        **payload,
        "items": [{"product_id": str(setup["product"].id), "quantity": 1}],
        "version": 2,
    }
    assert c.put(url + "/edit/", edited, format="json").status_code == 400
    post(
        c,
        url + "/payments/",
        dict(amount="1000.00", kind="refund", method="cash", note="Изменение заказа"),
        201,
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    edited["version"] = 3
    response = c.put(url + "/edit/", edited, format="json")
    assert response.status_code == 200, response.data
    assert response.json()["total"] == "1234.50"
    assert PaymentRecord.objects.count() == 2
    post(c, url + "/transition/", {"status": "cancelled", "version": 4, "reason": ""}, 400)
    post(c, url + "/transition/", {"status": "cancelled", "version": 4, "reason": "Отказ клиента"})


def test_photo_validation_and_scope(setup, base, payload, settings, tmp_path):
    settings.STORAGES = {
        **settings.STORAGES,
        "photos": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path)},
        },
    }
    c = setup["client"]
    order = create(setup, base, payload)
    url = base + f"/orders/{order['id']}/photos/"
    assert (
        c.post(
            url,
            {"kind": "bouquet", "file": SimpleUploadedFile("bad.jpg", b"not image")},
            format="multipart",
        ).status_code
        == 400
    )
    content = BytesIO()
    Image.new("RGB", (10, 10), "red").save(content, "PNG")
    response = c.post(
        url,
        {"kind": "bouquet", "file": SimpleUploadedFile("a.png", content.getvalue())},
        format="multipart",
    )
    assert response.status_code == 201, response.data
    file_url = url + str(response.json()["id"]) + "/"
    assert c.get(file_url).status_code == 200
    c.force_login(setup["other_owner"])
    assert c.get(file_url).status_code == 403
    assert len(list(tmp_path.rglob("*.jpg"))) == 1


def test_customer_profile_version_and_foreign_children(setup, base):
    c = setup["client"]
    url = base + f"/customers/{setup['customer'].id}/"
    body = c.get(url).json()
    body.pop("id")
    body["dates"] = [dict(label="День рождения", person="Мама", month=2, day=29)]
    assert c.put(url, body, format="json").status_code == 200
    assert c.put(url, body, format="json").status_code == 409
    foreign = ImportantDateRecord.objects.create(
        customer=setup["other_customer"], label="Дата", person="Друг", month=1, day=1
    )
    body["version"] = 2
    body["dates"] = [dict(id=str(foreign.id), label="Дата", person="Друг", month=1, day=1)]
    assert c.put(url, body, format="json").status_code == 404


def test_reminders_dedup_pause_and_consent(setup, base, payload):
    customer = setup["customer"]
    customer.consent = True
    customer.save()
    ImportantDateRecord.objects.create(
        customer=customer, label="День рождения", person="Мама", month=10, day=6
    )
    scope = Scope(setup["owner"].id, setup["business"].id)
    service = composition.reminders()
    service.save_rules(scope, ReminderRules(start_hour=0, end_hour=24))
    now = datetime(2026, 9, 22, 10, tzinfo=UTC)
    assert service.generate(scope, now) == 1
    assert service.generate(scope, now) == 0
    row = service.list(scope, "wait", 50, 0, now)["results"][0]
    assert "wa.me" in service.prepare(scope, row["id"], now)["url"]
    order = create(setup, base, payload)
    feedback = post(
        setup["client"],
        base + f"/orders/{order['id']}/feedback/",
        {"kind": "complaint", "message": "Цветы повреждены"},
        201,
    )
    assert service.list(scope, "wait", 50, 0, now)["results"][0]["paused"] is True
    with pytest.raises(InvalidInput):
        service.prepare(scope, row["id"], now)
    post(
        setup["client"],
        base + f"/feedback/{feedback['id']}/resolve/",
        {"outcome": "Букет заменён"},
        204,
    )
    service.act(scope, row["id"], "sent", now)
    assert service.list(scope, "sent", 50, 0, now)["count"] == 1
    customer.consent = False
    customer.save()
    with pytest.raises(InvalidInput):
        service.act(scope, row["id"], "answered", now)


def test_settings_staff_owner_only(setup, base):
    c = setup["client"]
    c.force_login(setup["manager"])
    data = c.get(base + "/settings/").json()
    assert c.put(base + "/settings/", data, format="json").status_code == 403
    c.force_login(setup["owner"])
    data["name"] = "Мастерская"
    assert c.put(base + "/settings/", data, format="json").status_code == 200
    staff = post(
        c,
        base + "/staff/",
        dict(
            username="new_courier", name="Курьер", password="new-courier-test-pass", role="courier"
        ),
        201,
    )
    assert staff["role"] == "courier"
    assert (
        c.put(
            base + f"/staff/{setup['owner'].id}/",
            {"role": "manager", "is_active": False},
            format="json",
        ).status_code
        == 400
    )
