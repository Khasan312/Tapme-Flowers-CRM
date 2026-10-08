from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient

from tapme.accounts.models import User
from tapme.businesses.application.contracts import Scope
from tapme.businesses.models import Membership, Shop
from tapme.customers.models import ImportantDateRecord
from tapme.orders.models import OrderRecord
from tapme.reminders.domain import DEFAULT_TEMPLATE, render_template
from tapme.reminders.infrastructure.repository import DjangoReminderRepository
from tapme.reminders.models import ReminderRecord, ReminderSettings
from tapme.shared.domain import InvalidInput

pytestmark = pytest.mark.django_db


def create(setup, base, payload):
    result = setup["client"].post(
        base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    )
    assert result.status_code == 201, result.data
    return result.json()


@pytest.mark.parametrize(
    "resource,field", [("settings", "address"), ("reminder-rules", "template")]
)
def test_stale_settings_cannot_overwrite_and_can_reload(setup, base, resource, field):
    c, url = setup["client"], f"{base}/{resource}/"
    original = c.get(url).json()
    first = c.put(url, {**original, field: "Первое изменение"}, format="json")
    assert first.status_code == 200, first.data
    assert first.json()["version"] == original["version"] + 1
    assert c.put(url, {**original, field: "Старая вкладка"}, format="json").status_code == 409
    assert c.get(url).json() == first.json()
    without_version = {k: v for k, v in original.items() if k != "version"}
    assert c.put(url, without_version, format="json").status_code == 400
    latest = c.get(url).json()
    result = c.put(url, {**latest, field: "После обновления"}, format="json")
    assert result.status_code == 200 and result.json()["version"] == latest["version"] + 1


def test_stale_rules_do_not_erase_custom_templates(setup, base):
    c, url = setup["client"], base + "/reminder-rules/"
    old = c.get(url).json()
    custom = {"id": str(uuid4()), "name": "Свой", "text": "Здравствуйте, {имя}!"}
    assert c.put(url, {**old, "custom_templates": [custom]}, format="json").status_code == 200
    old.pop("custom_templates")
    assert c.put(url, old, format="json").status_code == 409
    assert c.get(url).json()["custom_templates"] == [custom]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "resource,field", [("settings", "address"), ("reminder-rules", "template")]
)
def test_concurrent_settings_saves_have_only_one_winner(setup, base, resource, field):
    url = f"{base}/{resource}/"
    old = setup["client"].get(url).json()
    barrier = Barrier(2)

    def submit(index):
        close_old_connections()
        try:
            c = APIClient()
            c.force_authenticate(setup["owner"])
            barrier.wait(timeout=10)
            return c.put(url, {**old, field: f"Вкладка {index}"}, format="json").status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, range(2))) == [200, 409]
    assert setup["client"].get(url).json()["version"] == old["version"] + 1


def route_order(setup, base, payload):
    couriers = []
    for name in ("previous", "replacement"):
        user = User.objects.create_user(username=name)
        Membership.objects.create(user=user, business=setup["business"], role="courier")
        couriers.append(user)
    order = create(setup, base, payload)
    url = base + f"/orders/{order['id']}"
    c = setup["client"]
    r = c.post(
        url + "/assignment/",
        dict(
            version=order["version"],
            florist_id=str(setup["florist"].id),
            courier_id=str(couriers[0].id),
        ),
        format="json",
    )
    assert r.status_code == 200, r.data
    order = r.json()
    for status in ["work", "ready", "route"]:
        r = c.post(
            url + "/transition/", dict(version=order["version"], status=status), format="json"
        )
        assert r.status_code == 200, r.data
        order = r.json()
    return url, order, couriers


@pytest.mark.parametrize("actor", ["owner", "manager"])
@pytest.mark.parametrize(
    "change", [{"role": "courier", "is_active": False}, {"role": "manager", "is_active": True}]
)
def test_reassign_in_route_after_courier_access_changed(setup, base, payload, actor, change):
    url, order, (previous, replacement) = route_order(setup, base, payload)
    c = setup["client"]
    assert c.put(base + f"/staff/{previous.id}/", change, format="json").status_code == 204
    # Even an unavailable florist must not prevent changing the courier.
    Membership.objects.filter(user=setup["florist"]).update(is_active=False)
    if not change["is_active"]:
        c.force_login(previous)
        assert (
            c.post(
                url + "/transition/", dict(version=order["version"], status="done"), format="json"
            ).status_code
            == 403
        )
    c.force_login(setup[actor])
    body = dict(
        version=order["version"], florist_id=order["florist_id"], courier_id=str(replacement.id)
    )
    r = c.post(url + "/assignment/", body, format="json")
    assert r.status_code == 200, r.data
    assert r.json()["status"] == "route"
    assert r.json()["florist_id"] == order["florist_id"]
    assert r.json()["courier_id"] == str(replacement.id)
    assert c.post(url + "/assignment/", body, format="json").status_code == 409
    assert "courier_reassigned" in [e["kind"] for e in c.get(url + "/history/").json()]
    # Restore previous courier's role/access: the old assignment still grants no access.
    Membership.objects.filter(user=previous).update(role="courier", is_active=True)
    c.force_login(previous)
    assert c.get(base + "/tasks/").json()["count"] == 0
    assert (
        c.post(
            url + "/transition/", dict(version=r.json()["version"], status="done"), format="json"
        ).status_code
        == 403
    )
    c.force_login(replacement)
    assert c.get(base + "/tasks/").json()["count"] == 1
    finished = c.post(
        url + "/transition/", dict(version=r.json()["version"], status="done"), format="json"
    )
    assert finished.status_code == 200, finished.data
    c.force_login(setup["owner"])
    assert (
        c.post(
            url + "/assignment/", {**body, "version": finished.json()["version"]}, format="json"
        ).status_code
        == 400
    )


