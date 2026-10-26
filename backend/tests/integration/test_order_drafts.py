from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import close_old_connections
from django.utils import timezone

from config import composition
from tapme.accounts.models import User
from tapme.businesses.application.contracts import Scope
from tapme.businesses.models import Membership, Shop
from tapme.catalog.models import ProductRecord
from tapme.messaging.models import ChannelAccount, Conversation, Message
from tapme.orders.models import OfficeTask, OrderDraft, OrderEvent, OrderLineRecord, OrderRecord
from tapme.orders.tasks import maintain_order_drafts


@pytest.fixture
def draft_setup(setup, base):
    channel = ChannelAccount.objects.create(
        business=setup["business"],
        phone_number_id="draft-test",
        display_phone="+996555000111",
        display_name="Test",
        token_encrypted="",
        provider_mode="fake",
    )
    chat = Conversation.objects.create(
        channel=channel, customer=setup["customer"], phone=setup["customer"].phone
    )
    url = f"{base}/chats/{chat.id}/order-draft/"
    return setup["client"], url, chat


def save_complete(setup, draft_setup, fulfillment="courier"):
    client, url, chat = draft_setup
    response = client.post(url, {}, format="json")
    assert response.status_code == 200, response.data
    draft = response.data["draft"]
    fields = {
        **draft["fields"],
        "items": [{"kind": "product", "product_id": str(setup["product"].id), "quantity": 2}],
        "date": (timezone.now() + timedelta(days=5)).date().isoformat(),
        "window": {"start": "10:00", "end": "12:00"},
        "fulfillment": fulfillment,
        "address": "Бишкек, Токтогула 125",
        "recipient_phone": "+996700123456",
        "card_text": "Маме!",
    }
    response = client.put(
        url, {"draft_id": draft["id"], "version": draft["version"], "fields": fields}, format="json"
    )
    assert response.status_code == 200, response.data
    return response.data["draft"]


def convert(draft_setup, draft, **options):
    client, url, chat = draft_setup
    response = client.post(
        url + "convert/",
        {"draft_id": draft["id"], "version": draft["version"], **options},
        format="json",
    )
    assert response.status_code == 200, response.data
    return response.data


def test_incomplete_draft_preserved_and_conflict(setup, draft_setup):
    client, url, chat = draft_setup
    assert client.get(url).data["draft"] is None
    draft = client.post(url, {}, format="json").data["draft"]
    assert client.post(url, {}, format="json").data["draft"]["id"] == draft["id"]
    data = {
        "draft_id": draft["id"],
        "version": 1,
        "fields": {"notes": "Без лилий", "recipient_phone": "+996555"},
    }
    assert client.put(url, data, format="json").status_code == 200
    assert (
        client.put(url, {**data, "fields": {"notes": "Старая вкладка"}}, format="json").status_code
        == 409
    )
    saved = client.get(url).data["draft"]
    assert saved["fields"]["notes"] == "Без лилий"
    assert saved["field_meta"]["notes"]["locked"]
    assert "Корректный телефон получателя" in saved["missing"]
    assert (
        client.post(
            url + "convert/", {"draft_id": draft["id"], "version": 2}, format="json"
        ).status_code
        == 400
    )
    assert OrderRecord.objects.count() == 0


@pytest.mark.parametrize("role", ["florist", "other_owner"])
def test_draft_role_and_business_isolation(setup, draft_setup, base, role):
    client, url, chat = draft_setup
    draft = save_complete(setup, draft_setup)
    client.force_login(setup[role])
    for method, suffix, data in [
        ("get", "", {}),
        ("post", "", {}),
        ("put", "", {"draft_id": draft["id"], "version": 2, "fields": draft["fields"]}),
        ("post", "convert/", {"draft_id": draft["id"], "version": 2}),
    ]:
        assert getattr(client, method)(url + suffix, data, format="json").status_code == 403
    if role == "other_owner":
        other_url = url.replace(str(setup["business"].id), str(setup["other_business"].id))
        assert client.get(other_url).status_code == 404


