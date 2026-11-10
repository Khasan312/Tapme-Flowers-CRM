from datetime import datetime
from typing import Protocol

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize
from tapme.shared.domain import page_bounds


class DirectoryReader(Protocol):
    def list(
        self, scope: Scope, search: str, group: str, limit: int, offset: int, now: datetime
    ) -> dict[str, object]: ...


class DirectoryService:
    def __init__(self, access: MembershipReader, reader: DirectoryReader):
        self.access, self.reader = access, reader

    def list(
        self, scope: Scope, search: str, group: str, limit: int, offset: int, now: datetime
    ) -> dict[str, object]:
        authorize(self.access, scope, OFFICE_ROLES)
        page_bounds(limit, offset)
        return self.reader.list(scope, search, group, limit, offset, now)
