from datetime import datetime, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from tapme.shared.domain import InvalidInput


class DeliveryRejected(Exception):
    """Provider explicitly rejected the request; a deliberate retry is safe."""


class DeliveryUnknown(Exception):
    """The provider may have accepted it. Never retry automatically."""


class MessagingGateway(Protocol):
    def inspect(self, phone_id: str, token: str) -> dict[str, Any]: ...
    def send(self, phone_id: str, token: str, payload: dict[str, Any]) -> str: ...
    def upload(self, phone_id: str, token: str, content: bytes, mime: str) -> str: ...
    def download(self, phone_id: str, token: str, media_id: str) -> tuple[bytes, str]: ...
    def register(self, phone_id: str, token: str, pin: str) -> None: ...
    def subscribe(self, waba_id: str, token: str) -> None: ...
    def verify_account(self, phone_id: str, waba_id: str, token: str) -> None: ...
    def mark_read(self, phone_id: str, token: str, external_id: str) -> None: ...


class AttachmentStorage(Protocol):
    def save(self, key: str, content: bytes, mime: str) -> tuple[str, str]: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


def reply_allowed(last_inbound: datetime | None, now: datetime) -> bool:
    return last_inbound is not None and now < last_inbound + timedelta(hours=24)


def message_text(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 4096:
        raise InvalidInput("Введите сообщение до 4096 символов.")
    return value


def automatic_reply(
    policy: dict[str, Any],
    *,
    now: datetime,
    received_at: datetime,
    previous_inbound: datetime | None,
    last_reply: datetime | None,
    business_timezone: str,
    business_name: str,
) -> str | None:
    if not policy.get("enabled") or not reply_allowed(received_at, now):
        return None
    local = now.astimezone(ZoneInfo(business_timezone))
    clock = local.strftime("%H:%M")
    start, end = policy.get("start", "09:00"), policy.get("end", "20:00")
    opened = start <= clock < end if start < end else clock >= start or clock < end
    if opened:
        if previous_inbound and received_at - previous_inbound < timedelta(hours=24):
            return None
        if last_reply and received_at - last_reply < timedelta(hours=12):
            return None
    else:
        # One greeting per closure, including the part after midnight. A daytime
        # greeting must not suppress the first after-hours reply that evening.
        hour, minute = map(int, end.split(":"))
        closed_since = local.replace(hour=hour, minute=minute, second=0, microsecond=0, fold=0)
        if clock < end:
            closed_since -= timedelta(days=1)
        if previous_inbound and received_at < previous_inbound:
            return None
        # Delayed webhooks from before this closure do not start a new greeting.
        if received_at.astimezone(local.tzinfo) < closed_since:
            return None
        if last_reply and last_reply.astimezone(local.tzinfo) >= closed_since:
            return None
    text = str(policy.get("open_text" if opened else "closed_text", ""))
    return text.replace("{магазин}", business_name).strip()[:4096] or None