def test_draft_rejects_foreign_products_and_client_supplied_price(setup, draft_setup):
    client, url, chat = draft_setup
    draft = save_complete(setup, draft_setup)
    for item in [
        {"kind": "product", "product_id": str(setup["other_product"].id), "quantity": 1},
        {"kind": "product", "product_id": str(setup["product"].id), "quantity": 1, "price": "1"},
    ]:
        assert (
            client.put(
                url,
                {
                    "draft_id": draft["id"],
                    "version": 2,
                    "fields": {**draft["fields"], "items": [item]},
                },
                format="json",
            ).status_code
            == 400
        )


def test_courier_conversion_pending_and_idempotent(setup, draft_setup, base):
    client, url, chat = draft_setup
    draft = save_complete(setup, draft_setup)
    order = convert(draft_setup, draft)
    assert order["status"] == "pending"
    assert order["prepayment_required"] == order["total"]
    assert order["payment_due_at"] and order["source"] == "whatsapp"
    assert order["card"] == "Маме!"
    assert convert(draft_setup, {**draft, "version": 999})["id"] == order["id"]
    assert OrderRecord.objects.count() == 1
    assert Message.objects.filter(conversation=chat, direction="system").count() == 1
    desk = client.get(base + "/orders/desk/?scope=pending").data
    assert desk["count"] == 1 and desk["scopes"]["pending"] == 1
    assert desk["summary"]["build"] == desk["summary"]["late"] == 0
    assert Decimal(desk["summary"]["total"]) == 0
    overview = client.get(base + "/overview/").data
    assert overview["pending"] == 1 and overview["in_progress"] == 0 and overview["deliveries"] == 0
    assert (
        client.post(
            f"{base}/orders/{order['id']}/assignment/",
            {"version": 1, "florist_id": str(setup["florist"].id), "courier_id": None},
            format="json",
        ).status_code
        == 400
    )
    client.force_login(setup["florist"])
    assert client.get(base + "/tasks/").data["count"] == 0
    for suffix in ["photos/", "history/", ""]:
        assert client.get(f"{base}/orders/{order['id']}/" + suffix).status_code == 403
    assert (
        client.post(
            f"{base}/orders/{order['id']}/transition/",
            {"version": 1, "status": "work"},
            format="json",
        ).status_code
        == 403
    )


def test_pending_hidden_even_if_staff_was_assigned(setup, draft_setup, base):
    order = convert(draft_setup, save_complete(setup, draft_setup))
    courier = User.objects.create_user(username="draft-courier")
    Membership.objects.create(business=setup["business"], user=courier, role="courier")
    OrderRecord.objects.filter(id=order["id"]).update(florist=setup["florist"], courier=courier)
    for staff in [setup["florist"], courier]:
        setup["client"].force_login(staff)
        assert setup["client"].get(base + "/tasks/").data["count"] == 0
        assert setup["client"].get(f"{base}/orders/{order['id']}/photos/").status_code == 403


def test_confirm_requires_payment_or_reason_and_releases_to_florist(setup, draft_setup, base):
    client, url, chat = draft_setup
    order = convert(draft_setup, save_complete(setup, draft_setup))
    endpoint = f"{base}/orders/{order['id']}/transition/"
    client.force_login(setup["manager"])
    assert client.post(endpoint, {"version": 1, "status": "new"}, format="json").status_code == 400
    result = client.post(
        endpoint,
        {"version": 1, "status": "new", "reason": "Согласовано с постоянным клиентом"},
        format="json",
    )
    assert result.status_code == 200 and result.data["status"] == "new"
    assert OrderEvent.objects.filter(
        order_id=order["id"], kind="confirmed", detail__contains="Согласовано"
    ).exists()
    client.force_login(setup["florist"])
    assert client.get(base + "/tasks/").data["count"] == 1
    assert client.post(endpoint, {"version": 2, "status": "work"}, format="json").status_code == 200


