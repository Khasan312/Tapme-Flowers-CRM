from dataclasses import asdict, replace
from datetime import datetime, time, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.businesses.models import Business
from tapme.customers.models import CustomerRecord
from tapme.feedback.models import FeedbackRecord
from tapme.orders.models import OrderRecord
from tapme.reminders.default_templates import DEFAULT_TEMPLATES
from tapme.reminders.domain import (
    DEFAULT_TEMPLATE,
    ReminderRules,
    ensure_action,
    ensure_eligible,
    event_group,
    render_template,
    template_for,
)
from tapme.reminders.infrastructure import scenarios
from tapme.reminders.infrastructure.generation import generate_scenarios
from tapme.reminders.infrastructure.points import scoped_reminders
from tapme.reminders.models import ReminderRecord, ReminderSettings
from tapme.shared.domain import Conflict, InvalidInput, NotFound


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
            previous = self._rules(row)
            changed = replace(rules, version=row.version + 1)
            for key, value in asdict(changed).items():
                setattr(row, key, value)
            row.save()
            scenarios.sync_legacy(row, previous, changed)
            return changed

    @transaction.atomic
    def configuration(self, business_id):
        ReminderSettings.objects.get_or_create(business_id=business_id)
        row = ReminderSettings.objects.select_for_update().get(business_id=business_id)
        scenarios.initialize(row, self._rules(row))
        return scenarios.configuration(row)

    @transaction.atomic
    def save_configuration(self, business_id, config):
        ReminderSettings.objects.get_or_create(business_id=business_id)
        row = ReminderSettings.objects.select_for_update().get(business_id=business_id)
        scenarios.initialize(row, self._rules(row))
        if row.enabled != config.enabled:
            row.last_generated_at = timezone.now()
        return scenarios.save_configuration(row, config)

    @transaction.atomic
    def generate(self, business_id, now, point_ids=None):
        ReminderSettings.objects.get_or_create(business_id=business_id)
        settings = ReminderSettings.objects.select_for_update().get(business_id=business_id)
        scenarios.initialize(settings, self._rules(settings))
        count = generate_scenarios(settings, Business.objects.get(id=business_id), now, point_ids)
        settings.last_generated_at = max(now, settings.last_generated_at or now)
        settings.save(update_fields=["last_generated_at"])
        return count

    def _text(self, row, rules, last_bouquet=""):
        if row.message:
            return row.message
        text = row.step.template if row.step else template_for(row.key, rules, row.recovered)
        if row.recovered and row.key.startswith("date:"):
            text = DEFAULT_TEMPLATE
        return render_template(
            text,
            dict(
                name=row.customer.name,
                person=row.person,
                event=row.event,
                shop=row.business.name,
                date=row.event_date.strftime("%d.%m.%Y") if row.event_date else "",
                last_bouquet=last_bouquet,
            ),
        )

    def _history(self, row, scope):
        orders = (
            OrderRecord.objects.filter(
                business_id=row.business_id,
                customer_id=row.customer_id,
                point_id__in=DjangoMembershipReader().point_ids(scope),
            )
            .exclude(status="cancelled")
            .prefetch_related("lines")
            .order_by("-created_at", "-id")
        )
        last = orders.first()
        hint = None
        if row.event_date:
            target = row.event_date
            try:
                anniversary = target.replace(year=target.year - 1)
            except ValueError:
                anniversary = target.replace(year=target.year - 1, day=28)
            match = Q(occasion__iexact=row.event)
            if row.person:
                match |= Q(recipient_name__iexact=row.person)
            hint = orders.filter(
                match,
                status="done",
                delivery_date__range=(
                    anniversary - timedelta(days=10),
                    anniversary + timedelta(days=10),
                ),
            ).first()

        def payload(order):
            return (
                dict(
                    id=order.id,
                    number=order.number,
                    date=order.delivery_date,
                    total=str(order.total),
                    items=", ".join(line.name for line in order.lines.all()),
                )
                if order
                else None
            )

        return payload(last), payload(hint)

    def list(self, scope, state, limit, offset, now, kind="all", scenario=None):
        business_id = scope.business_id
        config = self.configuration(business_id)
        business = Business.objects.get(id=business_id)
        zone = ZoneInfo(business.timezone)
        local = now.astimezone(zone)
        today = local.date()
        all_rows = scoped_reminders(scope)
        visible = all_rows.exclude(state="wait", due_date__gt=today)
        stats = {
            row["state"]: row["count"]
            for row in visible.values("state").annotate(count=Count("id"))
        }
        query = (
            visible.filter(state=state)
            .select_related("customer", "business", "scenario", "step", "point")
            .order_by("event_date", "customer__name", "id")
        )
        if kind != "all":
            query = query.filter(key__startswith="inactive:" if kind == "inactive" else "date:")
        if scenario:
            query = query.filter(scenario_id=scenario)
        paused = set(paused_ids(business_id))
        rules = self.rules(business_id)
        rows = []
        for row in query[offset : offset + limit]:
            reason = self._pause_reason(row, config, paused, now)
            last, hint = self._history(row, scope)
            rows.append(
                dict(
                    id=row.id,
                    point_id=row.point_id,
                    point_name=row.point.short_name if row.point else "Основная",
                    kind=row.scenario.kind
                    if row.scenario
                    else (
                        "after_last_order" if row.key.startswith("inactive:") else "before_event"
                    ),
                    customer_id=row.customer_id,
                    customer_name=row.customer.name,
                    phone=row.customer.phone,
                    event=row.event,
                    person=row.person,
                    due_date=row.due_date,
                    event_date=row.event_date,
                    state=row.state,
                    message=row.message,
                    preview=self._text(row, rules, hint["items"] if hint else ""),
                    recovered=row.recovered,
                    paused=bool(reason),
                    pause_reason=reason,
                    scenario_id=row.scenario_id,
                    scenario_name=row.scenario.name if row.scenario else row.event,
                    sent_at=row.sent_at,
                    order_id=row.order_id,
                    last_order=last,
                    last_year_hint=hint,
                )
            )
        start = datetime.combine(today, time.min, zone)
        sent_today = all_rows.filter(
            sent_at__gte=start, sent_at__lt=start + timedelta(days=1)
        ).count()
        week = start - timedelta(days=today.weekday())
        ordered = all_rows.filter(state="ordered", acted_at__gte=week, order__isnull=False).exclude(
            order__status="cancelled"
        )
        order_ids = ordered.values_list("order_id", flat=True).distinct()
        revenue = sum(
            OrderRecord.objects.filter(
                business_id=business_id,
                id__in=order_ids,
                point_id__in=DjangoMembershipReader().point_ids(scope),
            ).values_list("total", flat=True)
        )
        return dict(
            count=query.count(),
            results=rows,
            stats=stats,
            summary=dict(
                sent_today=sent_today,
                total_today=sent_today + stats.get("wait", 0),
                ordered_week=len(set(order_ids)),
                revenue_week=str(revenue),
            ),
            scenarios=[dict(id=s.id, name=s.name) for s in config.scenarios],
            rules=dict(
                enabled=config.enabled,
                start_hour=config.start_hour,
                end_hour=config.end_hour,
                min_days_between=config.min_days_between,
            ),
        )

    def _pause_reason(self, row, config, complaints, now):
        local = now.astimezone(ZoneInfo(row.business.timezone))
        if not row.customer.consent:
            return "У клиента нет согласия на сообщения"
        if row.customer_id in complaints:
            return "У клиента открыта жалоба"
        if not config.enabled:
            return "Напоминания выключены в настройках"
        if row.scenario and (row.scenario.archived or not row.scenario.enabled):
            return "Сценарий выключен"
        if row.step and (row.step.archived or not row.step.enabled):
            return "Этот шаг сценария выключен"
        if (
            row.event_date
            and row.event_date < local.date()
            and (not row.scenario or row.scenario.kind in {"before_event", "holiday"})
        ):
            return "Дата события уже прошла"
        if not config.start_hour <= local.hour < config.end_hour:
            return f"Можно писать с {config.start_hour:02}:00 до {config.end_hour:02}:00"
        if (
            config.min_days_between
            and ReminderRecord.objects.filter(
                business_id=row.business_id,
                customer_id=row.customer_id,
                sent_at__gt=now - timedelta(days=config.min_days_between),
            )
            .exclude(id=row.id)
            .exists()
        ):
            return f"Не чаще одного сообщения в {config.min_days_between} дн."
        return ""

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
        if require_hours:
            config = scenarios.configuration(
                ReminderSettings.objects.get(business_id=row.business_id)
            )
            reason = self._pause_reason(row, config, set(paused_ids(row.business_id)), now)
            if reason:
                raise InvalidInput(reason)
        return rules

    def _row(self, scope, reminder_id, lock=False):
        query = (
            scoped_reminders(scope)
            .filter(id=reminder_id)
            .select_related("business", "customer", "scenario", "step")
        )
        if lock:
            query = query.select_for_update(of=("self",))
        row = query.first()
        if row is None:
            raise NotFound("Напоминание не найдено.")
        return row

    def prepare(self, scope, reminder_id, now):
        row = self._row(scope, reminder_id)
        if row.state != "wait":
            raise Conflict("Это напоминание уже обработано.")
        rules = self._eligible(row, now, require_hours=True)
        _, hint = self._history(row, scope)
        message = self._text(row, rules, hint["items"] if hint else "")
        return dict(
            message=message,
            url="https://wa.me/" + row.customer.phone.lstrip("+") + "?text=" + quote(message),
        )

    @transaction.atomic
    def open_message(self, scope, reminder_id, now):
        row = self._row(scope, reminder_id, lock=True)
        # Serialize two reminders for one customer, including the frequency check.
        row.customer = CustomerRecord.objects.select_for_update().get(
            id=row.customer_id, business_id=scope.business_id
        )
        if row.state != "wait":
            raise Conflict("Это напоминание уже обработано. Обновите список.")
        rules = self._eligible(row, now, require_hours=True)
        _, hint = self._history(row, scope)
        row.message = self._text(row, rules, hint["items"] if hint else "")
        row.state, row.sent_at, row.acted_at, row.actor_id = "sent", now, now, scope.user_id
        row.save()
        return dict(
            message=row.message,
            url="https://wa.me/" + row.customer.phone.lstrip("+") + "?text=" + quote(row.message),
        )

    @transaction.atomic
    def edit_message(self, scope, reminder_id, text):
        row = self._row(scope, reminder_id, lock=True)
        if row.state != "wait":
            raise Conflict("Нельзя изменить уже обработанное сообщение.")
        row.message = text
        row.save(update_fields=["message"])

    @transaction.atomic
    def act(self, scope, reminder_id, action, now, order_id=None):
        row = self._row(scope, reminder_id, lock=True)
        if action == "undo":
            if (
                row.state != "sent"
                or row.actor_id != scope.user_id
                or not row.sent_at
                or now - row.sent_at > timedelta(seconds=10)
            ):
                raise Conflict("Отметку уже нельзя отменить. Обновите список.")
            row.state, row.sent_at, row.acted_at, row.actor_id = "wait", None, None, None
            row.save()
            return
        if action == "opt_out":
            customer = CustomerRecord.objects.select_for_update().get(
                id=row.customer_id, business_id=scope.business_id
            )
            customer.consent = False
            customer.version += 1
            customer.save(update_fields=["consent", "version"])
            row.opt_out_at, row.actor_id, row.acted_at = now, scope.user_id, now
            row.save()
            return
        ensure_action(row.state, action)
        if action in {"sent", "answered", "ordered"}:
            rules = self._eligible(row, now)
            if action == "sent":
                row.customer = CustomerRecord.objects.select_for_update().get(
                    id=row.customer_id, business_id=scope.business_id
                )
                rules = self._eligible(row, now, require_hours=True)
                _, hint = self._history(row, scope)
                row.message = self._text(row, rules, hint["items"] if hint else "")
                row.sent_at = now
            if action == "ordered" and order_id:
                order = (
                    OrderRecord.objects.filter(
                        id=order_id,
                        business_id=scope.business_id,
                        customer_id=row.customer_id,
                        point_id__in=DjangoMembershipReader().point_ids(scope),
                        created_at__gte=row.sent_at or row.created_at,
                    )
                    .exclude(status="cancelled")
                    .first()
                )
                if order is None:
                    raise InvalidInput("Выберите заказ этого клиента, созданный после сообщения.")
                row.order = order
        if action == "tomorrow":
            row.due_date = now.astimezone(ZoneInfo(row.business.timezone)).date() + timedelta(
                days=1
            )
        else:
            row.state = action
        if action == "skipped":
            related = ReminderRecord.objects.filter(business_id=scope.business_id, state="wait")
            if row.occurrence_key:
                related = related.filter(occurrence_key=row.occurrence_key)
            elif row.key.startswith("date:"):
                related = related.filter(key__startswith=event_group(row.key) + ":")
            else:
                related = related.filter(id=row.id)
            related.exclude(id=row.id).update(state="skipped", actor_id=scope.user_id, acted_at=now)
        row.actor_id, row.acted_at = scope.user_id, now
        row.save()
