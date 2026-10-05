from decimal import Decimal
from uuid import UUID, uuid4

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize
from tapme.catalog.application.ports import ProductRepository
from tapme.catalog.domain import Product
from tapme.shared.domain import Page, page_bounds


class CatalogService:
    def __init__(self, access: MembershipReader, repository: ProductRepository) -> None:
        self.access = access
        self.repository = repository

    def create(self, scope: Scope, name: str, price: Decimal) -> Product:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.add(Product(uuid4(), scope.business_id, name, price))

    def list(
        self, scope: Scope, limit: int = 50, offset: int = 0, include_hidden: bool = False
    ) -> Page[Product]:
        authorize(self.access, scope, OFFICE_ROLES)
        page_bounds(limit, offset)
        return self.repository.list(scope.business_id, limit, offset, include_hidden)

    def update(
        self,
        scope: Scope,
        product_id: UUID,
        name: str,
        price: Decimal,
        version: int,
        active: bool = True,
    ) -> Product:
        authorize(self.access, scope, OFFICE_ROLES)
        self.repository.get(scope.business_id, product_id)
        return self.repository.save(
            Product(product_id, scope.business_id, name, price, version + 1, active), version
        )