def test_payment_then_manual_confirmation(setup, draft_setup, base):
    client, url, chat = draft_setup
    order = convert(draft_setup, save_complete(setup, draft_setup))
    result = client.post(
        f"{base}/orders/{order['id']}/payments/",
        {"amount": order["total"], "kind": "payment", "method": "transfer"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert result.status_code == 201
    result = client.post(
        f"{base}/orders/{order['id']}/transition/", {"version": 2, "status": "new"}, format="json"
    )
    assert result.status_code == 200 and result.data["status"] == "new"


def test_pickup_and_ordinary_orders_remain_new(setup, draft_setup, payload, base):
    order = convert(draft_setup, save_complete(setup, draft_setup, "pickup"))
    assert order["status"] == "new" and order["payment_due_at"] is None
    result = setup["client"].post(
        base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    )
    assert result.status_code == 201 and result.data["status"] == "new"


def test_free_urgent_delivery_does_not_require_payment_deadline(setup, draft_setup, monkeypatch):
    # At 09:00 in Bishkek an order for the 10:00 window is urgent, but owes nothing.
    now = datetime.fromisoformat("2027-01-04T03:00:00+00:00")
    monkeypatch.setattr(timezone, "now", lambda: now)
    ProductRecord.objects.filter(id=setup["product"].id).update(price=0)
    client, url, _ = draft_setup
    client.force_login(setup["owner"])
    draft = save_complete(setup, draft_setup)
    draft = client.put(
        url,
        {
            "draft_id": draft["id"],
            "version": draft["version"],
            "fields": {**draft["fields"], "date": "2027-01-04"},
        },
        format="json",
    ).data["draft"]
    order = convert(draft_setup, draft)
    assert order["status"] == "new"
    assert order["prepayment_required"] == "0.00" and order["payment_due_at"] is None


def test_budget_order_hidden_system_product_and_snapshot(setup, draft_setup, base):
    client, url, chat = draft_setup
    draft = save_complete(setup, draft_setup, "pickup")
    fields = {
        **draft["fields"],
        "items": [{"kind": "budget", "amount": "5000", "description": "Без лилий"}],
    }
    draft = client.put(
        url, {"draft_id": draft["id"], "version": 2, "fields": fields}, format="json"
    ).data["draft"]
    order = convert(draft_setup, draft)
    assert order["total"] == "5000.00" and "Без лилий" in order["lines"][0]["name"]
    system = ProductRecord.objects.get(system_kind="budget")
    assert not system.active
    assert str(system.id) not in str(client.get(base + "/products/?include_hidden=true").data)
    assert (
        client.put(
            f"{base}/products/{system.id}/",
            {"name": "Хак", "price": "1", "version": 1, "active": False},
            format="json",
        ).status_code
        == 400
    )


def test_pending_reserves_capacity_and_cancellation_releases_it(setup, draft_setup, base):
    client, url, chat = draft_setup
    Shop.objects.filter(business=setup["business"]).update(
        enforce_capacity=True,
        delivery_windows=[{"start": "10:00", "end": "12:00", "capacity": 1, "price": "100"}],
    )
    first = convert(draft_setup, save_complete(setup, draft_setup))
    second = save_complete(setup, draft_setup)
    data = {"draft_id": second["id"], "version": second["version"]}
    assert client.post(url + "convert/", data, format="json").status_code == 400
    assert OrderDraft.objects.get(id=second["id"]).status == "active"
    assert (
        client.post(
            f"{base}/orders/{first['id']}/transition/",
            {"version": 1, "status": "cancelled", "reason": "Отказ клиента"},
            format="json",
        ).status_code
        == 200
    )
    assert convert(draft_setup, second)["status"] == "pending"


@pytest.mark.parametrize("hold", ["none", "payment", "image", "document"])
def test_expiry_safely_preserves_payment_and_possible_receipt(setup, draft_setup, base, hold):
    client, url, chat = draft_setup
    order = convert(draft_setup, save_complete(setup, draft_setup))
    if hold == "payment":
        assert (
            client.post(
                f"{base}/orders/{order['id']}/payments/",
                {"amount": "1", "kind": "payment", "method": "cash"},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid4()),
            ).status_code
            == 201
        )
    elif hold != "none":
        Message.objects.create(conversation=chat, direction="in", kind=hold, status="received")
    OrderRecord.objects.filter(id=order["id"]).update(
        payment_due_at=timezone.now() - timedelta(minutes=1)
    )
    maintain_order_drafts()
    maintain_order_drafts()
    assert OrderRecord.objects.get(id=order["id"]).status == (
        "cancelled" if hold == "none" else "pending"
    )
    assert OfficeTask.objects.count() == (0 if hold == "none" else 1)


def test_abandoned_draft_can_restore_without_duplication(setup, draft_setup):
    client, url, chat = draft_setup
    draft = save_complete(setup, draft_setup)
    OrderDraft.objects.filter(id=draft["id"]).update(
        updated_at=timezone.now() - timedelta(hours=73)
    )
    maintain_order_drafts()
    assert client.get(url).data["draft"]["status"] == "abandoned"
    response = client.post(url + "restore/", {"draft_id": draft["id"], "version": 3}, format="json")
    assert response.status_code == 200 and response.data["draft"]["status"] == "active"
    assert response.data["draft"]["fields"]["card_text"] == "Маме!"


def test_extend_and_stale_confirmation(setup, draft_setup, base):
    client, url, chat = draft_setup
    order = convert(draft_setup, save_complete(setup, draft_setup))
    endpoint = f"{base}/orders/{order['id']}/"
    result = client.post(endpoint + "extend-payment/", {"version": 1}, format="json")
    assert result.status_code == 200 and result.data["version"] == 2
    assert (
        client.post(
            endpoint + "transition/",
            {"version": 1, "status": "new", "reason": "Отсрочка"},
            format="json",
        ).status_code
        == 409
    )


def test_expiry_processes_orders_beyond_first_batch(setup, draft_setup):
    order = convert(draft_setup, save_complete(setup, draft_setup))
    row = OrderRecord.objects.get(id=order["id"])
    values = {
        field.attname: getattr(row, field.attname)
        for field in OrderRecord._meta.concrete_fields
        if field.name not in {"id", "number", "request_key"}
    }
    copies = OrderRecord.objects.bulk_create(
        [OrderRecord(id=uuid4(), number=n, request_key=uuid4(), **values) for n in range(2, 202)]
    )
    line = row.lines.get()
    OrderLineRecord.objects.bulk_create(
        [
            OrderLineRecord(
                order=copy,
                product=line.product,
                name=line.name,
                unit_price=line.unit_price,
                quantity=line.quantity,
                position=0,
            )
            for copy in copies
        ]
    )
    OrderRecord.objects.update(payment_due_at=timezone.now() - timedelta(minutes=1))
    maintain_order_drafts()
    assert OrderRecord.objects.filter(status="cancelled").count() == 201


@pytest.mark.django_db(transaction=True)
def test_concurrent_conversion_only_one_order(setup, draft_setup):
    draft = save_complete(setup, draft_setup)
    chat = draft_setup[2]
    scope = Scope(setup["owner"].id, setup["business"].id)

    def submit():
        close_old_connections()
        try:
            return composition.drafts().convert(scope, chat.id, draft["id"], draft["version"]).id
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(lambda _: submit(), range(2)))
    assert result[0] == result[1] and OrderRecord.objects.count() == 1


def test_draft_keeps_explicit_point_and_its_delivery_price(setup, draft_setup, base):
    client, url, _ = draft_setup
    second = client.post(
        base + "/points/",
        {
            "name": "Чуй",
            "short_name": "Чуй",
            "windows": [{"start": "10:00", "end": "12:00", "capacity": 3, "price": "750.00"}],
        },
        format="json",
    ).data
    draft = save_complete(setup, draft_setup)
    assert "Выберите доступную точку заказа" in draft["missing"]
    updated = client.put(
        url,
        {
            "draft_id": draft["id"],
            "version": draft["version"],
            "fields": {**draft["fields"], "point_id": second["id"]},
        },
        format="json",
    )
    assert updated.status_code == 200
    draft = updated.data["draft"]
    assert draft["delivery_fee"] == "750.00"
    # Switching the global view does not move a previously saved draft.
    other = client.get(url, HTTP_X_TAPME_POINT=str(setup["business"].shop.id)).data["draft"]
    assert other["fields"]["point_id"] == second["id"]
    order = convert(draft_setup, draft)
    assert order["point_id"] == second["id"]
    assert order["delivery_fee"] == "750.00"
