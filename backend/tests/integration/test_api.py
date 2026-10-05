from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient

from tapme.businesses.models import Membership
from tapme.catalog.models import ProductRecord
from tapme.customers.models import CustomerRecord
from tapme.orders.models import OrderCounter, OrderEvent, OrderRecord


def create(setup, base, payload, key=None, client=None):
    return (client or setup["client"]).post(
        base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(key or uuid4())
    )


def test_real_login_csrf_logout(setup, base):
    client = APIClient(enforce_csrf_checks=True)
    creds = {"username": "owner", "password": "test-owner-password"}
    assert client.post("/api/v1/auth/login/", creds, format="json").status_code == 403
    csrf = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
    response = client.post("/api/v1/auth/login/", creds, format="json", HTTP_X_CSRFTOKEN=csrf)
    assert response.status_code == 200
    csrf = response.json()["csrf_token"]
    assert client.get("/api/v1/auth/me/").json()["username"] == "owner"
    assert len(client.get("/api/v1/businesses/").json()) == 1
    assert (
        client.post(
            base + "/customers/", {"name": "Новый", "phone": "+996700444555"}, format="json"
        ).status_code
        == 403
    )
    assert (
        client.post(
            base + "/customers/",
            {"name": "Новый", "phone": "+996700444555"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 201
    )
    assert client.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=csrf).status_code == 204
    assert client.get(base + "/orders/").status_code == 403


@pytest.mark.parametrize("resource", ["orders", "customers", "products"])
def test_tenant_scope_and_anonymous(setup, resource):
    other = f"/api/v1/businesses/{setup['other_business'].id}/{resource}/"
    assert setup["client"].get(other).status_code == 403
    assert APIClient().get(other).status_code == 403


@pytest.mark.parametrize("resource", ["orders", "customers", "products"])
def test_florist_cannot_read_office_data(setup, base, resource):
    setup["client"].force_login(setup["florist"])
    assert setup["client"].get(base + f"/{resource}/").status_code == 403


def test_revoked_membership_is_enforced(setup, base):
    Membership.objects.filter(user=setup["owner"]).update(is_active=False)
    assert setup["client"].get(base + "/customers/").status_code == 403


def test_order_totals_snapshots_history_and_second_employee(setup, base, payload):
    response = create(setup, base, payload)
    assert response.status_code == 201, response.json()
    order = response.json()
    assert order["total"] == "2469.00"
    assert order["number"] == 1
    assert order["status"] == "new"
    assert OrderEvent.objects.get().actor_id == setup["owner"].id
    ProductRecord.objects.filter(id=setup["product"].id).update(
        price="5000.00", name="Новое название"
    )
    CustomerRecord.objects.filter(id=setup["customer"].id).update(name="Другое имя")
    setup["client"].force_login(setup["manager"])
    saved = setup["client"].get(base + f"/orders/{order['id']}/").json()
    assert saved["total"] == "2469.00"
    assert saved["lines"][0]["name"] == "Букет"
    assert saved["customer_name"] == "Клиент"
    setup["client"].force_login(setup["other_owner"])
    other = f"/api/v1/businesses/{setup['other_business'].id}/orders/{order['id']}/"
    assert setup["client"].get(other).status_code == 404


@pytest.mark.parametrize("field", ["customer_id", "product_id"])
def test_foreign_relations_rejected_and_counter_rolled_back(setup, base, payload, field):
    if field == "customer_id":
        payload[field] = str(setup["other_customer"].id)
    else:
        payload["items"][0][field] = str(setup["other_product"].id)
    assert create(setup, base, payload).status_code == 404
    assert not OrderRecord.objects.exists()
    assert not OrderCounter.objects.exists()


def test_retries_and_conflicting_idempotency_key(setup, base, payload):
    key = uuid4()
    first = create(setup, base, payload, key)
    second = create(setup, base, payload, key)
    assert second.json() == first.json()
    payload["notes"] = "Другой запрос"
    assert create(setup, base, payload, key).status_code == 409
    assert OrderRecord.objects.count() == 1
    assert OrderEvent.objects.count() == 1


def test_reject_client_prices_and_status(setup, base, payload):
    payload["total"] = "0.01"
    payload["status"] = "done"
    assert create(setup, base, payload).status_code == 400
    assert not OrderRecord.objects.exists()


@pytest.mark.parametrize(
    "changes", [{"window_end": "09:00"}, {"address": ""}, {"items": []}, {"recipient_phone": "abc"}]
)
def test_invalid_order_does_not_persist(setup, base, payload, changes):
    payload.update(changes)
    assert create(setup, base, payload).status_code == 400
    assert not OrderRecord.objects.exists()
    assert not OrderCounter.objects.exists()


def test_customer_normalization_and_duplicates_are_scoped(setup, base):
    data = {"name": "Тест", "phone": "+996 (700) 22-33-44"}
    response = setup["client"].post(base + "/customers/", data, format="json")
    assert response.status_code == 201
    assert response.json()["phone"] == "+996700223344"
    assert response.json()["consent"] is False
    assert setup["client"].post(base + "/customers/", data, format="json").status_code == 409
    setup["client"].force_login(setup["other_owner"])
    other = f"/api/v1/businesses/{setup['other_business'].id}/customers/"
    assert setup["client"].post(other, data, format="json").status_code == 201


def test_customer_search_and_pagination(setup, base):
    response = setup["client"].get(base + "/customers/?search=Клиент&limit=1")
    assert response.json()["count"] == 1
    assert len(response.json()["results"]) == 1
    assert setup["client"].get(base + "/customers/?limit=10000").status_code == 400


def test_atomic_rollback_on_history_failure(setup, base, payload, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("Simulated persistence failure")

    monkeypatch.setattr(OrderEvent.objects, "create", fail)
    with pytest.raises(RuntimeError):
        create(setup, base, payload)
    assert not OrderRecord.objects.exists()
    assert not OrderCounter.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_retry_creates_one_order(setup, base, payload):
    barrier, key = Barrier(2), uuid4()

    def send():
        close_old_connections()
        try:
            client = APIClient()
            client.force_login(setup["owner"])
            barrier.wait(timeout=10)
            result = create(setup, base, payload, key, client)
            return result.status_code, result.json()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(send) for _ in range(2)]
        results = [f.result(timeout=20) for f in futures]
    assert [r[0] for r in results] == [201, 201]
    assert results[0][1]["id"] == results[1][1]["id"]
    assert OrderRecord.objects.count() == OrderEvent.objects.count() == 1
