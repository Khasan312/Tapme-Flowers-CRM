from uuid import uuid4

from tapme.businesses.application.contracts import (
    OFFICE_ROLES,
    MembershipReader,
    Scope,
    authorize,
)
from tapme.customers.application.ports import CustomerRepository
from tapme.customers.domain import Customer
from tapme.shared.domain import Page, page_bounds


class CustomerService:
    def __init__(self, access: MembershipReader, repository: CustomerRepository) -> None:
        self.access = access
        self.repository = repository

    def create(
        self,
        scope: Scope,
        name: str,
        phone: str,
        notes: str = "",
        consent: bool = False,
        source: str = "",
        tags: tuple[str, ...] = (),
    ) -> Customer:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.add(
            Customer(uuid4(), scope.business_id, name, phone, notes, consent, source, tuple(tags))
        )

    def list(
        self, scope: Scope, search: str = "", limit: int = 50, offset: int = 0
    ) -> Page[Customer]:
        authorize(self.access, scope, OFFICE_ROLES)
        page_bounds(limit, offset)
        return self.repository.list(scope.business_id, search, limit, offset)
