from dataclasses import dataclass, field
from datetime import date, timedelta
from string import Formatter

from tapme.shared.domain import InvalidInput

DEFAULT_TEMPLATE = "{name}, здравствуйте! Скоро {event} у {person}. Поможем выбрать букет? {shop}"


TEMPLATE_FIELDS = {
    "имя": "name",
    "магазин": "shop",
    "повод": "event",
    "получатель": "person",
    "номер": "number",
    "состав": "items",
    "дата": "date",
    "окно": "window",
    "адрес": "address",
    "сумма": "total",
    "ссылка": "link",
}
TEMPLATE_IDS = {"d14", "d7", "d3", "d1", "lapsed", "confirm", "ready", "done", "feedback", "sorry"}


def render_template(template: str, values: dict[str, str]) -> str:
    values = {**values, **{ru: values.get(en, "") for ru, en in TEMPLATE_FIELDS.items()}}

    try:
        for _, field, spec, conversion in Formatter().parse(template):
            if field is not None and (
                field not in set(TEMPLATE_FIELDS) | set(TEMPLATE_FIELDS.values())
                or spec
                or conversion
            ):
                raise ValueError
        return template.format_map(values)
    except (ValueError, KeyError):
        raise InvalidInput("Допустимые подстановки: {name}, {person}, {event}, {shop}.") from None


@dataclass(frozen=True)
class ReminderRules:
    enabled: bool = True
    offsets: tuple[int, ...] = (14, 7, 3, 1)
    inactive_days: int = 90
    start_hour: int = 9
    end_hour: int = 20
    template: str = DEFAULT_TEMPLATE
    inactive_template: str = (
        "{name}, здравствуйте! Давно не выбирали цветы у нас. Подобрать букет для вас? {shop}"
    )

    templates: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        for key, text in self.templates.items():
            if key not in TEMPLATE_IDS or not 1 <= len(text) <= 2000:
                raise InvalidInput("Проверьте название и длину шаблона.")
            render_template(text, {name: "Пример" for name in TEMPLATE_FIELDS.values()})

        if (
            not self.offsets
            or len(set(self.offsets)) != len(self.offsets)
            or any(n < 0 or n > 60 for n in self.offsets)
        ):
            raise InvalidInput("Укажите неповторяющиеся интервалы от 0 до 60 дней.")
        if not 30 <= self.inactive_days <= 730 or not 0 <= self.start_hour < self.end_hour <= 24:
            raise InvalidInput("Проверьте срок отсутствия покупок и часы сообщений.")
        if not 1 <= len(self.template) <= 2000:
            raise InvalidInput("Шаблон должен содержать от 1 до 2000 символов.")
        render_template(
            self.template, dict(name="Имя", person="Получатель", event="событие", shop="Магазин")
        )

        if not 1 <= len(self.inactive_template) <= 2000:
            raise InvalidInput("Проверьте длину шаблона для давних клиентов.")
        render_template(
            self.inactive_template,
            dict(name="Имя", person="Получатель", event="событие", shop="Магазин"),
        )


def event_day(today: date, month: int, day: int) -> date:
    # An anniversary on February 29 falls on February 28 in non-leap years.
    def in_year(year: int) -> date:
        try:
            return date(year, month, day)
        except ValueError:
            if (month, day) == (2, 29):
                return date(year, 2, 28)
            raise

    target = in_year(today.year)
    return in_year(today.year + 1) if target < today else target


def reminder_due(
    today: date, month: int, day: int, offsets: tuple[int, ...]
) -> tuple[date, int] | None:
    target = event_day(today, month, day)
    for offset in offsets:
        if today == target - timedelta(days=offset):
            return target, offset
    return None


def candidates_for_customer(
    customer_id: str,
    name: str,
    events: list[tuple[str, str, str, int, int]],
    last_order: str | None,
    last_order_day: date | None,
    today: date,
    rules: ReminderRules,
) -> list[tuple[str, str, str]]:
    candidates = []
    for event_id, label, person, month, day in events:
        due = reminder_due(today, month, day, rules.offsets)
        if due:
            target, offset = due
            candidates.append((f"date:{event_id}:{target.year}:{offset}", label, person))
    if last_order and last_order_day and (today - last_order_day).days >= rules.inactive_days:
        candidates.append((f"inactive:{customer_id}:{last_order}", "давно не выбирали цветы", name))
    return candidates


def ensure_eligible(
    rules: ReminderRules,
    consent: bool,
    complaint: bool,
    due_date: date,
    today: date,
    hour: int,
    require_hours: bool,
) -> None:
    if not rules.enabled or not consent or complaint:
        raise InvalidInput("Напоминание приостановлено: проверьте согласие, жалобы и настройки.")
    if due_date > today:
        raise InvalidInput("Это напоминание отложено на будущую дату.")
    if require_hours and not rules.start_hour <= hour < rules.end_hour:
        raise InvalidInput("Сейчас тихие часы. Откройте сообщение в разрешённое время.")


def ensure_action(state: str, action: str) -> None:
    from tapme.shared.domain import Conflict

    allowed = {
        "wait": {"sent", "skipped", "tomorrow"},
        "sent": {"answered", "ordered"},
        "answered": {"ordered"},
    }
    if action not in allowed.get(state, set()):
        raise Conflict("Напоминание уже изменено. Обновите список.")


def template_for(key: str, rules: ReminderRules) -> str:
    template_id = "lapsed" if key.startswith("inactive:") else "d" + key.rsplit(":", 1)[-1]
    return rules.templates.get(template_id) or (
        rules.inactive_template if key.startswith("inactive:") else rules.template
    )


def event_group(key: str) -> str:
    return key.rsplit(":", 1)[0] if key.startswith("date:") else key
