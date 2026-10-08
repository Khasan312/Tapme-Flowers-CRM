from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import uuid4

import pytest

from tapme.orders.application.overview import delivered_on_time
from tapme.payments.domain import Payment
from tapme.reminders.domain import (
    ReminderRules,
    candidates_for_customer,
    ensure_action,
    ensure_eligible,
    event_day,
    event_group,
    reminder_due,
    render_template,
    template_for,
)
from tapme.shared.domain import Conflict, InvalidInput


def test_anniversaries_year_boundary_and_leap_day():
    assert event_day(date(2026, 12, 30), 1, 3) == date(2027, 1, 3)
    assert event_day(date(2027, 2, 1), 2, 29) == date(2027, 2, 28)
    assert reminder_due(date(2026, 12, 27), 1, 3, (7, 3, 1)) == (date(2027, 1, 3), 7)
    assert reminder_due(date(2026, 12, 26), 1, 3, (7, 3, 1)) is None


@pytest.mark.parametrize(
    "template", ["{name.__class__}", "{name!r}", "{unknown}", "{name:100000000}", "{"]
)
def test_template_is_limited_to_plain_placeholders(template):
    with pytest.raises(InvalidInput):
        render_template(template, {"name": "Клиент"})


def test_inactive_cycle_and_independent_template():
    rules = ReminderRules()
    candidates = candidates_for_customer(
        "abc", "Имя", [], "2026-01-01T00:00:00Z", date(2026, 1, 1), date(2026, 9, 22), rules
    )
    assert len(candidates) == 1
    assert template_for(candidates[0][0], rules) == rules.inactive_template
    assert event_group("date:abc:2026:14") == event_group("date:abc:2026:7")
    assert event_group("date:abc:2027:14") != event_group("date:abc:2026:14")


def test_consent_pause_hours_and_state_transitions():
    today = date(2026, 9, 22)
    rules = ReminderRules()
    for consent, complaint, hour in [(False, False, 12), (True, True, 12), (True, False, 23)]:
        with pytest.raises(InvalidInput):
            ensure_eligible(rules, consent, complaint, today, today, hour, True)
    ensure_eligible(rules, True, False, today, today, 12, True)
    ensure_action("wait", "sent")
    with pytest.raises(Conflict):
        ensure_action("sent", "sent")


def test_payment_balance_rules_without_database():
    ids = [uuid4() for _ in range(5)]
    payment = Payment(
        ids[0],
        ids[1],
        ids[2],
        Decimal("100.00"),
        "payment",
        "cash",
        "",
        ids[3],
        datetime.now(UTC),
        ids[4],
        "hash",
    )
    payment.check_balance(Decimal("50"), Decimal("150"), False)
    with pytest.raises(InvalidInput):
        payment.check_balance(Decimal("51"), Decimal("150"), False)
    with pytest.raises(InvalidInput):
        payment.check_balance(Decimal("0"), Decimal("150"), True)


def test_delivery_deadline_uses_shop_timezone_and_includes_exact_end():
    day, end = date(2026, 9, 22), time(18)
    assert delivered_on_time(datetime(2026, 9, 22, 12, tzinfo=UTC), day, end, "Asia/Bishkek")
    assert not delivered_on_time(
        datetime(2026, 9, 22, 12, 0, 1, tzinfo=UTC), day, end, "Asia/Bishkek"
    )
    assert delivered_on_time(datetime(2026, 9, 22, 12, 0, 1, tzinfo=UTC), day, end, "UTC")


@pytest.mark.parametrize(
    "today,month,day,since,expected",
    [
        (date(2026, 12, 29), 1, 3, date(2026, 12, 25), (date(2027, 1, 3), 7)),
        (date(2027, 2, 23), 2, 29, date(2027, 2, 20), (date(2027, 2, 28), 7)),
        (date(2028, 2, 24), 2, 29, date(2028, 2, 20), (date(2028, 2, 29), 7)),
        (date(2026, 10, 14), 10, 13, date(2026, 10, 5), None),
        (date(2026, 10, 13), 10, 13, date(2026, 10, 1), (date(2026, 10, 13), 1)),
    ],
)
def test_recovery_calendar_boundaries(today, month, day, since, expected):
    assert reminder_due(today, month, day, (14, 7, 3, 1), since) == expected
