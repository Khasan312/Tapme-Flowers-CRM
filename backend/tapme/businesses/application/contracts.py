from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from tapme.shared.domain import Forbidden


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


class MembershipReader(Protocol):
    def role_for(self, scope: Scope) -> Role | None: ...


def authorize(reader: MembershipReader, scope: Scope, roles: frozenset[Role]) -> None:
    if reader.role_for(scope) not in roles:
        raise Forbidden("Нет доступа к этому действию в выбранном магазине.")
