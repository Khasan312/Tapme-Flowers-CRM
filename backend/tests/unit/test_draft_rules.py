from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from tapme.orders.application.draft_rules import normalize_fields, payment_deadline
from tapme.shared.domain import InvalidInput


@pytest.mark.parametrize(
    "fields",
    [
        {"fulfillment": []},
        {"date": 123},
        {"window": {"start": [], "end": ""}},
        {"items": [{"kind": "budget", "amount": "NaN", "description": ""}]},
        {"items": [{"kind": "budget", "amount": "0", "description": ""}]},
        {"window": {"start": "12:00", "end": "10:00"}},
    ],
)
def test_malformed_drafts_are_rejected(fields):
    with pytest.raises(InvalidInput):
        normalize_fields(fields)


def test_payment_deadline_timezone_and_assembly_boundary():
    now = datetime(2026, 10, 18, 16, 0, tzinfo=UTC)  # 22:00 in Bishkek.
    receiving = datetime(2026, 10, 19, 1, 30, tzinfo=ZoneInfo("Asia/Bishkek"))
    assert payment_deadline(now, receiving) == now + timedelta(hours=1)
    receiving = now + timedelta(hours=2, minutes=15)
    assert payment_deadline(now, receiving) == now + timedelta(minutes=15)
    with pytest.raises(InvalidInput):
        payment_deadline(now, now + timedelta(hours=1))
    assert payment_deadline(
        now, now + timedelta(hours=1), now + timedelta(minutes=30)
    ) == now + timedelta(minutes=30)
    for invalid in [
        now,
        now - timedelta(minutes=1),
        now + timedelta(hours=1),
        now.replace(tzinfo=None),
    ]:
        with pytest.raises(InvalidInput):
            payment_deadline(now, now + timedelta(hours=1), invalid)
