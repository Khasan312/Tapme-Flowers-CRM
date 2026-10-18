"""Persistence and migration of the legacy reminder rules into editable scenarios."""

from datetime import date

from tapme.customers.models import ImportantDateRecord
from tapme.reminders.default_templates import DEFAULT_TEMPLATES
from tapme.reminders.domain import (
    ReminderConfiguration,
    Scenario,
    ScenarioStep,
    template_for,
)
from tapme.reminders.models import ReminderRecord, ReminderScenario, ReminderStep
from tapme.shared.domain import Conflict, InvalidInput


def event_scenario(scenarios, label):
    normalized = label.strip().casefold()
    matching = [
        s for s in scenarios if normalized in {v.strip().casefold() for v in s.event_labels}
    ]
    candidates = matching or [s for s in scenarios if not s.event_labels]
    # A disabled explicit scenario suppresses the fallback, but must not hide
    # a replacement enabled scenario for the same event.
    return next((s for s in candidates if s.enabled), candidates[0] if candidates else None)


def initialize(settings, rules):
    """Caller holds the settings lock. Keep historical keys, state and message snapshots."""
    if settings.scenarios_initialized:
        return
    presets = [
        ("День рождения", "before_event", ["День рождения"], True, "date", rules.offsets),
        (
            "Годовщина и свадьба",
            "before_event",
            ["Годовщина", "Свадьба"],
            True,
            "date",
            rules.offsets,
        ),
        ("Другие важные даты", "before_event", [], True, "date", rules.offsets),
        ("Давно не заказывали", "after_last_order", [], True, "inactive", [rules.inactive_days]),
        ("Спасибо после доставки", "after_delivery", [], False, "", [1]),
        ("8 Марта", "holiday", [], False, "", [5]),
    ]
    for index, (name, kind, labels, enabled, legacy, offsets) in enumerate(presets):
        scenario = ReminderScenario.objects.create(
            business_id=settings.business_id,
            name=name,
            kind=kind,
            event_labels=labels,
            enabled=enabled,
            legacy_kind=legacy,
            sort=index,
        )
        for position, offset in enumerate(offsets):
            text = (
                template_for(f"{legacy}:migration:{offset}", rules)
                if legacy
                else (
                    DEFAULT_TEMPLATES["feedback"]
                    if kind == "after_delivery"
                    else "{имя}, здравствуйте! Скоро 8 Марта. Подобрать букет заранее? {магазин}"
                )
            )
            ReminderStep.objects.create(
                scenario=scenario,
                offset_days=offset,
                template=text,
                sort=position,
            )
    scenarios = list(
        ReminderScenario.objects.filter(business_id=settings.business_id).prefetch_related("steps")
    )
    dates = {
        str(e.id): e
        for e in ImportantDateRecord.objects.filter(customer__business_id=settings.business_id)
    }
    changed = []
    for row in ReminderRecord.objects.filter(business_id=settings.business_id).iterator():
        if row.key.startswith("date:"):
            parts = row.key.split(":")
            event = dates.get(parts[1])
            if not event or len(parts) != 4:
                continue
            scenario = event_scenario(
                [s for s in scenarios if s.kind == "before_event"], event.label
            )
            try:
                row.event_date = date(int(parts[2]), event.month, event.day)
            except ValueError:
                row.event_date = date(int(parts[2]), 2, 28)
            offset = int(parts[3])
            row.occurrence_key = ":".join(parts[:3])
        elif row.key.startswith("inactive:"):
            scenario = next(s for s in scenarios if s.legacy_kind == "inactive")
            offset = rules.inactive_days
            row.occurrence_key = row.key
        else:
            continue
        row.scenario = scenario
        row.step = next((s for s in scenario.steps.all() if s.offset_days == offset), None)
        if row.state in {"sent", "answered", "ordered"}:
            row.sent_at = row.acted_at or row.created_at
        changed.append(row)
    ReminderRecord.objects.bulk_update(
        changed, ["scenario", "step", "event_date", "occurrence_key", "sent_at"]
    )
    settings.scenarios_initialized = True
    settings.save(update_fields=["scenarios_initialized"])


