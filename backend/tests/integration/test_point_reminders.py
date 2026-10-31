from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from test_points import add_point, create_order

from tapme.businesses.application.contracts import Scope
from tapme.businesses.models import Membership
from tapme.customers.models import CustomerRecord, ImportantDateRecord
from tapme.orders.models import OrderRecord
from tapme.reminders.domain import Scenario, ScenarioStep
from tapme.reminders.infrastructure.repository import DjangoReminderRepository
from tapme.reminders.models import ReminderRecord

NOW = datetime(2026, 10, 25, 6, tzinfo=UTC)


def queue(setup, base, payload):
    primary = setup["business"].shop
    second = add_point(setup, base)
    customer = setup["customer"]
    customer.consent = True
    customer.save()
    a = create_order(setup, base, payload, primary).data
    b = create_order(setup, base, payload, second).data
    new = CustomerRecord.objects.create(
        business=setup["business"], name="Новый клиент", phone="+996555444333", consent=True
    )
    for client in (customer, new):
        ImportantDateRecord.objects.create(customer=client, label="День рождения", month=10, day=26)
    repo = DjangoReminderRepository()
    assert repo.generate(setup["business"].id, NOW, (second.id,)) == 1
    rows = {r.customer_id: r for r in ReminderRecord.objects.all()}
    assert rows[customer.id].point_id == second.id
    assert rows[new.id].point_id == primary.id
    assert repo.generate(setup["business"].id, NOW) == 0
    return primary, second, rows[customer.id], rows[new.id], a, b


def test_reminder_queue_counters_history_and_owner_switch(setup, base, payload):
    primary, second, row, other, a, b = queue(setup, base, payload)
    c = setup["client"]
    for point, expected in [(primary.id, other), (second.id, row)]:
        response = c.get(base + f"/reminders/?point={point}")
        assert response.status_code == 200, response.data
        data = response.data
        assert data["count"] == 1
        assert str(data["results"][0]["id"]) == str(expected.id)
        assert data["stats"]["wait"] == 1
        assert c.get(base + f"/overview/?point={point}").data["reminders"] == 1
    assert c.get(base + "/reminders/?point=all").data["count"] == 2
    Membership.objects.get(user=setup["manager"]).points.set([primary])
    c.force_login(setup["manager"])
    assert c.get(base + "/reminders/").data["count"] == 1
    assert c.get(base + f"/reminders/?point={second.id}").status_code == 403
    activity = c.get(base + f"/customers/{setup['customer'].id}/activity/").data
    assert activity["reminders"] == []
    assert c.get(base + "/overview/").data["reminders"] == 1
    c.force_login(setup["owner"])
    data = c.get(base + f"/reminders/?point={second.id}").data["results"][0]
    assert str(data["last_order"]["id"]) == b["id"]
    # Already generated reminders keep their assignment after a newer order at another point.
    create_order(setup, base, payload, primary)
    assert DjangoReminderRepository().generate(setup["business"].id, NOW) == 0
    row.refresh_from_db()
    assert row.point_id == second.id


@pytest.mark.parametrize("action", ["prepare", "edit", "open", "skip", "opt_out", "link"])
def test_other_point_reminder_cannot_be_read_or_changed(setup, base, payload, action):
    primary, _, row, _, _, b = queue(setup, base, payload)
    Membership.objects.get(user=setup["manager"]).points.set([primary])
    c = setup["client"]
    c.force_login(setup["manager"])
    path = base + f"/reminders/{row.id}/"
    if action == "prepare":
        response = c.get(path + "message/")
    elif action == "edit":
        response = c.patch(path + "message/", {"message": "Подмена"}, format="json")
    elif action == "open":
        response = c.post(path + "open/", {}, format="json")
    else:
        data = {"action": {"skip": "skipped", "opt_out": "opt_out", "link": "ordered"}[action]}
        if action == "link":
            data["order_id"] = b["id"]
        response = c.post(path + "action/", data, format="json")
    assert response.status_code == 404, response.data
    row.refresh_from_db()
    setup["customer"].refresh_from_db()
    assert row.state == "wait" and row.message == "" and setup["customer"].consent


def test_after_delivery_reminder_belongs_to_delivered_orders_point(setup, base, payload):
    primary = setup["business"].shop
    second = add_point(setup, base)
    customer = setup["customer"]
    customer.consent = True
    customer.save()
    orders = [create_order(setup, base, payload, p).data for p in (primary, second)]
    OrderRecord.objects.filter(id__in=[o["id"] for o in orders]).update(
        status="done", completed_at=NOW
    )
    repo = DjangoReminderRepository()
    config = repo.configuration(setup["business"].id)
    followup = Scenario(
        uuid4(), "После вручения", "after_delivery", (ScenarioStep(uuid4(), 0, "Спасибо, {имя}"),)
    )
    repo.save_configuration(setup["business"].id, replace(config, scenarios=(followup,)))
    assert repo.generate(setup["business"].id, NOW) == 2
    assert set(ReminderRecord.objects.values_list("point_id", flat=True)) == {primary.id, second.id}
    assert (
        repo.list(Scope(setup["owner"].id, setup["business"].id, primary.id), "wait", 50, 0, NOW)[
            "count"
        ]
        == 1
    )
