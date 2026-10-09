from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from io import BytesIO
from threading import Barrier
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from openpyxl import load_workbook
from rest_framework.test import APIClient

from config import composition
from tapme.accounts.models import User
from tapme.businesses.application.contracts import Scope
from tapme.businesses.models import Membership
from tapme.orders.models import OrderEvent, OrderRecord
from tapme.payments.models import PaymentRecord
from tapme.reminders.models import ReminderRecord


def create(setup, base, payload):
    response = setup["client"].post(
        base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    )
    assert response.status_code == 201, response.data
    return response.json()


def test_import_preview_commit_repeat_and_export(setup, base):
    c = setup["client"]
    csv = (
        "name,phone,notes\nНовый,+996700111333,=1+1\nПовтор,+996700111333,\nПлохой,abc,\n".encode()
    )

    def upload(commit):
        return c.post(
            base + "/customers/import/",
            {"file": SimpleUploadedFile("clients.csv", csv), "commit": str(commit).lower()},
            format="multipart",
        )

    preview = upload(False)
    assert preview.status_code == 200, preview.data
    assert [r["status"] for r in preview.json()["results"]] == ["ready", "duplicate", "error"]
    assert upload(True).json()["created"] == 1
    assert upload(True).json()["created"] == 0
    data = c.get(base + "/customers/export/?kind=xlsx")
    assert data.status_code == 200
    book = load_workbook(BytesIO(data.content), read_only=True)
    rows = list(book.active.rows)
    assert any(cell.value == "=1+1" and cell.data_type == "s" for row in rows for cell in row)
    book.close()
    c.force_login(setup["florist"])
    assert c.get(base + "/customers/export/").status_code == 403


def test_public_link_revocation_data_minimization_feedback(setup, base, payload):
    c = setup["client"]
    order = create(setup, base, payload)
    url = base + f"/orders/{order['id']}/share/"
    token = c.post(url, {}, format="json").json()["token"]
    public = APIClient(enforce_csrf_checks=True)
    public_url = f"/api/v1/public/orders/{token}/"
    data = public.get(public_url).json()
    assert set(data) == {
        "number",
        "status",
        "delivery_date",
        "window_start",
        "window_end",
        "fulfillment",
        "shop_name",
        "shop_phone",
        "can_review",
    }
    assert public.post(public_url, {"rating": 5}, format="json").status_code == 403
    csrf = public.get("/api/v1/auth/csrf/").json()["csrf_token"]
    assert (
        public.post(public_url, {"rating": 5}, format="json", HTTP_X_CSRFTOKEN=csrf).status_code
        == 400
    )
    OrderRecord.objects.filter(id=order["id"]).update(status="done", completed_at=datetime.now(UTC))
    assert (
        public.post(
            public_url, {"rating": 2, "message": "Повреждён"}, format="json", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 201
    )
    assert (
        public.post(public_url, {"rating": 5}, format="json", HTTP_X_CSRFTOKEN=csrf).status_code
        == 409
    )
    assert not public.get(public_url).json()["can_review"]
    # Customer history must preserve the actual public rating, including low scores.
    activity_url = base + f"/customers/{setup['customer'].id}/activity/"
    feedback = c.get(activity_url).json()["feedback"]
    assert len(feedback) == 1
    assert feedback[0]["rating"] == 2
    assert feedback[0]["message"] == "Повреждён"
    manual = c.post(
        base + f"/orders/{order['id']}/feedback/",
        {"kind": "review", "message": "Отзыв из разговора"},
        format="json",
    )
    assert manual.status_code == 201, manual.data
    feedback = c.get(activity_url).json()["feedback"]
    assert len(feedback) == 2
    assert next(f for f in feedback if f["id"] == manual.json()["id"])["rating"] is None
    c.post(url, {"revoke": True}, format="json")
    assert public.get(public_url).status_code == 404


def test_catalog_update_snapshots_search_and_activity(setup, base, payload):
    c = setup["client"]
    order = create(setup, base, payload)
    url = base + f"/products/{setup['product'].id}/"
    data = {"name": "Новое название", "price": "9999.00", "version": 1}
    assert c.put(url, data, format="json").status_code == 200
    assert c.put(url, data, format="json").status_code == 409
    saved = c.get(base + f"/orders/{order['id']}/").json()
    assert saved["total"] == "2469.00"
    assert c.get(base + "/orders/?status=work").json()["count"] == 0
    assert c.get(base + "/orders/?search=Получатель").json()["count"] == 1
    assert c.get(base + f"/orders/?customer_id={setup['other_customer'].id}").json()["count"] == 0
    activity = c.get(base + f"/customers/{setup['customer'].id}/activity/").json()
    assert activity["order_count"] == 1 and activity["orders"][0]["number"] == 1
    assert c.get(base + "/overview/").json()["total"] == "2469.00"


@pytest.mark.django_db(transaction=True)
def test_simultaneous_florist_claim(setup, base, payload):
    order = create(setup, base, payload)
    second = User.objects.create_user(username="second_florist")
    Membership.objects.create(business=setup["business"], user=second, role="florist")
    clients = [APIClient(), APIClient()]
    for client, user in zip(clients, [setup["florist"], second], strict=True):
        client.force_login(user)
    barrier = Barrier(2)

    def claim(client):
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            return client.post(
                base + f"/orders/{order['id']}/transition/",
                {"version": 1, "status": "work"},
                format="json",
            ).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, clients))
    assert results.count(200) == 1
    assert any(code in {403, 409} for code in results)
    assert OrderEvent.objects.filter(order_id=order["id"], kind="work").count() == 1


