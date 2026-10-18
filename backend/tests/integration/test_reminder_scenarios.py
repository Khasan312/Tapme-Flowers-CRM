from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from django.db import close_old_connections

from tapme.businesses.application.contracts import Scope
from tapme.customers.models import CustomerRecord, ImportantDateRecord
from tapme.orders.models import OrderRecord
from tapme.reminders.domain import Scenario, ScenarioStep
from tapme.reminders.infrastructure.repository import DjangoReminderRepository
from tapme.reminders.models import ReminderRecord, ReminderScenario, ReminderSettings, ReminderStep
from tapme.shared.domain import Conflict, InvalidInput

NOW = datetime(2026, 10, 17, 6, tzinfo=UTC)


def prepare(setup):
    customer = setup["customer"]
    customer.consent = True
    customer.save()
    event = ImportantDateRecord.objects.create(
        customer=customer, label="День рождения", person="Мама", month=10, day=18
    )
    repo = DjangoReminderRepository()
    repo.generate(setup["business"].id, NOW)
    return repo, ReminderRecord.objects.get(customer=customer), event


def test_existing_keys_messages_and_templates_are_migrated_once(setup):
    rules = ReminderSettings.objects.create(
        business=setup["business"],
        offsets=[7, 1],
        template="Свой {name}: {event}",
        inactive_template="Давно ждём, {имя}",
    )
    event = ImportantDateRecord.objects.create(
        customer=setup["customer"], label="Свадьба", person="Мама", month=10, day=18
    )
    old = ReminderRecord.objects.create(
        business=setup["business"],
        customer=setup["customer"],
        key=f"date:{event.id}:2026:1",
        event=event.label,
        person=event.person,
        due_date=date(2026, 10, 17),
        state="sent",
        message="Уже отправленный текст",
        acted_at=NOW,
    )
    repo = DjangoReminderRepository()
    config = repo.configuration(setup["business"].id)
    old.refresh_from_db()
    assert old.message == "Уже отправленный текст" and old.state == "sent"
    assert old.scenario.name == "Годовщина и свадьба"
    assert old.step.offset_days == 1 and old.sent_at == NOW
    assert old.event_date == date(2026, 10, 18)
    assert config.version == rules.version
    assert all(s.template == "Свой {name}: {event}" for s in config.scenarios[0].steps)
    assert config.scenarios[3].steps[0].template == "Давно ждём, {имя}"
    repo.configuration(setup["business"].id)
    setup["customer"].consent = True
    setup["customer"].save()
    assert repo.generate(setup["business"].id, NOW) == 0
    assert ReminderScenario.objects.count() == 6


def test_configuration_permissions_versions_and_template_compatibility(setup, base):
    c = setup["client"]
    url = base + "/reminder-scenarios/"
    original = c.get(url).json()
    assert len(original["scenarios"]) == 6
    changed = {**original, "start_hour": 8, "min_days_between": 2}
    assert c.put(url, changed, format="json").status_code == 200
    assert c.put(url, original, format="json").status_code == 409
    legacy = c.get(base + "/reminder-rules/").json()
    assert legacy["start_hour"] == 8
    legacy["templates"]["d7"] = "Новый старый шаблон {имя}"
    assert c.put(base + "/reminder-rules/", legacy, format="json").status_code == 200
    assert all(
        s.template == "Новый старый шаблон {имя}"
        for s in ReminderStep.objects.filter(scenario__legacy_kind="date", offset_days=7)
    )
    c.force_login(setup["manager"])
    assert c.get(url).status_code == 200
    assert c.put(url, changed, format="json").status_code == 403
    c.force_login(setup["florist"])
    assert c.get(url).status_code == 403
    c.force_login(setup["other_owner"])
    assert c.get(url).status_code == 403


def test_invalid_scenario_update_is_atomic_and_foreign_ids_rejected(setup, base):
    c = setup["client"]
    repo = DjangoReminderRepository()
    config = c.get(base + "/reminder-scenarios/").json()
    foreign = repo.configuration(setup["other_business"].id)
    config["scenarios"][0]["steps"][0]["id"] = str(foreign.scenarios[0].steps[0].id)
    config["scenarios"][0]["name"] = "Не должно сохраниться"
    assert c.put(base + "/reminder-scenarios/", config, format="json").status_code == 400
    assert repo.configuration(setup["business"].id).scenarios[0].name == "День рождения"
    config = c.get(base + "/reminder-scenarios/").json()
    config["scenarios"][0]["steps"][0]["template"] = "{неизвестная}"
    assert c.put(base + "/reminder-scenarios/", config, format="json").status_code == 400
    config["scenarios"][0]["steps"][0]["template"] = "Привет, {имя}"
    config["scenarios"][0]["steps"][0]["offset_days"] = config["scenarios"][0]["steps"][1][
        "offset_days"
    ]
    assert c.put(base + "/reminder-scenarios/", config, format="json").status_code == 400


