from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

from tapme.businesses.application.contracts import (
    OFFICE_ROLES,
    MembershipReader,
    Role,
    Scope,
    authorize,
)
from tapme.catalog.application.ports import ProductRepository
from tapme.catalog.domain import Product
from tapme.media.application.ports import PhotoStorage
from tapme.shared.domain import Conflict, InvalidInput, NotFound, Page, page_bounds


class CatalogService:
    def __init__(
        self, access: MembershipReader, repository: ProductRepository, storage: PhotoStorage
    ) -> None:
        self.access = access
        self.repository = repository
        self.storage = storage

    def create(
        self, scope: Scope, name: str, price: Decimal, photo: bytes | None = None
    ) -> Product:
        authorize(self.access, scope, OFFICE_ROLES)
        product = Product(uuid4(), scope.business_id, name, price)
        key = self._save_photo(product, photo) if photo is not None else ""
        try:
            return self.repository.add(replace(product, photo_key=key))
        except Exception:
            if key:
                self.storage.delete(key)
            raise

    def _save_photo(self, product: Product, content: bytes) -> str:
        return self.storage.save(
            f"{product.business_id}/products/{product.id}/{uuid4()}.jpg", content
        )

    def photo(self, scope: Scope, product_id: UUID) -> bytes:
        authorize(self.access, scope, frozenset(Role))
        product = self.repository.get(scope.business_id, product_id)
        if not product.photo_key:
            raise NotFound("У позиции пока нет фотографии.")
        return self.storage.read(product.photo_key)

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
        photo: bytes | None = None,
        remove_photo: bool = False,
    ) -> Product:
        authorize(self.access, scope, OFFICE_ROLES)
        current = self.repository.get(scope.business_id, product_id)
        if current.version != version:
            raise Conflict("Позиция уже изменена. Обновите прайс.")
        if remove_photo and photo is not None:
            raise InvalidInput("Выберите новое фото или удаление прежнего.")
        product = Product(
            product_id,
            scope.business_id,
            name,
            price,
            version + 1,
            active,
            "" if remove_photo else current.photo_key,
        )
        key = self._save_photo(product, photo) if photo is not None else ""
        try:
            return self.repository.save(
                replace(product, photo_key=key) if key else product, version
            )
        except Exception:
            if key:
                self.storage.delete(key)
            raise
        # Replaced files are reclaimed by cleanup_orphan_photos after its grace period.
