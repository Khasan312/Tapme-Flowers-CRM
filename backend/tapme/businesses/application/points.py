from __future__ import annotations

import builtins
from typing import Protocol
from uuid import UUID

from tapme.businesses.application.contracts import MembershipReader, Role, Scope, authorize


class PointRepository(Protocol):
    def list(self, scope: Scope) -> list[dict[str, object]]: ...
    def get(self, scope: Scope, point_id: UUID) -> dict[str, object]: ...
    def save(
        self, scope: Scope, point_id: UUID | None, values: dict[str, object]
    ) -> dict[str, object]: ...
    def archive(self, scope: Scope, point_id: UUID, version: int) -> None: ...
    def staff_points(self, scope: Scope, user_id: UUID, point_ids: builtins.list[UUID]) -> None: ...


class PointService:
    def __init__(self, access: MembershipReader, repository: PointRepository):
        self.access, self.repository = access, repository

    def list(self, scope: Scope) -> list[dict[str, object]]:
        authorize(self.access, scope, frozenset(Role))
        return self.repository.list(scope)

    def get(self, scope: Scope, point_id: UUID) -> dict[str, object]:
        authorize(self.access, scope, frozenset({Role.OWNER, Role.MANAGER}))
        return self.repository.get(scope, point_id)

    def save(
        self, scope: Scope, point_id: UUID | None, values: dict[str, object]
    ) -> dict[str, object]:
        authorize(self.access, scope, frozenset({Role.OWNER}))
        return self.repository.save(scope, point_id, values)

    def archive(self, scope: Scope, point_id: UUID, version: int) -> None:
        authorize(self.access, scope, frozenset({Role.OWNER}))
        self.repository.archive(scope, point_id, version)

    def staff_points(self, scope: Scope, user_id: UUID, point_ids: builtins.list[UUID]) -> None:
        authorize(self.access, scope, frozenset({Role.OWNER}))
        self.repository.staff_points(scope, user_id, point_ids)
