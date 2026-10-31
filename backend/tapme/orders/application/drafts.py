from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize
from tapme.orders.application.draft_rules import normalize_fields
from tapme.orders.domain import Order


class DraftRepository(Protocol):
    def extract(
        self, scope: Scope, chat_id: UUID, draft_id: UUID, version: int
    ) -> dict[str, Any]: ...
    def abandon(
        self, scope: Scope, chat_id: UUID, draft_id: UUID, version: int
    ) -> dict[str, Any]: ...
    def read(self, scope: Scope, chat_id: UUID) -> dict[str, Any]: ...
    def start(self, scope: Scope, chat_id: UUID) -> dict[str, Any]: ...
    def save(
        self,
        scope: Scope,
        chat_id: UUID,
        draft_id: UUID,
        version: int,
        fields: dict[str, Any],
        reviewed_fields: list[str] | None = None,
    ) -> dict[str, Any]: ...
    def restore(
        self, scope: Scope, chat_id: UUID, draft_id: UUID, version: int
    ) -> dict[str, Any]: ...
    def convert(
        self,
        scope: Scope,
        chat_id: UUID,
        draft_id: UUID,
        version: int,
        payment_due_at: datetime | None,
        without_prepayment: bool,
        reason: str,
    ) -> Order: ...
    def extend(self, scope: Scope, order_id: UUID, version: int) -> Order: ...


class DraftService:
    def __init__(self, access: MembershipReader, repository: DraftRepository):
        self.access, self.repository = access, repository

    def extract(self, scope: Scope, chat_id: UUID, draft_id: UUID, version: int) -> dict[str, Any]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.extract(scope, chat_id, draft_id, version)

    def abandon(self, scope: Scope, chat_id: UUID, draft_id: UUID, version: int) -> dict[str, Any]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.abandon(scope, chat_id, draft_id, version)

    def read(self, scope: Scope, chat_id: UUID) -> dict[str, Any]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.read(scope, chat_id)

    def start(self, scope: Scope, chat_id: UUID) -> dict[str, Any]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.start(scope, chat_id)

    def save(
        self,
        scope: Scope,
        chat_id: UUID,
        draft_id: UUID,
        version: int,
        fields: dict[str, Any],
        reviewed_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.save(
            scope, chat_id, draft_id, version, normalize_fields(fields), reviewed_fields
        )

    def restore(self, scope: Scope, chat_id: UUID, draft_id: UUID, version: int) -> dict[str, Any]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.restore(scope, chat_id, draft_id, version)

    def convert(
        self,
        scope: Scope,
        chat_id: UUID,
        draft_id: UUID,
        version: int,
        payment_due_at: datetime | None = None,
        without_prepayment: bool = False,
        reason: str = "",
    ) -> Order:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.convert(
            scope, chat_id, draft_id, version, payment_due_at, without_prepayment, reason
        )

    def extend(self, scope: Scope, order_id: UUID, version: int) -> Order:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.extend(scope, order_id, version)
