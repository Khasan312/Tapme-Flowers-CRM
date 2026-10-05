from typing import Protocol
from uuid import UUID

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize


class ActivityReader(Protocol):
    def get(self, business_id: UUID, customer_id: UUID) -> dict[str, object]: ...


class ActivityService:
    def __init__(self, access: MembershipReader, reads: ActivityReader):
        self.access, self.reads = access, reads

    def get(self, scope: Scope, customer_id: UUID) -> dict[str, object]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.reads.get(scope.business_id, customer_id)
