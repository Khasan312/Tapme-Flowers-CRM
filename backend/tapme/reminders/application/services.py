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
from tapme.reminders.domain import ReminderConfiguration, ReminderRules
from tapme.shared.domain import InvalidInput, page_bounds


class ReminderRepository(Protocol):
    def configuration(self, business_id: UUID) -> ReminderConfiguration: ...
    def save_configuration(
        self, business_id: UUID, config: ReminderConfiguration
    ) -> ReminderConfiguration: ...
    def rules(self, business_id: UUID) -> ReminderRules: ...
    def save_rules(self, business_id: UUID, rules: ReminderRules) -> ReminderRules: ...
    def generate(
        self, business_id: UUID, now: datetime, point_ids: tuple[UUID, ...] | None = None
    ) -> int: ...
    def list(
        self,
        scope: Scope,
        state: str,
        limit: int,
        offset: int,
        now: datetime,
        kind: str = "all",
        scenario: UUID | None = None,
    ) -> dict[str, object]: ...
    def prepare(self, scope: Scope, reminder_id: UUID, now: datetime) -> dict[str, str]: ...
    def act(
        self,
        scope: Scope,
        reminder_id: UUID,
        action: str,
        now: datetime,
        order_id: UUID | None = None,
    ) -> None: ...
    def open_message(self, scope: Scope, reminder_id: UUID, now: datetime) -> dict[str, str]: ...
    def edit_message(self, scope: Scope, reminder_id: UUID, text: str) -> None: ...


class ReminderService:
    def __init__(self, access: MembershipReader, repository: ReminderRepository):
        self.access, self.repository = access, repository

    def configuration(self, scope: Scope) -> ReminderConfiguration:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.configuration(scope.business_id)

    def save_configuration(
        self, scope: Scope, config: ReminderConfiguration
    ) -> ReminderConfiguration:
        authorize(self.access, scope, frozenset({Role.OWNER}))
        config.validate()
        return self.repository.save_configuration(scope.business_id, config)

    def open_message(self, scope: Scope, reminder_id: UUID, now: datetime) -> dict[str, str]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.open_message(scope, reminder_id, now)

    def edit_message(self, scope: Scope, reminder_id: UUID, text: str) -> None:
        authorize(self.access, scope, OFFICE_ROLES)
        if not text.strip() or len(text) > 2000:
            raise InvalidInput("Сообщение должно содержать от 1 до 2000 символов.")
        self.repository.edit_message(scope, reminder_id, text)

    def rules(self, scope: Scope) -> ReminderRules:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.rules(scope.business_id)

    def save_rules(self, scope: Scope, rules: ReminderRules) -> ReminderRules:
        authorize(self.access, scope, frozenset({Role.OWNER}))
        rules.validate()
        return self.repository.save_rules(scope.business_id, rules)

    def generate(self, scope: Scope, now: datetime) -> int:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.generate(scope.business_id, now, self.access.point_ids(scope))

    def list(
        self,
        scope: Scope,
        state: str,
        limit: int,
        offset: int,
        now: datetime,
        kind: str = "all",
        scenario: UUID | None = None,
    ) -> dict[str, object]:
        authorize(self.access, scope, OFFICE_ROLES)
        page_bounds(limit, offset)
        if state not in {"wait", "sent", "skipped", "answered", "ordered"}:
            raise InvalidInput("Неизвестное состояние напоминания.")
        return self.repository.list(scope, state, limit, offset, now, kind, scenario)

    def prepare(self, scope: Scope, reminder_id: UUID, now: datetime) -> dict[str, str]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.prepare(scope, reminder_id, now)

    def act(
        self,
        scope: Scope,
        reminder_id: UUID,
        action: str,
        now: datetime,
        order_id: UUID | None = None,
    ) -> None:
        authorize(self.access, scope, OFFICE_ROLES)
        if action not in {"sent", "skipped", "tomorrow", "answered", "ordered", "undo", "opt_out"}:
            raise InvalidInput("Неизвестное действие.")
        self.repository.act(scope, reminder_id, action, now, order_id)


class ReminderGeneration:
    """Trusted scheduler entrypoint; callers outside the scheduler use ReminderService."""

    def __init__(self, businesses: Callable[[], Iterable[UUID]], repository: ReminderRepository):
        self.businesses, self.repository = businesses, repository

    def run(self, now: datetime) -> int:
        return sum(self.repository.generate(business_id, now) for business_id in self.businesses())
