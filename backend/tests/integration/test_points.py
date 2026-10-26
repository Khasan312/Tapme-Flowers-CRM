from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient

from tapme.businesses.models import Membership, Shop
from tapme.orders.models import OrderRecord


def create_order(setup, base, payload, point=None):
    return setup["client"].post(
        base + "/orders/",
        {**payload, **({"point_id": str(point.id)} if point else {})},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )


def add_point(setup, base, **values):
    response = setup["client"].post(
        base + "/points/",
        {"name": "Филиал Чуй", "short_name": "Чуй", "address": "Чуй, 12", **values},
        format="json",
    )
    assert response.status_code == 201, response.data
    return Shop.objects.get(id=response.data["id"])


def test_create_points_preserves_staff_and_requires_explicit_order_point(setup, base, payload):
    primary = setup["business"].shop
    old = create_order(setup, base, payload)
    assert old.status_code == 201
    assert old.data["point_id"] == str(primary.id)
    second = add_point(setup, base)
    third = add_point(setup, base, name="Филиал Юг", short_name="Юг")
    assert set(setup["client"].get(base + "/points/").data[i]["id"] for i in range(3)) == {
        str(p.id) for p in [primary, second, third]
    }
    assert Membership.objects.get(user=setup["florist"]).points.get() == primary
    assert create_order(setup, base, payload).status_code == 400
    result = create_order(setup, base, payload, second)
    assert result.status_code == 201
    assert result.data["point_name"] == "Чуй"
    assert result.data["number"] == old.data["number"] + 1
    foreign = setup["other_business"].shop
    assert create_order(setup, base, payload, foreign).status_code == 400


def test_primary_switch_stale_settings_and_archive(setup, base, payload):
    primary = setup["business"].shop
    primary.version = 3
    primary.save(update_fields=["version"])
    stale_settings = setup["client"].get(base + "/settings/").data
    second = add_point(setup, base)
    path = base + f"/points/{second.id}/"
    response = setup["client"].patch(
        path, {"version": second.version, "is_primary": True}, format="json"
    )
    assert response.status_code == 200
    assert response.data["version"] > stale_settings["version"]
    assert (
        setup["client"].put(base + "/settings/", stale_settings, format="json").status_code == 409
    )
    assert setup["business"].points.filter(is_primary=True).get().id == second.id
    assert (
        setup["client"]
        .patch(path, {"version": second.version, "name": "Старые данные"}, format="json")
        .status_code
        == 409
    )
    assert (
        setup["client"]
        .post(path + "archive/", {"version": response.data["version"]}, format="json")
        .status_code
        == 409
    )
    # Creation into former primary still works until archived.
    result = create_order(setup, base, payload, primary)
    assert result.status_code == 201
    primary.refresh_from_db()
    archive = base + f"/points/{primary.id}/archive/"
    assert (
        setup["client"].post(archive, {"version": primary.version}, format="json").status_code
        == 409
    )
    OrderRecord.objects.filter(id=result.data["id"]).update(status="cancelled")
    assert (
        setup["client"].post(archive, {"version": primary.version}, format="json").status_code
        == 204
    )
    assert create_order(setup, base, payload, primary).status_code == 400
    assert setup["client"].get(base + "/orders/?point=all").data["count"] == 1


@pytest.mark.parametrize("role", ["manager", "florist"])
def test_only_owner_manages_points(setup, base, role):
    setup["client"].force_login(setup[role])
    assert (
        setup["client"]
        .post(base + "/points/", {"name": "Точка", "short_name": "Точка"}, format="json")
        .status_code
        == 403
    )


def test_scoped_orders_counters_search_and_shared_customers(setup, base, payload):
    primary = setup["business"].shop
    second = add_point(setup, base)
    a = create_order(setup, base, payload, primary).data
    b = create_order(setup, base, payload, second).data
    for resource in ["orders", "orders/desk?scope=all"]:
        path = base + ("/orders/?" if resource == "orders" else "/orders/desk/?scope=all&")
        assert setup["client"].get(path + f"point={second.id}").data["count"] == 1
    assert setup["client"].get(base + f"/overview/?point={second.id}").data["orders"] == 1
    assert setup["client"].get(base + "/overview/?point=all").data["orders"] == 2
    Membership.objects.get(user=setup["manager"]).points.set([primary])
    setup["client"].force_login(setup["manager"])
    assert setup["client"].get(base + "/orders/?point=all").data["count"] == 1
    assert setup["client"].get(base + f"/orders/?point={second.id}").status_code == 403
    assert setup["client"].get(base + f"/orders/?search={b['id']}").data["count"] == 0
    assert setup["client"].get(base + f"/orders/{b['id']}/").status_code == 404
    assert setup["client"].get(base + f"/orders/{a['id']}/").status_code == 200
    assert setup["client"].get(base + "/customers/").data["count"] == 1
    activity = setup["client"].get(base + f"/customers/{setup['customer'].id}/activity/").data
    assert activity["order_count"] == 1
    assert activity["total"] == a["total"]
    assert setup["client"].get(base + f"/points/{second.id}/").status_code == 404
    assert setup["client"].get(base + "/orders/?point=invalid").status_code == 400


