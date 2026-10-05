from typing import Protocol
from uuid import UUID

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize
from tapme.customers.domain import Customer, ImportantDate, Recipient
from tapme.shared.domain import InvalidInput


class ProfileRepository(Protocol):
    def get(self, business_id: UUID, customer_id: UUID) -> dict[str, object]: ...
    def save(
        self,
        customer: Customer,
        version: int,
        recipients: tuple[Recipient, ...],
        dates: tuple[ImportantDate, ...],
    ) -> dict[str, object]: ...


class ProfileService:
    def __init__(self, access: MembershipReader, repository: ProfileRepository):
        self.access, self.repository = access, repository

    def get(self, scope: Scope, customer_id: UUID) -> dict[str, object]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.get(scope.business_id, customer_id)

    def save(
        self,
        scope: Scope,
        customer: Customer,
        version: int,
        recipients: tuple[Recipient, ...],
        dates: tuple[ImportantDate, ...],
    ) -> dict[str, object]:
        authorize(self.access, scope, OFFICE_ROLES)
        if customer.business_id != scope.business_id:
            raise InvalidInput("Клиент относится к другому магазину.")
        if len(recipients) > 50 or len(dates) > 50:
            raise InvalidInput("Не более 50 получателей и дат на клиента.")
        for recipient in recipients:
            recipient.validate()
        for date in dates:
            date.validate()
        if len({r.id for r in recipients}) != len(recipients) or len({d.id for d in dates}) != len(
            dates
        ):
            raise InvalidInput("Повторяющиеся записи в карточке.")
        return self.repository.save(customer, version, recipients, dates)
