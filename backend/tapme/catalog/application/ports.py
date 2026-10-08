from typing import Protocol
from uuid import UUID

from tapme.catalog.domain import Product
from tapme.shared.domain import Page


class ProductReader(Protocol):
    def get(self, business_id: UUID, product_id: UUID) -> Product: ...


class ProductPhotoReader(Protocol):
    def photo_versions(
        self, business_id: UUID, product_ids: tuple[UUID, ...]
    ) -> dict[UUID, int]: ...


class ProductRepository(ProductReader, Protocol):
    def add(self, product: Product) -> Product: ...
    def save(self, product: Product, expected_version: int) -> Product: ...
    def list(
        self, business_id: UUID, limit: int, offset: int, include_hidden: bool = False
    ) -> Page[Product]: ...
