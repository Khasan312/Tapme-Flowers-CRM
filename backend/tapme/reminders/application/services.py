from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from tapme.businesses.application.contracts import (
    OFFICE_ROLES,
    MembershipReader,
    Role,
    Scope,
    authorize,
)
from tapme.reminders.domain import ReminderRules
from tapme.shared.domain import InvalidInput, page_bounds


class ReminderRepository(Protocol):
    def rules(self, business_id: UUID) -> ReminderRules: ...
    def save_rules(self, business_id: UUID, rules: ReminderRules) -> ReminderRules: ...
    def generate(self, business_id: UUID, now: datetime) -> int: ...
    def list(
        self,
        business_id: UUID,
        state: str,
        limit: int,
        offset: int,
        now: datetime,
        kind: str = "all",
    ) -> dict[str, object]: ...
    def prepare(self, business_id: UUID, reminder_id: UUID, now: datetime) -> dict[str, str]: ...
    def act(self, scope: Scope, reminder_id: UUID, action: str, now: datetime) -> None: ...


class ReminderService:
    def __init__(self, access: MembershipReader, repository: ReminderRepository):
        self.access, self.repository = access, repository

    def rules(self, scope: Scope) -> ReminderRules:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.rules(scope.business_id)

    def save_rules(self, scope: Scope, rules: ReminderRules) -> ReminderRules:
        authorize(self.access, scope, frozenset({Role.OWNER}))
        rules.validate()
        return self.repository.save_rules(scope.business_id, rules)

    def generate(self, scope: Scope, now: datetime) -> int:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.generate(scope.business_id, now)

    def list(
        self, scope: Scope, state: str, limit: int, offset: int, now: datetime, kind: str = "all"
    ) -> dict[str, object]:
        authorize(self.access, scope, OFFICE_ROLES)
        page_bounds(limit, offset)
        if state not in {"wait", "sent", "skipped", "answered", "ordered"}:
            raise InvalidInput("Неизвестное состояние напоминания.")
        return self.repository.list(scope.business_id, state, limit, offset, now, kind)

    def prepare(self, scope: Scope, reminder_id: UUID, now: datetime) -> dict[str, str]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.prepare(scope.business_id, reminder_id, now)

    def act(self, scope: Scope, reminder_id: UUID, action: str, now: datetime) -> None:
        authorize(self.access, scope, OFFICE_ROLES)
        if action not in {"sent", "skipped", "tomorrow", "answered", "ordered"}:
            raise InvalidInput("Неизвестное действие.")
        self.repository.act(scope, reminder_id, action, now)


class ReminderGeneration:
    """Trusted scheduler entrypoint; callers outside the scheduler use ReminderService."""

    def __init__(self, businesses: Callable[[], Iterable[UUID]], repository: ReminderRepository):
        self.businesses, self.repository = businesses, repository

    def run(self, now: datetime) -> int:
        return sum(self.repository.generate(business_id, now) for business_id in self.businesses())