def test_route_reassignment_rejects_wrong_staff_and_florist_changes(setup, base, payload):
    url, order, (previous, replacement) = route_order(setup, base, payload)
    c = setup["client"]
    body = dict(
        version=order["version"], florist_id=order["florist_id"], courier_id=str(replacement.id)
    )
    Membership.objects.filter(user=replacement).update(is_active=False)
    for change in [
        {},
        {"courier_id": None},
        {"courier_id": str(setup["other_owner"].id)},
        {"courier_id": str(setup["florist"].id)},
        {"courier_id": str(previous.id), "florist_id": None},
    ]:
        r = c.post(url + "/assignment/", {**body, **change}, format="json")
        assert r.status_code == 400, r.data
    c.force_login(previous)
    assert c.post(url + "/assignment/", body, format="json").status_code == 403
    stored = OrderRecord.objects.get(id=order["id"])
    assert stored.version == order["version"] and stored.courier_id == previous.id


@pytest.mark.parametrize("change", ["deleted", "full", "price"])
def test_old_window_can_edit_without_repricing_but_new_bookings_validate(
    setup, base, payload, change
):
    c = setup["client"]
    shop = Shop.objects.get(business=setup["business"])
    shop.delivery_windows = [
        dict(start="10:00", end="12:00", capacity=2, price="300.00"),
        dict(start="12:00", end="14:00", capacity=2, price="500.00"),
    ]
    shop.enforce_capacity = True
    shop.save()
    order = create(setup, base, payload)
    create(setup, base, payload)
    settings = c.get(base + "/settings/").json()
    if change == "deleted":
        settings["windows"] = settings["windows"][1:]
    elif change == "full":
        settings["windows"][0]["capacity"] = 1
    else:
        settings["windows"][0]["price"] = "900.00"
    assert c.put(base + "/settings/", settings, format="json").status_code == 200
    url = base + f"/orders/{order['id']}/edit/"
    result = c.put(
        url, {**payload, "version": order["version"], "notes": "Уточнён подъезд"}, format="json"
    )
    assert result.status_code == 200, result.data
    assert result.json()["delivery_fee"] == "300.00"
    assert (
        c.post(
            base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
        ).status_code
        == 400
    )
    if change == "deleted":
        assert (
            c.put(
                url,
                {**payload, "version": result.json()["version"], "delivery_date": "2026-11-20"},
                format="json",
            ).status_code
            == 400
        )
    moved = c.put(
        url,
        {
            **payload,
            "version": result.json()["version"],
            "window_start": "12:00",
            "window_end": "14:00",
        },
        format="json",
    )
    assert moved.status_code == 200, moved.data
    assert moved.json()["delivery_fee"] == "500.00"


def reminders(setup, day=13):
    customer = setup["customer"]
    customer.consent = True
    customer.save()
    event = ImportantDateRecord.objects.create(
        customer=customer, label="День рождения", person="Мама", month=10, day=day
    )
    settings = ReminderSettings.objects.create(
        business=setup["business"], last_generated_at=datetime(2026, 10, 5, 8, tzinfo=UTC)
    )
    return DjangoReminderRepository(), settings, event


def test_missed_reminder_recovered_once_with_accurate_message(setup):
    repo, settings, event = reminders(setup)
    now = datetime(2026, 10, 7, 8, tzinfo=UTC)
    assert repo.generate(settings.business_id, now) == 1
    row = ReminderRecord.objects.get(business_id=settings.business_id)
    assert row.key == f"date:{event.id}:2026:7"
    assert row.due_date == date(2026, 10, 6) and row.recovered
    assert row.state == "wait" and not row.message and row.acted_at is None
    assert repo.generate(settings.business_id, now) == 0
    assert repo.generate(settings.business_id, now + timedelta(days=1)) == 0
    expected = render_template(
        DEFAULT_TEMPLATE,
        dict(
            name=setup["customer"].name,
            person="Мама",
            event="День рождения",
            shop=setup["business"].name,
        ),
    )
    assert repo.prepare(settings.business_id, row.id, now)["message"] == expected
    listed = repo.list(settings.business_id, "wait", 50, 0, now)["results"][0]
    assert listed["preview"] == expected and listed["recovered"]
    scope = Scope(setup["owner"].id, settings.business_id)
    repo.act(scope, row.id, "sent", now)
    row.refresh_from_db()
    assert row.message == expected
    settings.refresh_from_db()
    assert settings.version == 1  # Background jobs do not invalidate an open settings form.


