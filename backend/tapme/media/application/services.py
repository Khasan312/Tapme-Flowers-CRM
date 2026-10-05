from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Role, Scope
from tapme.media.application.ports import Photo, PhotoStorage, PhotoUnit
from tapme.orders.application.workflow import ensure_order_access
from tapme.shared.domain import Forbidden, InvalidInput


class PhotoService:
    def __init__(
        self,
        access: MembershipReader,
        uow: Callable[[], PhotoUnit],
        storage: PhotoStorage,
        clock: Callable[[], datetime],
    ):
        self.access, self.uow, self.storage, self.clock = access, uow, storage, clock

    def upload(self, scope: Scope, order_id: UUID, kind: str, content: bytes) -> Photo:
        saved_key = None
        try:
            with self.uow() as work:
                order = work.orders.lock(scope.business_id, order_id)
                role = ensure_order_access(self.access, scope, order)
                if kind not in {"bouquet", "delivery"}:
                    raise InvalidInput("Выберите фото букета или вручения.")
                if role not in OFFICE_ROLES and (
                    (
                        kind == "bouquet"
                        and (role != Role.FLORIST or order.florist_id != scope.user_id)
                    )
                    or (kind == "delivery" and role != Role.COURIER)
                ):
                    raise Forbidden("Нельзя добавлять фото этого этапа.")
                if order.status == "cancelled":
                    raise InvalidInput("Заказ отменён.")
                if len(work.photos.list(scope.business_id, order_id)) >= 20:
                    raise InvalidInput("Для заказа уже загружено 20 фотографий.")
                photo_id = uuid4()
                saved_key = self.storage.save(
                    f"{scope.business_id}/{order_id}/{photo_id}.jpg", content
                )
                photo = Photo(
                    photo_id,
                    scope.business_id,
                    order_id,
                    saved_key,
                    kind,
                    self.clock(),
                    scope.user_id,
                )
                work.photos.add(photo)
                work.orders.event(order, scope.user_id, "photo", kind, self.clock())
                return photo
        except Exception:
            if saved_key:
                self.storage.delete(saved_key)
            raise

    def list(self, scope: Scope, order_id: UUID) -> tuple[Photo, ...]:
        with self.uow() as work:
            order = work.orders.get(scope.business_id, order_id)
            ensure_order_access(self.access, scope, order)
            return work.photos.list(scope.business_id, order_id)

    def read(self, scope: Scope, order_id: UUID, photo_id: UUID) -> bytes:
        with self.uow() as work:
            ensure_order_access(self.access, scope, work.orders.get(scope.business_id, order_id))
            photo = work.photos.get(scope.business_id, order_id, photo_id)
            return self.storage.read(photo.key)