def test_scenario_offsets_and_specific_templates_control_generation(setup):
    repo, old, event = prepare(setup)
    config = repo.configuration(setup["business"].id)
    birthday = config.scenarios[0]
    kept = replace(birthday.steps[-1], template="Свои {name} {event} {дата}", offset_days=2)
    repo.save_configuration(
        setup["business"].id,
        replace(config, scenarios=(replace(birthday, steps=(kept,)), *config.scenarios[1:])),
    )
    assert repo.generate(setup["business"].id, NOW) == 0  # stable migrated step, already queued
    assert repo.prepare(setup["business"].id, old.id, NOW)["message"].endswith("18.10.2026")
    config = repo.configuration(setup["business"].id)
    repo.save_configuration(
        setup["business"].id,
        replace(
            config, scenarios=(replace(config.scenarios[0], enabled=False), *config.scenarios[1:])
        ),
    )
    with pytest.raises(InvalidInput, match="выключен"):
        repo.prepare(setup["business"].id, old.id, NOW)
    assert repo.generate(setup["business"].id, NOW + timedelta(days=1)) == 0


def test_archive_keeps_history_and_blocks_pending_message(setup):
    repo, row, _ = prepare(setup)
    config = repo.configuration(setup["business"].id)
    repo.save_configuration(setup["business"].id, replace(config, scenarios=config.scenarios[1:]))
    row.refresh_from_db()
    assert row.scenario.archived and row.step.archived
    with pytest.raises(InvalidInput):
        repo.open_message(Scope(setup["owner"].id, setup["business"].id), row.id, NOW)
    assert ReminderRecord.objects.filter(id=row.id).exists()


def test_open_undo_snapshot_frequency_quiet_hours_and_consent(setup):
    repo, row, _ = prepare(setup)
    scope = Scope(setup["owner"].id, setup["business"].id)
    repo.edit_message(scope, row.id, "Личный текст для мамы")
    with pytest.raises(InvalidInput, match="тихие"):
        repo.open_message(scope, row.id, NOW.replace(hour=20))
    result = repo.open_message(scope, row.id, NOW)
    row.refresh_from_db()
    assert result["message"] == row.message == "Личный текст для мамы"
    assert row.sent_at == NOW and row.state == "sent"
    with pytest.raises(Conflict):
        repo.open_message(scope, row.id, NOW)
    with pytest.raises(Conflict):
        repo.act(Scope(setup["manager"].id, scope.business_id), row.id, "undo", NOW)
    repo.act(scope, row.id, "undo", NOW + timedelta(seconds=5))
    row.refresh_from_db()
    assert row.state == "wait" and row.sent_at is None
    repo.open_message(scope, row.id, NOW)
    with pytest.raises(Conflict):
        repo.act(scope, row.id, "undo", NOW + timedelta(seconds=11))
    other = ReminderRecord.objects.create(
        business=setup["business"],
        customer=setup["customer"],
        key="new-test",
        event="Повод",
        due_date=date(2026, 10, 17),
    )
    config = repo.configuration(scope.business_id)
    repo.save_configuration(scope.business_id, replace(config, min_days_between=7))
    with pytest.raises(InvalidInput, match="Не чаще"):
        repo.open_message(scope, other.id, NOW)
    repo.act(scope, other.id, "opt_out", NOW)
    setup["customer"].refresh_from_db()
    other.refresh_from_db()
    assert not setup["customer"].consent and other.opt_out_at == NOW


def test_snooze_counts_and_skip_suppresses_event_year(setup):
    repo, row, _ = prepare(setup)
    scope = Scope(setup["owner"].id, setup["business"].id)
    repo.act(scope, row.id, "tomorrow", NOW)
    result = repo.list(scope.business_id, "wait", 50, 0, NOW)
    assert result["count"] == 0 and result["stats"].get("wait", 0) == 0
    result = repo.list(scope.business_id, "wait", 50, 0, NOW + timedelta(days=1))
    assert result["count"] == 1 and result["results"][0]["event_date"] == date(2026, 10, 18)
    repo.act(scope, row.id, "skipped", NOW + timedelta(days=1))
    config = repo.configuration(scope.business_id)
    birthday = config.scenarios[0]
    repo.save_configuration(
        scope.business_id,
        replace(
            config,
            scenarios=(
                replace(
                    birthday, steps=(*birthday.steps, ScenarioStep(uuid4(), 0, "Сегодня {имя}"))
                ),
                *config.scenarios[1:],
            ),
        ),
    )
    assert repo.generate(scope.business_id, NOW + timedelta(days=1)) == 0


