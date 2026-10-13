from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Role, Scope
from tapme.media.application.ports import Photo, PhotoInfo, PhotoStorage, PhotoUnit
from tapme.orders.application.workflow import ensure_order_access
from tapme.orders.domain import Order
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

    @staticmethod
    def can_change(scope: Scope, order: Order, role: Role, kind: str) -> bool:
        return order.status != "cancelled" and (
            role in OFFICE_ROLES
            or (role == Role.FLORIST and order.florist_id == scope.user_id and kind == "bouquet")
            or (role == Role.COURIER and order.courier_id == scope.user_id and kind == "delivery")
        )

    def upload(self, scope: Scope, order_id: UUID, kind: str, content: bytes) -> PhotoInfo:
        saved_key = None
        try:
            with self.uow() as work:
                order = work.orders.lock(scope.business_id, order_id)
                role = ensure_order_access(self.access, scope, order)
                if kind not in {"bouquet", "delivery"}:
                    raise InvalidInput("Выберите фото букета или вручения.")
                if order.status == "cancelled":
                    raise InvalidInput("Заказ отменён.")
                if not self.can_change(scope, order, role, kind):
                    raise Forbidden("Нельзя добавлять фото этого этапа.")
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
                return PhotoInfo(photo.id, photo.kind, photo.created_at, True)
        except Exception:
            if saved_key:
                self.storage.delete(saved_key)
            raise

    def list(self, scope: Scope, order_id: UUID) -> tuple[PhotoInfo, ...]:
        with self.uow() as work:
            order = work.orders.get(scope.business_id, order_id)
            role = ensure_order_access(self.access, scope, order)
            return tuple(
                PhotoInfo(
                    photo.id,
                    photo.kind,
                    photo.created_at,
                    self.can_change(scope, order, role, photo.kind),
                )
                for photo in work.photos.list(scope.business_id, order_id)
            )

    def delete(self, scope: Scope, order_id: UUID, photo_id: UUID) -> None:
        with self.uow() as work:
            order = work.orders.lock(scope.business_id, order_id)
            role = ensure_order_access(self.access, scope, order)
            photo = work.photos.get(scope.business_id, order_id, photo_id)
            if order.status == "cancelled":
                raise InvalidInput("Заказ отменён.")
            if not self.can_change(scope, order, role, photo.kind):
                raise Forbidden("Нельзя удалять фото этого этапа.")
            work.photos.delete(scope.business_id, order_id, photo_id)
            detail = "Фото букета" if photo.kind == "bouquet" else "Фото вручения"
            work.orders.event(order, scope.user_id, "photo_deleted", detail, self.clock())
            # A rollback must retain the file. Failed cleanup can be retried by
            # cleanup_orphan_photos; the deleted photo is already inaccessible.
            work.after_commit(lambda: self.storage.delete(photo.key))

    def read(self, scope: Scope, order_id: UUID, photo_id: UUID) -> bytes:
        with self.uow() as work:
            ensure_order_access(self.access, scope, work.orders.get(scope.business_id, order_id))
            photo = work.photos.get(scope.business_id, order_id, photo_id)
            return self.storage.read(photo.key)
