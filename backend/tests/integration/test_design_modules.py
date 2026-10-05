from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient

from config import composition
from tapme.businesses.application.contracts import Scope
from tapme.businesses.models import Shop
from tapme.customers.models import CustomerRecord, RecipientRecord
from tapme.orders.models import OrderRecord
from tapme.reminders.domain import ReminderRules, render_template, template_for
from tapme.shared.domain import InvalidInput


def create(setup, base, payload):
    return setup["client"].post(
        base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    )


def test_desk_search_paid_scope_and_role_boundary(setup, base, payload):
    c = setup["client"]
    result = create(setup, base, payload)
    assert result.status_code == 201, result.data
    order = result.json()
    url = base + "/orders/desk/"
    result = c.get(url, {"scope": "all", "search": "Получатель"})
    assert result.status_code == 200, result.data
    assert result.json()["count"] == 1
    assert result.json()["results"][0]["paid_amount"] == "0.00"
    assert c.get(url, {"scope": "all", "search": "#1"}).json()["count"] == 1
    assert c.get(url, {"scope": "date", "day": payload["delivery_date"]}).json()["count"] == 1
    assert c.get(url, {"scope": "all", "status": "pickup"}).json()["count"] == 0
    assert c.get(url, {"scope": "all", "status": "courier"}).json()["count"] == 1
    payment = c.post(
        base + f"/orders/{order['id']}/payments/",
        dict(amount=order["total"], kind="payment", method="cash", note=""),
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert payment.status_code == 201, payment.data
    assert c.get(url, {"scope": "unpaid"}).json()["count"] == 0
    assert c.get(url, {"scope": "all"}).json()["results"][0]["paid_amount"] == order["total"]
    for actor in (setup["other_owner"], setup["florist"]):
        c.force_login(actor)
        assert c.get(url).status_code == 403


def test_manual_tasks_are_scoped_and_complete_once(setup, base):
    c = setup["client"]
    task = c.post(base + "/office-tasks/", {"content": "Позвонить поставщику"}, format="json")
    assert task.status_code == 201, task.data
    url = base + f"/office-tasks/{task.json()['id']}/done/"
    assert len(c.get(base + "/office-tasks/").json()) == 1
    c.force_login(setup["other_owner"])
    assert c.post(url).status_code == 403
    c.force_login(setup["owner"])
    assert c.post(url).status_code == 204
    assert c.post(url).status_code == 204
    assert c.get(base + "/office-tasks/").json() == []


def configure_slot(setup):
    shop = Shop.objects.get(business=setup["business"])
    shop.delivery_windows = [dict(start="10:00", end="12:00", capacity=1, price="300.00")]
    shop.enforce_capacity = True
    shop.save()
    return shop


def test_window_capacity_shipping_snapshot_and_failed_order_rollback(setup, base, payload):
    shop = configure_slot(setup)
    first = create(setup, base, payload)
    assert first.status_code == 201, first.data
    assert first.json()["delivery_fee"] == "300.00"
    assert first.json()["total"] == "2769.00"
    assert create(setup, base, payload).status_code == 400
    assert OrderRecord.objects.filter(business=setup["business"]).count() == 1
    # Editing the same slot excludes the order itself and preserves its quoted fee.
    shop.delivery_windows[0]["price"] = "900.00"
    shop.save()
    changed = setup["client"].put(
        base + f"/orders/{first.json()['id']}/edit/",
        {**payload, "version": 1, "notes": "Уточнение"},
        format="json",
    )
    assert changed.status_code == 200, changed.data
    assert changed.json()["delivery_fee"] == "300.00"
    pickup = create(setup, base, {**payload, "fulfillment": "pickup", "address": ""})
    assert pickup.status_code == 201, pickup.data
    assert pickup.json()["delivery_fee"] == "0.00"
    assert (
        create(setup, base, {**payload, "window_start": "09:00", "window_end": "10:00"}).status_code
        == 400
    )


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_orders_do_not_overbook(setup, base, payload):
    configure_slot(setup)

    def submit(_):
        close_old_connections()
        try:
            client = APIClient()
            client.force_authenticate(setup["owner"])
            return client.post(
                base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
            ).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, range(2))) == [201, 400]
    assert OrderRecord.objects.filter(business=setup["business"]).count() == 1


def test_directory_metadata_recipient_search_and_totals(setup, base, payload):
    c = setup["client"]
    customer = setup["customer"]
    customer.tags = ["VIP"]
    customer.source = "Instagram"
    customer.save()
    RecipientRecord.objects.create(customer=customer, name="Мама", phone="+996700111222")
    assert create(setup, base, payload).status_code == 201
    r = c.get(base + "/customers/directory/", {"search": "Мама", "group": "vip"})
    assert r.status_code == 200, r.data
    row = r.json()["results"][0]
    assert row["order_count"] == 1 and row["total"] == "2469.00"
    assert row["code"] == customer.code
    assert (
        c.get(base + "/customers/directory/", {"search": str(customer.code)}).json()["count"] == 1
    )
    assert c.get(base + "/customers/directory/", {"group": "corp"}).json()["count"] == 0
    other = CustomerRecord.objects.create(
        business=setup["business"], name="Второй", phone="+996555999999"
    )
    assert other.code > customer.code
    c.force_login(setup["other_owner"])
    assert c.get(base + "/customers/directory/").status_code == 403


def test_russian_templates_saved_and_used_by_offset(setup, base):
    c = setup["client"]
    rules = c.get(base + "/reminder-rules/").json()
    rules["templates"] = {
        "d7": "{имя}, {повод} у {получатель}. {магазин}",
        "confirm": "Заказ №{номер}: {ссылка}",
    }
    response = c.put(base + "/reminder-rules/", rules, format="json")
    assert response.status_code == 200, response.data
    stored = composition.reminders().rules(Scope(setup["owner"].id, setup["business"].id))
    assert (
        render_template(
            template_for("date:abc:2026:7", stored),
            dict(name="Алия", event="праздник", person="Мамы", shop="Цветы"),
        )
        == "Алия, праздник у Мамы. Цветы"
    )
    assert template_for("date:abc:2026:14", stored) == stored.template
    with pytest.raises(InvalidInput):
        ReminderRules(templates={"d7": "{имя.__class__}"}).validate()


def test_archive_preserves_order_but_prevents_new_sale(setup, base, payload):
    c = setup["client"]
    order = create(setup, base, payload).json()
    p = setup["product"]
    archived = c.put(
        base + f"/products/{p.id}/",
        dict(name=p.name, price=str(p.price), version=p.version, active=False),
        format="json",
    )
    assert archived.status_code == 200, archived.data
    assert c.get(base + "/products/").json()["count"] == 0
    assert c.get(base + "/products/", {"include_hidden": True}).json()["count"] == 1
    assert create(setup, base, payload).status_code == 400
    result = c.put(
        base + f"/orders/{order['id']}/edit/",
        {**payload, "version": 1, "notes": "Сохранённая позиция"},
        format="json",
    )
    assert result.status_code == 200, result.data
