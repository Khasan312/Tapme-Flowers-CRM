from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient

from tapme.accounts.models import User
from tapme.businesses.models import Membership
from tapme.orders.models import OrderEvent, OrderRecord
from tapme.payments.models import PaymentRecord

pytestmark = pytest.mark.django_db


def post(client, url, data, expected=200, **headers):
    response = client.post(url, data, format="json", **headers)
    assert response.status_code == expected, response.data
    return response.json()


def create(setup, base, payload):
    return post(setup["client"], base + "/orders/", payload, 201, HTTP_IDEMPOTENCY_KEY=str(uuid4()))


@pytest.mark.parametrize("active", [True, False])
def test_remove_membership_preserves_account_and_other_shop(setup, base, active):
    user = setup["florist"]
    Membership.objects.filter(business=setup["business"], user=user).update(is_active=active)
    Membership.objects.create(user=user, business=setup["other_business"], role="manager")
    session = APIClient()
    session.force_login(user)

    url = base + f"/staff/{user.id}/"
    assert setup["client"].delete(url).status_code == 204
    assert setup["client"].delete(url).status_code == 404
    assert str(user.id) not in {s["id"] for s in setup["client"].get(base + "/staff/").json()}
    assert User.objects.get(id=user.id).is_active
    assert session.get(base + "/tasks/").status_code == 403
    assert session.get(base + "/staff/").status_code == 403
    assert [b["id"] for b in session.get("/api/v1/businesses/").json()] == [
        str(setup["other_business"].id)
    ]
    assert session.get(f"/api/v1/businesses/{setup['other_business'].id}/staff/").status_code == 200


@pytest.mark.parametrize("actor", ["manager", "florist", "other_owner"])
def test_only_owner_can_remove_staff(setup, base, actor):
    setup["client"].force_login(setup[actor])
    assert setup["client"].delete(base + f"/staff/{setup['florist'].id}/").status_code == 403
    assert Membership.objects.filter(business=setup["business"], user=setup["florist"]).exists()


def test_cannot_remove_owners_or_foreign_staff_and_csrf_required(setup, base):
    client = setup["client"]
    assert client.delete(base + f"/staff/{setup['owner'].id}/").status_code == 400
    assert client.delete(base + f"/staff/{setup['other_owner'].id}/").status_code == 404
    assert client.delete(base + f"/staff/{uuid4()}/").status_code == 404
    membership = Membership.objects.create(
        business=setup["business"], user=setup["other_owner"], role="owner"
    )
    for active in (True, False):
        membership.is_active = active
        membership.save()
        assert client.delete(base + f"/staff/{membership.user_id}/").status_code == 400
    csrf_client = APIClient(enforce_csrf_checks=True)
    csrf_client.force_login(setup["owner"])
    assert csrf_client.delete(base + f"/staff/{setup['florist'].id}/").status_code == 403


@pytest.mark.parametrize("status", ["new", "work", "ready", "route"])
@pytest.mark.parametrize("assignment", ["florist", "courier"])
def test_unfinished_assignments_block_removal(setup, base, payload, status, assignment):
    order = create(setup, base, payload)
    user = setup["florist"]
    # Also cover inactive staff and a changed role with assignments still outstanding.
    Membership.objects.filter(business=setup["business"], user=user).update(is_active=False)
    OrderRecord.objects.filter(id=order["id"]).update(status=status, **{assignment: user})
    result = setup["client"].delete(base + f"/staff/{user.id}/")
    assert result.status_code == 409
    assert "незавершённые заказы" in result.json()["detail"]
    assert Membership.objects.filter(business=setup["business"], user=user).exists()
    assert getattr(OrderRecord.objects.get(id=order["id"]), assignment + "_id") == user.id


def test_can_remove_after_reassigning_and_cannot_assign_removed_staff(setup, base, payload):
    client = setup["client"]
    order = create(setup, base, payload)
    url = base + f"/orders/{order['id']}/assignment/"
    assignment = {"florist_id": str(setup["florist"].id), "courier_id": None}
    post(client, url, {**assignment, "version": 1})
    post(client, url, {"florist_id": None, "courier_id": None, "version": 2})
    assert client.delete(base + f"/staff/{setup['florist'].id}/").status_code == 204
    post(client, url, {**assignment, "version": 3}, 400)
    assert OrderRecord.objects.get(id=order["id"]).florist_id is None


@pytest.mark.parametrize("status", ["done", "cancelled"])
def test_completed_history_and_payments_survive_removal(setup, base, payload, status):
    client = setup["client"]
    client.force_login(setup["manager"])
    order = create(setup, base, {**payload, "fulfillment": "pickup", "address": ""})
    url = base + f"/orders/{order['id']}"
    post(
        client,
        url + "/payments/",
        {"amount": "100.00", "kind": "payment", "method": "cash"},
        201,
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    client.force_login(setup["florist"])
    order = post(client, url + "/transition/", {"version": 2, "status": "work"})
    order = post(client, url + "/transition/", {"version": 3, "status": "ready"})
    client.force_login(setup["owner"])
    order = post(
        client, url + "/transition/", {"version": 4, "status": status, "reason": "Отмена клиента"}
    )
    before = (
        client.get(url + "/").json(),
        client.get(url + "/history/").json(),
        list(PaymentRecord.objects.values()),
    )
    for actor in ("manager", "florist"):
        assert client.delete(base + f"/staff/{setup[actor].id}/").status_code == 204
    assert before == (
        client.get(url + "/").json(),
        client.get(url + "/history/").json(),
        list(PaymentRecord.objects.values()),
    )
    assert OrderEvent.objects.filter(order_id=order["id"], actor=setup["florist"]).exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("claim", [False, True])
def test_removal_cannot_race_assignment_or_florist_claim(setup, base, payload, claim):
    order = create(setup, base, payload)
    client = APIClient()
    client.force_login(setup["florist"] if claim else setup["owner"])
    barrier = Barrier(2)

    def run(remove):
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            if remove:
                return setup["client"].delete(base + f"/staff/{setup['florist'].id}/").status_code
            action = "transition" if claim else "assignment"
            data = (
                {"version": 1, "status": "work"}
                if claim
                else {"version": 1, "florist_id": str(setup["florist"].id), "courier_id": None}
            )
            return client.post(
                base + f"/orders/{order['id']}/{action}/", data, format="json"
            ).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        removed, assigned = list(pool.map(run, [True, False]))
    member_exists = Membership.objects.filter(
        business=setup["business"], user=setup["florist"]
    ).exists()
    saved_order = OrderRecord.objects.get(id=order["id"])
    if removed == 204:
        assert assigned == (403 if claim else 400)
        assert not member_exists and saved_order.florist_id is None
    else:
        assert (removed, assigned) == (409, 200)
        assert member_exists and saved_order.florist_id == setup["florist"].id