@pytest.mark.django_db(transaction=True)
def test_simultaneous_payments_cannot_overpay(setup, base, payload):
    order = create(setup, base, payload)
    clients = [APIClient(), APIClient()]
    for c in clients:
        c.force_login(setup["owner"])
    barrier = Barrier(2)

    def pay(c):
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            return c.post(
                base + f"/orders/{order['id']}/payments/",
                {"amount": "2000.00", "kind": "payment", "method": "cash"},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid4()),
            ).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(pay, clients)) == [201, 400]
    assert PaymentRecord.objects.filter(order_id=order["id"]).count() == 1


def test_skip_year_and_custom_inactive_template(setup):
    scope = Scope(setup["owner"].id, setup["business"].id)
    from tapme.customers.models import ImportantDateRecord
    from tapme.reminders.domain import ReminderRules

    customer = setup["customer"]
    customer.consent = True
    customer.save()
    ImportantDateRecord.objects.create(
        customer=customer, label="День рождения", person="Мама", month=10, day=6
    )
    service = composition.reminders()
    service.save_rules(
        scope, ReminderRules(start_hour=0, end_hour=24, inactive_template="Скучаем, {name}!")
    )
    assert service.rules(scope).inactive_template == "Скучаем, {name}!"
    now = datetime(2026, 9, 22, 10, tzinfo=UTC)
    assert service.generate(scope, now) == 1
    row = ReminderRecord.objects.get()
    service.act(scope, row.id, "skipped", now)
    assert service.generate(scope, datetime(2026, 9, 29, 10, tzinfo=UTC)) == 0


def test_password_change_and_staff_reset_isolated(setup, base):
    c = setup["client"]
    assert (
        c.post(
            "/api/v1/auth/password/",
            {"current_password": "wrong", "new_password": "fresh-secure-test-pass"},
            format="json",
        ).status_code
        == 400
    )
    assert (
        c.post(
            "/api/v1/auth/password/",
            {"current_password": "test-owner-password", "new_password": "fresh-secure-test-pass"},
            format="json",
        ).status_code
        == 204
    )
    assert c.get("/api/v1/auth/me/").status_code == 200
    assert (
        c.post(
            base + f"/staff/{setup['florist'].id}/reset-password/",
            {"password": "reset-florist-test-pass"},
            format="json",
        ).status_code
        == 204
    )
    Membership.objects.create(
        business=setup["other_business"], user=setup["florist"], role="florist"
    )
    assert (
        c.post(
            base + f"/staff/{setup['florist'].id}/reset-password/",
            {"password": "another-florist-pass"},
            format="json",
        ).status_code
        == 400
    )
    assert (
        c.post(
            base + f"/staff/{setup['other_owner'].id}/reset-password/",
            {"password": "another-owner-pass"},
            format="json",
        ).status_code
        == 404
    )