def configuration(settings):
    return ReminderConfiguration(
        version=settings.version,
        enabled=settings.enabled,
        start_hour=settings.start_hour,
        end_hour=settings.end_hour,
        min_days_between=settings.min_days_between,
        scenarios=tuple(
            Scenario(
                id=s.id,
                name=s.name,
                kind=s.kind,
                enabled=s.enabled,
                event_labels=tuple(s.event_labels),
                holiday_month=s.holiday_month,
                holiday_day=s.holiday_day,
                audience=s.audience,
                daily_cap=s.daily_cap,
                steps=tuple(
                    ScenarioStep(
                        id=p.id, offset_days=p.offset_days, template=p.template, enabled=p.enabled
                    )
                    for p in s.steps.all()
                    if not p.archived
                ),
            )
            for s in ReminderScenario.objects.filter(
                business_id=settings.business_id, archived=False
            ).prefetch_related("steps")
        ),
    )


def save_configuration(settings, config):
    if settings.version != config.version:
        raise Conflict(
            "Настройки напоминаний уже изменены в другой вкладке. Загрузите актуальные настройки."
        )
    existing = {s.id: s for s in ReminderScenario.objects.filter(business_id=settings.business_id)}
    scenario_ids, step_ids = set(), set()
    for index, scenario in enumerate(config.scenarios):
        if scenario.id not in existing and ReminderScenario.objects.filter(id=scenario.id).exists():
            raise InvalidInput("Недопустимый идентификатор сценария.")
        row = existing.get(scenario.id)
        if row and row.archived:
            raise Conflict("Сценарий удалён. Загрузите актуальные настройки.")
        if row and row.kind != scenario.kind:
            raise InvalidInput("Для другого вида события создайте новый сценарий.")
        scenario_ids.add(scenario.id)
        row, _ = ReminderScenario.objects.update_or_create(
            business_id=settings.business_id,
            id=scenario.id,
            defaults=dict(
                name=scenario.name,
                kind=scenario.kind,
                enabled=scenario.enabled,
                event_labels=list(scenario.event_labels),
                holiday_month=scenario.holiday_month,
                holiday_day=scenario.holiday_day,
                audience=scenario.audience,
                daily_cap=scenario.daily_cap,
                sort=index,
            ),
        )
        for position, step in enumerate(scenario.steps):
            old = ReminderStep.objects.filter(id=step.id).first()
            if old and (old.scenario_id != row.id or old.archived):
                raise InvalidInput("Недопустимый идентификатор шага.")
            if len(step.template) > 500 and (not old or old.template != step.template):
                raise InvalidInput("Сократите новый текст шага до 500 символов.")
            step_ids.add(step.id)
            ReminderStep.objects.update_or_create(
                id=step.id,
                scenario=row,
                defaults=dict(
                    offset_days=step.offset_days,
                    template=step.template,
                    enabled=step.enabled,
                    sort=position,
                ),
            )
    ReminderScenario.objects.filter(business_id=settings.business_id).exclude(
        id__in=scenario_ids
    ).update(archived=True)
    ReminderStep.objects.filter(scenario__business_id=settings.business_id).exclude(
        id__in=step_ids
    ).update(archived=True)
    settings.version += 1
    settings.enabled, settings.start_hour, settings.end_hour = (
        config.enabled,
        config.start_hour,
        config.end_hour,
    )
    settings.min_days_between = config.min_days_between
    settings.save()
    return configuration(settings)


def sync_legacy(settings, previous, current):
    """The existing Templates screen remains compatible; unrelated template edits change no steps."""
    if not settings.scenarios_initialized:
        return
    for scenario in ReminderScenario.objects.filter(
        business_id=settings.business_id, archived=False
    ).exclude(legacy_kind=""):
        date_scenario = scenario.legacy_kind == "date"
        old_offsets = previous.offsets if date_scenario else (previous.inactive_days,)
        new_offsets = current.offsets if date_scenario else (current.inactive_days,)
        if old_offsets != new_offsets:
            scenario.steps.exclude(offset_days__in=new_offsets).update(archived=True)
            for index, offset in enumerate(new_offsets):
                if not scenario.steps.filter(offset_days=offset, archived=False).exists():
                    ReminderStep.objects.create(
                        scenario=scenario,
                        offset_days=offset,
                        sort=index,
                        template=template_for(
                            f"{scenario.legacy_kind}:migration:{offset}", current
                        ),
                    )
        for step in scenario.steps.filter(archived=False):
            key = f"{scenario.legacy_kind}:migration:{step.offset_days}"
            if template_for(key, previous) != template_for(key, current):
                step.template = template_for(key, current)
                step.save(update_fields=["template"])
