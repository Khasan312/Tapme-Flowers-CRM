from typing import Protocol
from uuid import UUID

from tapme.customers.domain import Customer
from tapme.shared.domain import Page


class CustomerReader(Protocol):
    def get(self, business_id: UUID, customer_id: UUID) -> Customer: ...


class CustomerRepository(CustomerReader, Protocol):
    def add(self, customer: Customer) -> Customer: ...
    def list(self, business_id: UUID, search: str, limit: int, offset: int) -> Page[Customer]: ...
    def has_phone(self, business_id: UUID, phones: tuple[str, ...]) -> bool: ...
