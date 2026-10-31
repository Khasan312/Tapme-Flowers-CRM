from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import OuterRef, Prefetch, Subquery

from tapme.businesses.models import Shop
from tapme.customers.models import CustomerRecord
from tapme.feedback.models import FeedbackRecord
from tapme.orders.models import OrderRecord
from tapme.reminders.domain import event_day, reminder_due
from tapme.reminders.infrastructure.scenarios import event_scenario
from tapme.reminders.models import ReminderRecord, ReminderScenario


def generate_scenarios(settings, business, now, point_ids=None):
    """Generate under the settings lock; only the latest missed step is recovered."""
    if not settings.enabled:
        return 0
    zone = ZoneInfo(business.timezone)
    today = now.astimezone(zone).date()
    primary_id = (
        Shop.objects.filter(business=business, is_primary=True).values_list("id", flat=True).first()
    )
    latest_point = (
        OrderRecord.objects.filter(business=business, customer_id=OuterRef("pk"))
        .exclude(status="cancelled")
        .order_by("-created_at", "-id")
        .values("point_id")[:1]
    )
    scenarios = list(
        ReminderScenario.objects.filter(business=business, archived=False).prefetch_related("steps")
    )
    suppressed = set(
        ReminderRecord.objects.filter(business=business, state="skipped").values_list(
            "occurrence_key", flat=True
        )
    )
    complaints = FeedbackRecord.objects.filter(
        business=business, kind="complaint", status="open"
    ).values_list("order__customer_id", flat=True)
    completed = (
        OrderRecord.objects.filter(business=business, completed_at__isnull=False)
        .exclude(status="cancelled")
        .order_by("-completed_at", "-id")
    )
    customers = (
        CustomerRecord.objects.filter(business=business, consent=True)
        .annotate(reminder_point_id=Subquery(latest_point))
        .exclude(id__in=complaints)
        .order_by("id")
        .prefetch_related(
            "dates", Prefetch("orderrecord_set", queryset=completed, to_attr="completed_orders")
        )
    )
    created_today = {
        s.id: ReminderRecord.objects.filter(
            business=business,
            scenario=s,
            created_at__gte=datetime.combine(today, time.min, zone),
            created_at__lt=datetime.combine(today + timedelta(days=1), time.min, zone),
        ).count()
        for s in scenarios
        if s.kind == "holiday"
    }
    count = 0

    def add(
        customer,
        scenario,
        step,
        occurrence,
        due,
        target,
        event,
        person,
        legacy_key=None,
        point_id=None,
    ):
        nonlocal count
        if occurrence in suppressed:
            return
        key = legacy_key or f"scenario:{scenario.id}:{step.id}:{customer.id}:{occurrence}"
        # Stable step IDs prevent duplicates after editing an interval. Old records
        # retain their original keys and are recognised by their migrated relation.
        if ReminderRecord.objects.filter(
            business=business, customer=customer, step=step, occurrence_key=occurrence
        ).exists():
            return
        if scenario.kind == "holiday" and created_today[scenario.id] >= scenario.daily_cap:
            return
        _, created = ReminderRecord.objects.get_or_create(
            business=business,
            key=key,
            defaults=dict(
                point_id=point_id or customer.reminder_point_id or primary_id,
                customer=customer,
                scenario=scenario,
                step=step,
                occurrence_key=occurrence,
                event=event,
                person=person,
                due_date=due,
                event_date=target,
                recovered=due < today,
                created_at=now,
            ),
        )
        assigned_point = point_id or customer.reminder_point_id or primary_id
        count += int(created and (point_ids is None or assigned_point in point_ids))
        if scenario.kind == "holiday":
            created_today[scenario.id] += int(created)

    for customer in customers.iterator(chunk_size=200):
        last = customer.completed_orders[0] if customer.completed_orders else None
        for scenario in scenarios:
            steps = [s for s in scenario.steps.all() if s.enabled and not s.archived]
            if not scenario.enabled or not steps:
                continue
            offsets = tuple(s.offset_days for s in steps)
            since = today - timedelta(days=max(offsets))
            if settings.last_generated_at:
                since = max(since, settings.last_generated_at.astimezone(zone).date())
            if scenario.kind == "before_event":
                for event in customer.dates.all():
                    selected = event_scenario(
                        [s for s in scenarios if s.kind == "before_event"], event.label
                    )
                    if selected is None or selected.id != scenario.id:
                        continue
                    due = reminder_due(today, event.month, event.day, offsets, since)
                    if due:
                        target, offset = due
                        step = next(s for s in steps if s.offset_days == offset)
                        occurrence = f"date:{event.id}:{target.year}"
                        legacy_key = (
                            f"{occurrence}:{offset}" if scenario.legacy_kind == "date" else None
                        )
                        add(
                            customer,
                            scenario,
                            step,
                            occurrence,
                            target - timedelta(days=offset),
                            target,
                            event.label,
                            event.person,
                            legacy_key,
                        )
            elif scenario.kind == "after_last_order" and last:
                last_day = last.completed_at.astimezone(zone).date()
                eligible = [s for s in steps if last_day + timedelta(days=s.offset_days) <= today]
                # A new unfinished order means the customer has already returned.
                if (
                    not eligible
                    or OrderRecord.objects.filter(
                        customer=customer,
                        business=business,
                        status__in=["new", "work", "ready", "route"],
                    ).exists()
                ):
                    continue
                step = max(eligible, key=lambda s: s.offset_days)
                occurrence = f"inactive:{customer.id}:{last.completed_at.isoformat()}"
                legacy_key = (
                    occurrence if scenario.legacy_kind == "inactive" and len(steps) == 1 else None
                )
                add(
                    customer,
                    scenario,
                    step,
                    occurrence,
                    today,
                    None,
                    "давно не выбирали цветы",
                    customer.name,
                    legacy_key,
                )
            elif scenario.kind == "after_delivery":
                for order in customer.completed_orders:
                    delivered = order.completed_at.astimezone(zone).date()
                    eligible = [
                        s
                        for s in steps
                        if since <= delivered + timedelta(days=s.offset_days) <= today
                    ]
                    if eligible:
                        step = max(eligible, key=lambda s: s.offset_days)
                        due = delivered + timedelta(days=step.offset_days)
                        add(
                            customer,
                            scenario,
                            step,
                            f"delivery:{order.id}",
                            due,
                            delivered,
                            scenario.name,
                            order.recipient_name,
                            point_id=order.point_id,
                        )
            elif scenario.kind == "holiday":
                target = event_day(today, scenario.holiday_month, scenario.holiday_day)
                eligible = [s for s in steps if target - timedelta(days=s.offset_days) <= today]
                if not eligible or (
                    scenario.audience == "ordered_last_year"
                    and (
                        not last
                        or last.completed_at.astimezone(zone).date() < today - timedelta(days=365)
                    )
                ):
                    continue
                step = min(eligible, key=lambda s: s.offset_days)
                add(
                    customer,
                    scenario,
                    step,
                    f"holiday:{scenario.id}:{customer.id}:{target.year}",
                    today,
                    target,
                    scenario.name,
                    customer.name,
                )
    return count
