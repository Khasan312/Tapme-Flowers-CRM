import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import date, datetime
from decimal import Decimal
from types import TracebackType
from typing import Protocol
from uuid import UUID, uuid4

from tapme.businesses.application.contracts import (
    OFFICE_ROLES,
    MembershipReader,
    Role,
    Scope,
    authorize,
)
from tapme.catalog.application.ports import ProductReader
from tapme.customers.application.ports import CustomerReader
from tapme.orders.application.delivery import DeliverySlots
from tapme.orders.application.services import CreateOrder
from tapme.orders.domain import Order, OrderLine
from tapme.payments.application.ports import PaymentRepository
from tapme.payments.domain import Payment
from tapme.shared.domain import Conflict, Forbidden, InvalidInput, Page, page_bounds, text


class WorkflowRepository(Protocol):
    def get(self, business_id: UUID, order_id: UUID) -> Order: ...
    def lock(self, business_id: UUID, order_id: UUID) -> Order: ...
    def lock_staff(self, business_id: UUID, user_id: UUID) -> None: ...
    def save(self, order: Order, actor_id: UUID, kind: str, detail: str, now: datetime) -> None: ...
    def event(
        self, order: Order, actor_id: UUID, kind: str, detail: str, now: datetime
    ) -> None: ...
    def tasks(
        self, scope: Scope, role: Role, day: date | None, limit: int, offset: int
    ) -> Page[Order]: ...
    def history(self, business_id: UUID, order_id: UUID) -> list[dict[str, object]]: ...


class WorkflowUnit(Protocol):
    orders: WorkflowRepository
    payments: PaymentRepository
    delivery: DeliverySlots

    def __enter__(self) -> "WorkflowUnit": ...
    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


def ensure_version(order: Order, version: int) -> None:
    if order.version != version:
        raise Conflict("Заказ уже изменён другим сотрудником. Обновите карточку.")


def ensure_order_access(access: MembershipReader, scope: Scope, order: Order) -> Role:
    role = access.role_for(scope)
    if role in OFFICE_ROLES:
        assert role is not None
        return role
    if role == Role.FLORIST and (
        order.florist_id == scope.user_id or (order.status == "new" and order.florist_id is None)
    ):
        return role
    if role == Role.COURIER and order.courier_id == scope.user_id:
        return role
    raise Forbidden("Этот заказ вам не назначен.")