@pytest.mark.parametrize(
    "resource,method,data",
    [
        ("history", "get", {}),
        ("payments", "get", {}),
        ("photos", "get", {}),
        ("feedback", "get", {}),
        ("feedback", "post", {"kind": "review", "message": "Тест", "rating": 5}),
        ("share", "post", {}),
        ("assignment", "post", {"version": 1, "florist_id": None, "courier_id": None}),
        ("transition", "post", {"version": 1, "status": "cancelled", "reason": "Тест"}),
    ],
)
def test_point_boundary_on_every_order_endpoint(setup, base, payload, resource, method, data):
    primary = setup["business"].shop
    second = add_point(setup, base)
    order = create_order(setup, base, payload, second).data
    Membership.objects.get(user=setup["manager"]).points.set([primary])
    setup["client"].force_login(setup["manager"])
    path = base + f"/orders/{order['id']}/{resource}/"
    response = getattr(setup["client"], method)(path, data, format="json")
    assert response.status_code == 404, response.data
    assert OrderRecord.objects.get(id=order["id"]).status == "new"


def test_independent_slot_capacity_and_prices(setup, base, payload):
    primary = setup["business"].shop
    primary.enforce_capacity = True
    primary.delivery_windows = [
        {"start": "10:00", "end": "12:00", "capacity": 1, "price": "100.00"}
    ]
    primary.save()
    second = add_point(
        setup,
        base,
        enforce_capacity=True,
        windows=[{"start": "10:00", "end": "12:00", "capacity": 1, "price": "200.00"}],
    )
    assert create_order(setup, base, payload, primary).data["delivery_fee"] == "100.00"
    assert create_order(setup, base, payload, primary).status_code == 400
    assert create_order(setup, base, payload, second).data["delivery_fee"] == "200.00"
    assert create_order(setup, base, payload, second).status_code == 400


def test_florist_scope_assignment_and_removal_guard(setup, base, payload):
    primary = setup["business"].shop
    second = add_point(setup, base)
    a = create_order(setup, base, payload, primary).data
    b = create_order(setup, base, payload, second).data
    assert (
        setup["client"]
        .post(
            base + f"/orders/{b['id']}/assignment/",
            {"version": 1, "florist_id": str(setup["florist"].id), "courier_id": None},
            format="json",
        )
        .status_code
        == 400
    )
    setup["client"].force_login(setup["florist"])
    assert setup["client"].get(base + "/tasks/").data["count"] == 1
    assert (
        setup["client"]
        .post(
            base + f"/orders/{b['id']}/transition/", {"version": 1, "status": "work"}, format="json"
        )
        .status_code
        == 404
    )
    assert (
        setup["client"]
        .post(
            base + f"/orders/{a['id']}/transition/", {"version": 1, "status": "work"}, format="json"
        )
        .status_code
        == 200
    )
    setup["client"].force_login(setup["owner"])
    path = base + f"/staff/{setup['florist'].id}/points/"
    assert (
        setup["client"].put(path, {"point_ids": [str(second.id)]}, format="json").status_code == 409
    )
    assert (
        setup["client"]
        .put(path, {"point_ids": [str(primary.id), str(second.id)]}, format="json")
        .status_code
        == 204
    )
    setup["client"].force_login(setup["florist"])
    assert setup["client"].get(base + "/tasks/").data["count"] == 2


def test_point_public_contact_and_legacy_settings(setup, base, payload):
    primary = setup["business"].shop
    second = add_point(setup, base, phone="+996555888777")
    order = create_order(setup, base, payload, second).data
    link = setup["client"].post(base + f"/orders/{order['id']}/share/", {}, format="json")
    assert link.status_code == 200
    token = link.data.get("token")
    assert token
    public = APIClient().get(f"/api/v1/public/orders/{token}/").data
    assert public["shop_name"] == "Филиал Чуй"
    assert public["shop_phone"] == "+996555888777"
    Membership.objects.get(user=setup["manager"]).points.set([second])
    setup["client"].force_login(setup["manager"])
    assert setup["client"].get(base + "/settings/").status_code == 404
    assert (
        setup["client"].get(base + "/settings/", HTTP_X_TAPME_POINT=str(second.id)).data["name"]
        == second.name
    )
    assert primary.id != second.id


@pytest.mark.django_db(transaction=True)
def test_concurrent_orders_across_points_keep_unique_numbers(setup, base, payload):
    primary = setup["business"].shop
    second = add_point(setup, base)
    barrier = Barrier(2)

    def submit(point):
        close_old_connections()
        try:
            client = APIClient()
            client.force_authenticate(setup["owner"])
            barrier.wait(timeout=5)
            return client.post(
                base + "/orders/",
                {**payload, "point_id": str(point.id)},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid4()),
            ).data
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [primary, second]))
    assert {r["number"] for r in results} == {1, 2}