def test_holiday_daily_cap_drains_next_day_without_duplicates(setup):
    repo = DjangoReminderRepository()
    for index in range(5):
        CustomerRecord.objects.create(
            business=setup["business"],
            name=f"Клиент {index}",
            phone=f"+99655512345{index}",
            consent=True,
        )
    config = repo.configuration(setup["business"].id)
    holiday = Scenario(
        uuid4(),
        "Праздник",
        "holiday",
        (ScenarioStep(uuid4(), 5, "С праздником, {имя}!"),),
        holiday_month=10,
        holiday_day=20,
        daily_cap=2,
    )
    repo.save_configuration(setup["business"].id, replace(config, scenarios=(holiday,)))
    assert repo.generate(setup["business"].id, NOW) == 2
    assert repo.generate(setup["business"].id, NOW) == 0
    assert repo.generate(setup["business"].id, NOW + timedelta(days=1)) == 2
    assert repo.generate(setup["business"].id, NOW + timedelta(days=2)) == 1
    assert ReminderRecord.objects.count() == 5


def create_order(setup, base, payload):
    response = setup["client"].post(
        base + "/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    )
    assert response.status_code == 201, response.data
    return OrderRecord.objects.get(id=response.json()["id"])


def test_after_delivery_and_inactive_use_actual_completed_order(setup, base, payload):
    setup["customer"].consent = True
    setup["customer"].save()
    order = create_order(setup, base, payload)
    order.status, order.completed_at = "done", NOW - timedelta(days=90)
    order.save()
    repo = DjangoReminderRepository()
    assert repo.generate(setup["business"].id, NOW) == 1
    assert ReminderRecord.objects.get().scenario.kind == "after_last_order"
    config = repo.configuration(setup["business"].id)
    delivery = replace(config.scenarios[4], enabled=True)
    repo.save_configuration(setup["business"].id, replace(config, scenarios=(delivery,)))
    # A much older delivery is not recovered as a new thank-you.
    assert repo.generate(setup["business"].id, NOW) == 0
    order.completed_at = NOW
    order.save()
    assert repo.generate(setup["business"].id, NOW + timedelta(days=1)) == 1
    assert repo.generate(setup["business"].id, NOW + timedelta(days=1)) == 0


def test_link_order_requires_same_customer_and_new_order_revenue_is_unique(setup, base, payload):
    repo, row, _ = prepare(setup)
    scope = Scope(setup["owner"].id, setup["business"].id)
    repo.open_message(scope, row.id, NOW)
    order = create_order(setup, base, payload)
    order.created_at = NOW - timedelta(days=1)
    order.save()
    with pytest.raises(InvalidInput):
        repo.act(scope, row.id, "ordered", NOW, order.id)
    order.created_at = NOW + timedelta(minutes=5)
    order.save()
    repo.act(scope, row.id, "ordered", NOW + timedelta(minutes=10), order.id)
    result = repo.list(scope.business_id, "ordered", 50, 0, NOW)
    assert result["summary"]["ordered_week"] == 1
    assert result["summary"]["revenue_week"] == str(order.total)
    order.status = "cancelled"
    order.save()
    assert repo.list(scope.business_id, "ordered", 50, 0, NOW)["summary"]["ordered_week"] == 0


@pytest.mark.django_db(transaction=True)
def test_simultaneous_open_cannot_mark_two_messages_with_frequency_limit(setup):
    repo, row, _ = prepare(setup)
    scope = Scope(setup["owner"].id, setup["business"].id)
    config = repo.configuration(scope.business_id)
    repo.save_configuration(scope.business_id, replace(config, min_days_between=7))
    other = ReminderRecord.objects.create(
        business=setup["business"],
        customer=setup["customer"],
        key="concurrent-test",
        event="Повод",
        due_date=date(2026, 10, 17),
    )
    barrier = Barrier(2)

    def send(identity):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            DjangoReminderRepository().open_message(scope, identity, NOW)
            return "sent"
        except InvalidInput:
            return "blocked"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(send, [row.id, other.id])) == ["blocked", "sent"]


def test_enabled_replacement_scenario_is_not_hidden_by_disabled_preset(setup):
    repo = DjangoReminderRepository()
    config = repo.configuration(setup["business"].id)
    setup["customer"].consent = True
    setup["customer"].save()
    ImportantDateRecord.objects.create(
        customer=setup["customer"], label="День рождения", person="Мама", month=10, day=18
    )
    replacement = Scenario(
        uuid4(),
        "Мой день рождения",
        "before_event",
        (ScenarioStep(uuid4(), 1, "Особый букет, {имя}?"),),
        event_labels=("День рождения",),
    )
    repo.save_configuration(
        setup["business"].id,
        replace(
            config,
            scenarios=(
                replace(config.scenarios[0], enabled=False),
                *config.scenarios[1:],
                replacement,
            ),
        ),
    )
    assert repo.generate(setup["business"].id, NOW) == 1
    assert ReminderRecord.objects.get().scenario_id == replacement.id
