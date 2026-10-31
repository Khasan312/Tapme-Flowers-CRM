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


def local(value):
    return datetime.fromisoformat(value + "+06:00") if value else None


@pytest.mark.parametrize(
    "now, previous, last_reply, start, end, expected",
    [
        # Existing conversation, enabled after the client's earlier message.
        ("2026-10-29T01:27", "2026-10-28T22:32", None, "09:00", "20:00", "Закрыто"),
        # A recent daytime greeting does not suppress the after-hours notice.
        ("2026-10-28T20:00", "2026-10-28T19:50", "2026-10-28T19:50", "09:00", "20:00", "Закрыто"),
        ("2026-10-28T20:01", "2026-10-28T20:00", "2026-10-28T20:00", "09:00", "20:00", None),
        # Midnight and even 12 hours do not reset the current closure.
        ("2026-10-29T00:01", "2026-10-28T23:59", "2026-10-28T20:00", "09:00", "20:00", None),
        ("2026-10-29T08:59", "2026-10-28T20:00", "2026-10-28T20:00", "09:00", "20:00", None),
        # The following closure is eligible even without 24 hours of silence.
        ("2026-10-29T20:01", "2026-10-29T08:59", "2026-10-28T20:00", "09:00", "20:00", "Закрыто"),
        # At reopening the ordinary daytime cooldown still applies.
        ("2026-10-29T09:00", "2026-10-29T08:59", "2026-10-28T20:00", "09:00", "20:00", None),
        # Shops working overnight close in the morning.
        ("2026-10-29T06:00", "2026-10-29T05:50", "2026-10-29T05:50", "22:00", "06:00", "Закрыто"),
        ("2026-10-29T21:59", "2026-10-29T06:00", "2026-10-29T06:00", "22:00", "06:00", None),
        ("2026-10-30T06:00", "2026-10-29T21:59", "2026-10-29T06:00", "22:00", "06:00", "Закрыто"),
        # Calendar boundaries are still one continuous closure.
        ("2027-01-01T01:00", "2026-12-31T21:00", "2026-12-31T21:00", "09:00", "20:00", None),
    ],
)
def test_once_per_closure(now, previous, last_reply, start, end, expected):
    assert (
        automatic_reply(
            {
                "enabled": True,
                "start": start,
                "end": end,
                "open_text": "Открыто",
                "closed_text": "Закрыто",
            },
            now=local(now),
            received_at=local(now),
            previous_inbound=local(previous),
            last_reply=local(last_reply),
            business_timezone="Asia/Bishkek",
            business_name="Цветы",
        )
        == expected
    )


@pytest.mark.parametrize(
    "received, previous, enabled, text",
    [
        ("2026-10-28T19:59", "2026-10-28T19:50", True, "Закрыто"),
        ("2026-10-28T20:01", "2026-10-28T20:02", True, "Закрыто"),
        ("2026-10-27T20:00", None, True, "Закрыто"),
        ("2026-10-28T20:05", None, False, "Закрыто"),
        ("2026-10-28T20:05", None, True, "  "),
    ],
)
def test_closed_reply_ignores_stale_webhooks_disabled_and_empty_text(
    received, previous, enabled, text
):
    assert (
        automatic_reply(
            {"enabled": enabled, "start": "09:00", "end": "20:00", "closed_text": text},
            now=local("2026-10-28T20:05"),
            received_at=local(received),
            previous_inbound=local(previous),
            last_reply=None,
            business_timezone="Asia/Bishkek",
            business_name="Цветы",
        )
        is None
    )


@pytest.mark.parametrize(
    "now, last_reply, expected",
    [
        ("2026-11-01T01:45:00-05:00", "2026-11-01T01:45:00-04:00", None),
        ("2026-03-08T03:05:00-04:00", None, "Закрыто"),
    ],
)
def test_closed_reply_uses_business_wall_time_across_dst(now, last_reply, expected):
    when = datetime.fromisoformat(now)
    assert (
        automatic_reply(
            {
                "enabled": True,
                "start": "09:00",
                "end": "01:30" if last_reply else "02:30",
                "closed_text": "Закрыто",
            },
            now=when,
            received_at=when,
            previous_inbound=when - timedelta(minutes=5),
            last_reply=datetime.fromisoformat(last_reply) if last_reply else None,
            business_timezone="America/New_York",
            business_name="Цветы",
        )
        == expected
    )