def test_long_outage_recovers_latest_only_and_excludes_past_events(setup):
    repo, settings, event = reminders(setup)
    settings.last_generated_at = datetime(2026, 9, 1, tzinfo=UTC)
    settings.save()
    ImportantDateRecord.objects.create(
        customer=setup["customer"], label="Уже прошёл", person="Друг", month=10, day=10
    )
    assert repo.generate(settings.business_id, datetime(2026, 10, 12, 8, tzinfo=UTC)) == 1
    row = ReminderRecord.objects.get()
    assert row.key == f"date:{event.id}:2026:1" and not row.recovered


def test_generation_rollback_keeps_cursor_and_retries_every_customer(setup):
    repo, settings, _ = reminders(setup)
    now = datetime(2026, 10, 7, 8, tzinfo=UTC)
    with patch.object(
        ReminderRecord.objects, "get_or_create", side_effect=RuntimeError("temporary error")
    ):
        with pytest.raises(RuntimeError):
            repo.generate(settings.business_id, now)
    settings.refresh_from_db()
    assert settings.last_generated_at == datetime(2026, 10, 5, 8, tzinfo=UTC)
    assert not ReminderRecord.objects.exists()
    assert repo.generate(settings.business_id, now) == 1


def test_disabled_reminders_and_consent_do_not_send_catchup(setup):
    repo, settings, _ = reminders(setup)
    now = datetime(2026, 10, 7, 8, tzinfo=UTC)
    with patch(
        "tapme.reminders.infrastructure.repository.timezone.now",
        return_value=now - timedelta(days=2),
    ):
        repo.save_rules(
            settings.business_id, replace(repo.rules(settings.business_id), enabled=False)
        )
    assert repo.generate(settings.business_id, now) == 0
    with patch("tapme.reminders.infrastructure.repository.timezone.now", return_value=now):
        repo.save_rules(
            settings.business_id, replace(repo.rules(settings.business_id), enabled=True)
        )
    assert repo.generate(settings.business_id, now) == 0
    # New installations recover upcoming dates, but consent and quiet hours still apply.
    settings.refresh_from_db()
    settings.last_generated_at = None
    settings.save()
    setup["customer"].consent = False
    setup["customer"].save()
    assert repo.generate(settings.business_id, now) == 0
    settings.last_generated_at = None
    settings.save()
    setup["customer"].consent = True
    setup["customer"].save()
    assert repo.generate(settings.business_id, now) == 1
    row = ReminderRecord.objects.get()
    with pytest.raises(InvalidInput):
        repo.prepare(settings.business_id, row.id, now.replace(hour=17))
    repo.act(Scope(setup["owner"].id, settings.business_id), row.id, "skipped", now)
    assert repo.generate(settings.business_id, now + timedelta(days=3)) == 0


@pytest.mark.django_db(transaction=True)
def test_concurrent_recovery_is_idempotent(setup):
    _, settings, _ = reminders(setup)
    barrier = Barrier(2)

    def generate(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return DjangoReminderRepository().generate(
                settings.business_id, datetime(2026, 10, 7, 8, tzinfo=UTC)
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(generate, range(2))) == [0, 1]
    assert ReminderRecord.objects.count() == 1


def test_recovery_cursor_uses_shop_local_day(setup):
    repo, settings, event = reminders(setup)
    # It is October 7 in Bishkek, but still October 6 in UTC.
    now = datetime(2026, 10, 6, 19, tzinfo=UTC)
    assert repo.generate(settings.business_id, now) == 1
    row = ReminderRecord.objects.get()
    assert row.key == f"date:{event.id}:2026:7" and row.recovered
    assert repo.generate(settings.business_id, now + timedelta(hours=1)) == 0


def test_recovery_respects_open_complaints(setup, base, payload):
    repo, settings, _ = reminders(setup)
    now = datetime(2026, 10, 7, 8, tzinfo=UTC)
    order = create(setup, base, payload)
    assert (
        setup["client"]
        .post(
            base + f"/orders/{order['id']}/feedback/",
            {"kind": "complaint", "message": "Проблема с доставкой"},
            format="json",
        )
        .status_code
        == 201
    )
    assert repo.generate(settings.business_id, now) == 0
    assert not ReminderRecord.objects.exists()
