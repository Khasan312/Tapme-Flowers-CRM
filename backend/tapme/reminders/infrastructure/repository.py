from dataclasses import asdict, replace
from datetime import timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone

from tapme.businesses.models import Business
from tapme.customers.models import CustomerRecord
from tapme.feedback.models import FeedbackRecord
from tapme.reminders.default_templates import DEFAULT_TEMPLATES
from tapme.reminders.domain import (
    DEFAULT_TEMPLATE,
    ReminderRules,
    candidates_for_customer,
    ensure_action,
    ensure_eligible,
    event_group,
    reminder_due,
    render_template,
    template_for,
)
from tapme.reminders.models import ReminderRecord, ReminderSettings
from tapme.shared.domain import Conflict, NotFound


def paused_ids(business_id):
    return FeedbackRecord.objects.filter(
        business_id=business_id, kind="complaint", status="open"
    ).values_list("order__customer_id", flat=True)


class DjangoReminderRepository:
    def rules(self, business_id):
        row, _ = ReminderSettings.objects.get_or_create(business_id=business_id)
        return self._rules(row)

    def _rules(self, row):
        templates = dict(row.templates)
        if not templates:
            templates = dict(DEFAULT_TEMPLATES)
            if row.template != DEFAULT_TEMPLATE:
                templates.update({key: row.template for key in ("d14", "d7", "d3", "d1")})
            if row.inactive_template != ReminderRules().inactive_template:
                templates["lapsed"] = row.inactive_template
        return ReminderRules(
            row.enabled,
            tuple(row.offsets),
            row.inactive_days,
            row.start_hour,
            row.end_hour,
            row.template,
            row.inactive_template,
            templates,
            row.custom_templates,
            row.version,
        )

    def save_rules(self, business_id, rules):
        with transaction.atomic():
            ReminderSettings.objects.get_or_create(business_id=business_id)
            row = ReminderSettings.objects.select_for_update().get(business_id=business_id)
            if row.version != rules.version:
                raise Conflict(
                    "Настройки напоминаний или шаблоны уже изменены в другой вкладке. "
                    "Ваши изменения не сохранены. Загрузите актуальные настройки."
                )
            if row.enabled != rules.enabled:
                # An intentional pause must not be treated as a scheduler outage.
                row.last_generated_at = timezone.now()
            changed = replace(rules, version=row.version + 1)
            for key, value in asdict(changed).items():
                setattr(row, key, value)
            row.save()
            return changed

    @transaction.atomic
    def generate(self, business_id, now):
        ReminderSettings.objects.get_or_create(business_id=business_id)
        settings = ReminderSettings.objects.select_for_update().get(business_id=business_id)
        rules = self._rules(settings)
        business = Business.objects.get(id=business_id)
        zone = ZoneInfo(business.timezone)
        today = now.astimezone(zone).date()
        since = today - timedelta(days=max(rules.offsets))
        if settings.last_generated_at:
            since = max(since, settings.last_generated_at.astimezone(zone).date())
        count = 0
        if rules.enabled:
            customers = (
                CustomerRecord.objects.filter(business_id=business_id, consent=True)
                .exclude(id__in=paused_ids(business_id))
                .prefetch_related("dates")
                .annotate(last_order=Max("orderrecord__completed_at"))
            )
            suppressed = {
                event_group(key)
                for key in ReminderRecord.objects.filter(
                    business_id=business_id, state="skipped"
                ).values_list("key", flat=True)
            }
            for customer in customers.iterator(chunk_size=200):
                last = customer.last_order
                dates = list(customer.dates.all())
                candidates = candidates_for_customer(
                    str(customer.id),
                    customer.name,
                    [(str(e.id), e.label, e.person, e.month, e.day) for e in dates],
                    last.isoformat() if last else None,
                    last.astimezone(zone).date() if last else None,
                    today,
                    rules,
                    since,
                )
                due_days = {}
                for event in dates:
                    due = reminder_due(today, event.month, event.day, rules.offsets, since)
                    if due:
                        target, offset = due
                        due_days[f"date:{event.id}:{target.year}:{offset}"] = target - timedelta(
                            days=offset
                        )
                for key, event, person in candidates:
                    if event_group(key) in suppressed:
                        continue
                    due_date = due_days.get(key, today)
                    _, created = ReminderRecord.objects.get_or_create(
                        business_id=business_id,
                        key=key,
                        defaults=dict(
                            customer=customer,
                            event=event,
                            person=person,
                            due_date=due_date,
                            recovered=due_date < today,
                        ),
                    )
                    count += int(created)
        # The cursor advances only when the whole run commits successfully.
        settings.last_generated_at = max(now, settings.last_generated_at or now)
        settings.save(update_fields=["last_generated_at"])
        return count

    def list(self, business_id, state, limit, offset, now, kind="all"):
        today = now.astimezone(ZoneInfo(Business.objects.get(id=business_id).timezone)).date()
        all_rows = ReminderRecord.objects.filter(business_id=business_id)
        stats = {
            row["state"]: row["count"]
            for row in all_rows.values("state").annotate(count=Count("id"))
        }
        query = (
            all_rows.filter(state=state)
            .select_related("customer", "business")
            .order_by("due_date", "id")
        )
        if state == "wait":
            query = query.filter(due_date__lte=today)
        if kind != "all":
            query = query.filter(key__startswith="inactive:" if kind == "inactive" else "date:")
        paused = set(paused_ids(business_id))
        rules = self.rules(business_id)
        enabled = rules.enabled
        rows = [
            dict(
                id=r.id,
                kind="inactive" if r.key.startswith("inactive:") else "date",
                customer_id=r.customer_id,
                customer_name=r.customer.name,
                phone=r.customer.phone,
                event=r.event,
                person=r.person,
                due_date=r.due_date,
                state=r.state,
                message=r.message,
                preview=render_template(
                    template_for(r.key, rules, r.recovered),
                    dict(
                        name=r.customer.name, person=r.person, event=r.event, shop=r.business.name
                    ),
                ),
                recovered=r.recovered,
                paused=not enabled or not r.customer.consent or r.customer_id in paused,
            )
            for r in query[offset : offset + limit]
        ]
        return dict(count=query.count(), results=rows, stats=stats)

    def _eligible(self, row, now, require_hours=False):
        rules = self.rules(row.business_id)
        local = now.astimezone(ZoneInfo(row.business.timezone))
        ensure_eligible(
            rules,
            row.customer.consent,
            row.customer_id in set(paused_ids(row.business_id)),
            row.due_date,
            local.date(),
            local.hour,
            require_hours,
        )
        return rules

    def prepare(self, business_id, reminder_id, now):
        row = (
            ReminderRecord.objects.filter(business_id=business_id, id=reminder_id)
            .select_related("business", "customer")
            .first()
        )
        if row is None:
            raise NotFound("Напоминание не найдено.")
        if row.state != "wait":
            raise Conflict("Это напоминание уже обработано.")
        rules = self._eligible(row, now, require_hours=True)
        message = render_template(
            template_for(row.key, rules, row.recovered),
            dict(
                name=row.customer.name, person=row.person, event=row.event, shop=row.business.name
            ),
        )
        return dict(
            message=message,
            url="https://wa.me/" + row.customer.phone.lstrip("+") + "?text=" + quote(message),
        )

    def act(self, scope, reminder_id, action, now):
        with transaction.atomic():
            row = (
                ReminderRecord.objects.select_for_update(of=("self",))
                .filter(business_id=scope.business_id, id=reminder_id)
                .select_related("business", "customer")
                .first()
            )
            if row is None:
                raise NotFound("Напоминание не найдено.")
            ensure_action(row.state, action)
            if action in {"sent", "answered", "ordered"}:
                rules = self._eligible(row, now)
                if action == "sent":
                    row.message = render_template(
                        template_for(row.key, rules, row.recovered),
                        dict(
                            name=row.customer.name,
                            person=row.person,
                            event=row.event,
                            shop=row.business.name,
                        ),
                    )
            if action == "tomorrow":
                row.due_date = now.astimezone(ZoneInfo(row.business.timezone)).date() + timedelta(
                    days=1
                )
            else:
                row.state = action
            if action == "skipped" and row.key.startswith("date:"):
                ReminderRecord.objects.filter(
                    business_id=scope.business_id,
                    key__startswith=event_group(row.key) + ":",
                    state="wait",
                ).exclude(id=row.id).update(state="skipped", actor_id=scope.user_id, acted_at=now)
            row.actor_id, row.acted_at = scope.user_id, now
            row.save()
