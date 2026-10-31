from datetime import datetime
from typing import Protocol
from uuid import UUID

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize
from tapme.shared.domain import page_bounds, text


class OrderDeskReader(Protocol):
    def read(
        self,
        actor: Scope,
        scope: str,
        day: str,
        search: str,
        status: str,
        limit: int,
        offset: int,
        now: datetime,
    ) -> dict[str, object]: ...
    def notes(self, actor: Scope) -> list[dict[str, object]]: ...
    def add_note(self, scope: Scope, content: str) -> dict[str, object]: ...
    def complete_note(self, scope: Scope, note_id: UUID) -> None: ...


class OrderDeskService:
    def __init__(self, access: MembershipReader, reader: OrderDeskReader):
        self.access, self.reader = access, reader

    def read(
        self,
        actor: Scope,
        scope: str,
        day: str,
        search: str,
        status: str,
        limit: int,
        offset: int,
        now: datetime,
    ) -> dict[str, object]:
        authorize(self.access, actor, OFFICE_ROLES)
        page_bounds(limit, offset)
        return self.reader.read(actor, scope, day, search, status, limit, offset, now)

    def notes(self, actor: Scope) -> list[dict[str, object]]:
        authorize(self.access, actor, OFFICE_ROLES)
        return self.reader.notes(actor)

    def add_note(self, actor: Scope, content: str) -> dict[str, object]:
        authorize(self.access, actor, OFFICE_ROLES)
        return self.reader.add_note(actor, text(content, "Задача", 500))

    def complete_note(self, actor: Scope, note_id: UUID) -> None:
        authorize(self.access, actor, OFFICE_ROLES)
        self.reader.complete_note(actor, note_id)