class WorkflowService:
    def __init__(
        self,
        access: MembershipReader,
        customers: CustomerReader,
        products: ProductReader,
        uow: Callable[[], WorkflowUnit],
        reads: WorkflowRepository,
        clock: Callable[[], datetime],
    ):
        self.access, self.customers, self.products = access, customers, products
        self.uow, self.reads, self.clock = uow, reads, clock

    def tasks(
        self, scope: Scope, day: date | None = None, limit: int = 50, offset: int = 0
    ) -> Page[Order]:
        authorize(self.access, scope, frozenset(Role))
        role = self.access.role_for(scope)
        assert role is not None
        page_bounds(limit, offset)
        return self.reads.tasks(scope, role, day, limit, offset)

    def edit(self, scope: Scope, order_id: UUID, version: int, command: CreateOrder) -> Order:
        authorize(self.access, scope, OFFICE_ROLES)
        with self.uow() as work:
            order = work.orders.lock(scope.business_id, order_id)
            ensure_version(order, version)
            if order.status not in {"new", "work"}:
                raise InvalidInput("Редактирование доступно до готовности букета.")
            customer = self.customers.get(scope.business_id, command.customer_id)
            if (
                command.delivery_date,
                command.window_start,
                command.window_end,
                command.fulfillment,
            ) == (order.delivery_date, order.window_start, order.window_end, order.fulfillment):
                fee = order.delivery_fee
            else:
                fee = work.delivery.lock(
                    scope.business_id,
                    command.delivery_date,
                    command.window_start,
                    command.window_end,
                    order_id,
                ).quote(command.fulfillment)
            previous = {line.product_id: line for line in order.lines}
            lines = []
            for item in command.items:
                product = self.products.get(scope.business_id, item.product_id)
                if not product.active and item.product_id not in {
                    line.product_id for line in order.lines
                }:
                    raise InvalidInput("Позиция скрыта из прайса.")
                old = previous.get(item.product_id)
                lines.append(
                    OrderLine(
                        product.id,
                        old.name if old else product.name,
                        old.unit_price if old else product.price,
                        item.quantity,
                    )
                )
            values = asdict(command)
            values.pop("items")
            changed = replace(
                order,
                **values,
                customer_name=customer.name,
                customer_phone=customer.phone,
                lines=tuple(lines),
                delivery_fee=fee,
                version=order.version + 1,
                courier_id=order.courier_id if command.fulfillment == "courier" else None,
            )
            if changed.total < work.payments.balance(scope.business_id, order_id):
                raise InvalidInput("Сначала оформите возврат: новая сумма меньше внесённой оплаты.")
            work.orders.save(
                changed, scope.user_id, "edited", "Изменены данные заказа", self.clock()
            )
            return changed

    def assign(
        self,
        scope: Scope,
        order_id: UUID,
        version: int,
        florist_id: UUID | None,
        courier_id: UUID | None,
    ) -> Order:
        authorize(self.access, scope, OFFICE_ROLES)
        with self.uow() as work:
            order = work.orders.lock(scope.business_id, order_id)
            ensure_version(order, version)
            if order.status in {"done", "cancelled"}:
                raise InvalidInput("Назначения нельзя менять после закрытия заказа.")
            if order.status == "route" and (florist_id != order.florist_id or not courier_id):
                raise InvalidInput(
                    "В заказе в пути можно только заменить курьера на другого активного курьера."
                )
            assignments = [(courier_id, Role.COURIER)]
            if order.status != "route":
                assignments.append((florist_id, Role.FLORIST))
            for staff_id in sorted({uid for uid, _ in assignments if uid}):
                work.orders.lock_staff(scope.business_id, staff_id)
            for user_id, role in assignments:
                if user_id and self.access.role_for(Scope(user_id, scope.business_id)) != role:
                    raise InvalidInput("Выберите активного сотрудника нужной роли своего магазина.")
            if order.status != "new" and not florist_id:
                raise InvalidInput("Нельзя убрать флориста из начатого заказа.")
            if courier_id and order.fulfillment != "courier":
                raise InvalidInput("Для самовывоза курьер не нужен.")
            changed = replace(
                order, florist_id=florist_id, courier_id=courier_id, version=order.version + 1
            )
            work.orders.save(
                changed,
                scope.user_id,
                "courier_reassigned" if order.status == "route" else "assigned",
                "Курьер заменён. Статус «В пути» сохранён."
                if order.status == "route"
                else "Обновлены ответственные сотрудники",
                self.clock(),
            )
            return changed

    def transition(
        self, scope: Scope, order_id: UUID, version: int, status: str, reason: str = ""
    ) -> Order:
        authorize(self.access, scope, frozenset(Role))
        with self.uow() as work:
            order = work.orders.lock(scope.business_id, order_id)
            # A florist can claim an unassigned order here; serialize with staff removal.
            work.orders.lock_staff(scope.business_id, scope.user_id)
            role = ensure_order_access(self.access, scope, order)
            ensure_version(order, version)
            if role == Role.FLORIST:
                if status not in {"work", "ready"}:
                    raise Forbidden("Флорист может взять заказ и отметить готовность.")
                if order.florist_id is None and order.status == "new" and status == "work":
                    order = replace(order, florist_id=scope.user_id)
            if role == Role.COURIER and status not in {"route", "done"}:
                raise Forbidden("Курьер может забрать и вручить назначенный заказ.")
            order.check_transition(status, reason)
            now = self.clock()
            changed = replace(
                order,
                status=status,
                version=order.version + 1,
                completed_at=now if status == "done" else None,
                delivery_issue="" if status in {"done", "cancelled"} else order.delivery_issue,
                cancellation_reason=text(reason, "Причина отмены", 1000)
                if status == "cancelled"
                else "",
            )
            work.orders.save(changed, scope.user_id, status, changed.cancellation_reason, now)
            return changed

    def issue(self, scope: Scope, order_id: UUID, version: int, detail: str) -> Order:
        with self.uow() as work:
            order = work.orders.lock(scope.business_id, order_id)
            role = ensure_order_access(self.access, scope, order)
            if role not in OFFICE_ROLES and role != Role.COURIER:
                raise Forbidden("Сообщение о доставке доступно курьеру и менеджеру.")
            ensure_version(order, version)
            if order.status != "route":
                raise InvalidInput("Проблему доставки можно отметить для заказа в пути.")
            changed = replace(
                order,
                version=order.version + 1,
                delivery_issue=text(detail, "Проблема доставки", 1000),
            )
            work.orders.save(
                changed,
                scope.user_id,
                "delivery_issue",
                text(detail, "Проблема доставки", 1000),
                self.clock(),
            )
            return changed

    def payment(
        self,
        scope: Scope,
        order_id: UUID,
        amount: Decimal,
        kind: str,
        method: str,
        note: str,
        request_key: UUID,
    ) -> Payment:
        authorize(self.access, scope, OFFICE_ROLES)
        fingerprint = hashlib.sha256(
            json.dumps([str(order_id), str(amount), kind, method, note]).encode()
        ).hexdigest()
        with self.uow() as work:
            order = work.orders.lock(scope.business_id, order_id)
            previous = work.payments.by_request(scope.business_id, request_key)
            if previous:
                if previous.request_hash != fingerprint:
                    raise Conflict("Ключ уже использован для другой операции.")
                return previous
            entry = Payment(
                uuid4(),
                scope.business_id,
                order_id,
                amount,
                kind,
                method,
                note,
                scope.user_id,
                self.clock(),
                request_key,
                fingerprint,
            )
            entry.check_balance(
                work.payments.balance(scope.business_id, order_id),
                order.total,
                order.status == "cancelled",
            )
            work.payments.add(entry)
            work.orders.save(
                replace(order, version=order.version + 1),
                scope.user_id,
                kind,
                f"{amount} · {method} · {note}",
                self.clock(),
            )
            return entry

    def payments(self, scope: Scope, order_id: UUID) -> tuple[Payment, ...]:
        authorize(self.access, scope, OFFICE_ROLES)
        with self.uow() as work:
            work.orders.get(scope.business_id, order_id)
            return work.payments.list(scope.business_id, order_id)

    def history(self, scope: Scope, order_id: UUID) -> list[dict[str, object]]:
        authorize(self.access, scope, OFFICE_ROLES)
        self.reads.get(scope.business_id, order_id)
        return self.reads.history(scope.business_id, order_id)

    def resolve_issue(self, scope: Scope, order_id: UUID, version: int) -> Order:
        authorize(self.access, scope, OFFICE_ROLES)
        with self.uow() as work:
            order = work.orders.lock(scope.business_id, order_id)
            ensure_version(order, version)
            if not order.delivery_issue:
                raise InvalidInput("Нет открытой проблемы доставки.")
            changed = replace(order, version=order.version + 1, delivery_issue="")
            work.orders.save(
                changed,
                scope.user_id,
                "delivery_issue_resolved",
                "Проблема доставки решена",
                self.clock(),
            )
            return changed
