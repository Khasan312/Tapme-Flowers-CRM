from datetime import date, datetime, time
from decimal import Decimal
from typing import Protocol

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize


class OverviewReader(Protocol):
    def overview(self, scope: Scope, day: date | None) -> dict[str, int | Decimal]: ...


class OverviewService:
    def __init__(self, access: MembershipReader, reads: OverviewReader):
        self.access, self.reads = access, reads

    def get(self, scope: Scope, day: date | None = None) -> dict[str, int | Decimal]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.reads.overview(scope, day)


def delivered_on_time(
    completed_at: datetime, delivery_date: date, window_end: time, timezone_name: str
) -> bool:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return completed_at <= datetime.combine(delivery_date, window_end, ZoneInfo(timezone_name))
