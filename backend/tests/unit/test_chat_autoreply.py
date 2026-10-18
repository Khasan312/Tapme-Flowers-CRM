from datetime import UTC, datetime, timedelta

import pytest

from tapme.messaging.domain import automatic_reply


@pytest.mark.parametrize(
    "hour, start, end, expected",
    [
        (3, "09:00", "20:00", "Открыто Цветы"),
        (14, "09:00", "20:00", "Закрыто"),
        (18, "22:00", "06:00", "Открыто Цветы"),
        (6, "22:00", "06:00", "Закрыто"),
    ],
)
def test_hours_in_business_timezone_including_overnight(hour, start, end, expected):
    now = datetime(2026, 10, 18, hour, tzinfo=UTC)
    assert (
        automatic_reply(
            {
                "enabled": True,
                "start": start,
                "end": end,
                "open_text": "Открыто {магазин}",
                "closed_text": "Закрыто",
            },
            now=now,
            received_at=now,
            previous_inbound=None,
            last_reply=None,
            business_timezone="Asia/Bishkek",
            business_name="Цветы",
        )
        == expected
    )


@pytest.mark.parametrize(
    "incoming_age, previous_age, reply_age, enabled, expected",
    [
        (0, 24, 12, True, "Да"),
        (0, 23, 12, True, None),
        (0, 24, 11, True, None),
        (25, 50, 50, True, None),
        (0, 24, 12, False, None),
    ],
)
def test_reply_window_silence_cooldown_and_disabled(
    incoming_age, previous_age, reply_age, enabled, expected
):
    now = datetime(2026, 10, 18, 10, tzinfo=UTC)
    assert (
        automatic_reply(
            {"enabled": enabled, "open_text": "Да", "closed_text": "Да"},
            now=now,
            received_at=now - timedelta(hours=incoming_age),
            previous_inbound=now - timedelta(hours=previous_age),
            last_reply=now - timedelta(hours=reply_age),
            business_timezone="Asia/Bishkek",
            business_name="Цветы",
        )
        == expected
    )
