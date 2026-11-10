from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from tapme.shared.domain import Forbidden, NotFound


class Role(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    FLORIST = "florist"
    COURIER = "courier"


OFFICE_ROLES = frozenset({Role.OWNER, Role.MANAGER})


@dataclass(frozen=True)
class Scope:
    user_id: UUID
    business_id: UUID
    point_id: UUID | None = None


class MembershipReader(Protocol):
    def role_for(self, scope: Scope) -> Role | None: ...
    def point_ids(self, scope: Scope) -> tuple[UUID, ...]: ...
    def order_point(self, scope: Scope, point_id: UUID | None) -> UUID | None: ...


def ensure_point_access(reader: MembershipReader, scope: Scope, point_id: UUID | None) -> None:
    if reader.role_for(Scope(scope.user_id, scope.business_id)) is None:
        raise Forbidden("Нет доступа к выбранному магазину.")
    if point_id and reader.role_for(Scope(scope.user_id, scope.business_id, point_id)) is None:
        if reader.role_for(Scope(scope.user_id, scope.business_id)) is None:
            raise Forbidden("Нет доступа к выбранному магазину.")
        raise NotFound("Заказ не найден.")


def authorize(reader: MembershipReader, scope: Scope, roles: frozenset[Role]) -> None:
    if reader.role_for(scope) not in roles:
        raise Forbidden("Нет доступа к этому действию в выбранном магазине.")
