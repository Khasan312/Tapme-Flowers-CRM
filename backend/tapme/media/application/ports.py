from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol
from uuid import UUID

from tapme.orders.application.workflow import WorkflowRepository


@dataclass(frozen=True)
class Photo:
    id: UUID
    business_id: UUID
    order_id: UUID
    key: str
    kind: str
    created_at: datetime
    actor_id: UUID


@dataclass(frozen=True)
class PhotoInfo:
    id: UUID
    kind: str
    created_at: datetime
    can_delete: bool


class PhotoStorage(Protocol):
    def save(self, key: str, content: bytes) -> str: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class PhotoRepository(Protocol):
    def add(self, photo: Photo) -> None: ...
    def get(self, business_id: UUID, order_id: UUID, photo_id: UUID) -> Photo: ...
    def list(self, business_id: UUID, order_id: UUID) -> tuple[Photo, ...]: ...
    def delete(self, business_id: UUID, order_id: UUID, photo_id: UUID) -> None: ...


class PhotoUnit(Protocol):
    orders: WorkflowRepository
    photos: PhotoRepository

    def after_commit(self, callback: Callable[[], None]) -> None: ...

    def __enter__(self) -> "PhotoUnit": ...
    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
