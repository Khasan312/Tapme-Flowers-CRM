from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
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


def test_desk_urgent_counts_and_window_load_apply_before_pagination(setup, base, payload):
    client = setup["client"]
    day = "2000-01-01"
    other_day = "2099-12-31"
    shop = Shop.objects.get(business=setup["business"])
    shop.pickup_unlimited = True
    shop.save(update_fields=["pickup_unlimited"])
    for date, status, method in (
        (day, "new", "courier"),
        (day, "ready", "courier"),
        (day, "cancelled", "courier"),
        (day, "new", "pickup"),
        (other_day, "new", "courier"),
    ):
        order = create(setup, base, {**payload, "delivery_date": date, "fulfillment": method})
        assert order.status_code == 201, order.data
        OrderRecord.objects.filter(id=order.data["id"]).update(status=status)

    url = base + "/orders/desk/"
    late = client.get(url, {"scope": "all", "status": "late", "limit": 1})
    assert late.status_code == 200, late.data
    assert late.data["count"] == 3
    assert len(late.data["results"]) == 1
    assert late.data["urgent_counts"] == {"build": 3, "late": 3}
    build = client.get(url, {"scope": "all", "status": "build"}).data
    assert {row["status"] for row in build["results"]} == {"new"}
    assert build["urgent_counts"] == late.data["urgent_counts"]

    delivery = client.get(url, {"scope": "date", "day": day, "status": "courier", "limit": 1})
    assert delivery.status_code == 200, delivery.data
    assert len(delivery.data["results"]) == 1
    assert delivery.data["window_load"] == [
        {
            "point_id": str(shop.id),
            "window_start": "10:00",
            "window_end": "12:00",
            "occupied": 2,
        }
    ]


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


def test_cancelled_scope_covers_all_dates_search_pagination_and_store_boundary(
    setup, base, payload
):
    c = setup["client"]
    assert create(setup, base, payload).status_code == 201
    cancelled = []
    for day in ("2000-01-01", "2099-12-31"):
        response = create(setup, base, {**payload, "delivery_date": day})
        assert response.status_code == 201, response.data
        order = response.json()
        result = c.post(
            base + f"/orders/{order['id']}/transition/",
            {"version": 1, "status": "cancelled", "reason": "По просьбе клиента"},
            format="json",
        )
        assert result.status_code == 200, result.data
        cancelled.append(order)
    c.force_login(setup["other_owner"])
    other_base = f"/api/v1/businesses/{setup['other_business'].id}"
    foreign = create(
        setup,
        other_base,
        {
            **payload,
            "customer_id": str(setup["other_customer"].id),
            "items": [{"product_id": str(setup["other_product"].id), "quantity": 1}],
        },
    ).json()
    assert (
        c.post(
            other_base + f"/orders/{foreign['id']}/transition/",
            {"version": 1, "status": "cancelled", "reason": "Другая отмена"},
            format="json",
        ).status_code
        == 200
    )
    url = base + "/orders/desk/"
    assert c.get(url, {"scope": "cancelled"}).status_code == 403
    c.force_login(setup["owner"])
    response = c.get(url, {"scope": "cancelled"})
    assert response.status_code == 200, response.data
    result = response.json()
    assert result["count"] == result["scopes"]["cancelled"] == 2
    assert result["scopes"]["all"] == 3
    assert result["scopes"]["unpaid"] == 1
    assert {o["id"] for o in result["results"]} == {o["id"] for o in cancelled}
    assert all(o["cancellation_reason"] == "По просьбе клиента" for o in result["results"])
    assert result["summary"]["late"] == 0
    assert result["summary"]["total"] == "0.00"
    assert (
        c.get(url, {"scope": "cancelled", "search": f"#{cancelled[1]['number']}"}).json()["count"]
        == 1
    )
    page = c.get(url, {"scope": "cancelled", "limit": 1, "offset": 1}).json()
    assert page["count"] == 2 and page["results"][0]["id"] == cancelled[1]["id"]
    c.force_login(setup["florist"])
    assert c.get(url, {"scope": "cancelled"}).status_code == 403


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


def test_directory_combined_category_requires_both_tags_and_keeps_other_filters(setup, base):
    c = setup["client"]
    both = setup["customer"]
    both.tags = ["VIP", "Корпоративный", "Постоянный"]
    both.save()
    for name, phone, tags in [
        ("Только VIP", "+996555000001", ["VIP"]),
        ("Только корпоративный", "+996555000002", ["Корпоративный"]),
        ("Обычный", "+996555000003", []),
    ]:
        CustomerRecord.objects.create(business=setup["business"], name=name, phone=phone, tags=tags)
    foreign = setup["other_customer"]
    foreign.tags = both.tags
    foreign.save()
    url = base + "/customers/directory/"
    result = c.get(url, {"group": "vip_corp"})
    assert result.status_code == 200, result.data
    assert [row["id"] for row in result.json()["results"]] == [str(both.id)]
    assert result.json()["total_count"] == 4
    for group in ("vip", "corp"):
        rows = c.get(url, {"group": group}).json()["results"]
        assert len(rows) == 2 and str(both.id) in {row["id"] for row in rows}
    assert c.get(url, {"group": "vip_corp", "search": "Только"}).json()["count"] == 0
    assert c.get(url, {"group": "vip_corp", "offset": 1}).json()["results"] == []
    c.force_login(setup["other_owner"])
    assert c.get(url, {"group": "vip_corp"}).status_code == 403


@pytest.mark.parametrize(
    ("orders", "expected"),
    [
        ([], 0),
        ([(89, "done")], 0),
        ([(90, "done")], 1),
        ([(91, "done")], 1),
        ([(100, "cancelled")], 0),
        ([(90, "done"), (1, "cancelled")], 1),
        ([(100, "done"), (89, "done")], 0),
        ([(100, "done"), (-1, "new")], 0),
    ],
)
def test_lapsed_directory_boundary_uses_local_date_and_latest_non_cancelled_order(
    setup, base, payload, monkeypatch, orders, expected
):
    # UTC is still the previous day: exactly 90 local days must be included.
    now = datetime(2026, 11, 20, 20, tzinfo=UTC)
    today = (now + timedelta(hours=6)).date()
    business = setup["business"]
    business.timezone = "Asia/Bishkek"
    business.save()
    monkeypatch.setattr("tapme.customers.directory_api.timezone.now", lambda: now)
    setup["client"].force_login(setup["owner"])
    for days, status in orders:
        result = create(
            setup, base, {**payload, "delivery_date": str(today - timedelta(days=days))}
        )
        assert result.status_code == 201, result.data
        OrderRecord.objects.filter(id=result.json()["id"]).update(status=status)
    response = setup["client"].get(base + "/customers/directory/", {"group": "lapsed"})
    assert response.status_code == 200, response.data
    assert response.json()["count"] == expected


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
