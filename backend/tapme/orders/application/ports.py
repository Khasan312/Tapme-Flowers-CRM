from datetime import date
from types import TracebackType
from typing import Protocol
from uuid import UUID

from tapme.orders.application.delivery import DeliverySlots
from tapme.orders.application.extraction import ExtractionContext, ExtractionResult
from tapme.orders.domain import Order
from tapme.shared.domain import Page


class ChatExtractor(Protocol):
    def extract(self, context: ExtractionContext) -> ExtractionResult: ...


class OrderRepository(Protocol):
    def lock_business(self, business_id: UUID) -> None: ...
    def next_number(self, business_id: UUID) -> int: ...
    def by_request(self, business_id: UUID, key: UUID) -> Order | None: ...
    def add(self, order: Order) -> None: ...
    def get(self, business_id: UUID, order_id: UUID) -> Order: ...
    def list(
        self,
        business_id: UUID,
        day: date | None,
        limit: int,
        offset: int,
        search: str = "",
        status: str = "",
        customer_id: UUID | None = None,
        point_ids: tuple[UUID, ...] | None = None,
    ) -> Page[Order]: ...


class UnitOfWork(Protocol):
    orders: OrderRepository
    delivery: DeliverySlots

    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
