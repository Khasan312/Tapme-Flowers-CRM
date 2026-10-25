import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from decimal import ROUND_CEILING, Decimal
from uuid import UUID, uuid4

from tapme.businesses.application.contracts import (
    OFFICE_ROLES,
    MembershipReader,
    Scope,
    authorize,
    ensure_point_access,
)
from tapme.catalog.application.ports import ProductReader
from tapme.customers.application.ports import CustomerReader
from tapme.orders.application.ports import OrderRepository, UnitOfWork
from tapme.orders.domain import Fulfillment, Order, OrderLine
from tapme.shared.domain import Conflict, InvalidInput, Page, page_bounds


@dataclass(frozen=True)
class ItemInput:
    product_id: UUID
    quantity: int


@dataclass(frozen=True)
class CreateOrder:
    customer_id: UUID
    items: tuple[ItemInput, ...]
    recipient_name: str
    recipient_phone: str
    fulfillment: Fulfillment
    delivery_date: date
    window_start: time
    window_end: time
    address: str = ""
    notes: str = ""
    card: str = ""
    occasion: str = ""
    source: str = ""
    relation: str = ""
    point_id: UUID | None = None


class OrderService:
    def __init__(
        self,
        access: MembershipReader,
        customers: CustomerReader,
        products: ProductReader,
        uow: Callable[[], UnitOfWork],
        reads: OrderRepository,
        clock: Callable[[], datetime],
    ) -> None:
        self.access, self.customers, self.products = access, customers, products
        self.uow, self.reads, self.clock = uow, reads, clock

    def create(
        self,
        scope: Scope,
        command: CreateOrder,
        request_key: UUID,
        *,
        prepayment_percent: int = 0,
        payment_due_at: datetime | None = None,
        custom_lines: tuple[OrderLine, ...] = (),
        origin: str = "",
    ) -> Order:
        authorize(self.access, scope, OFFICE_ROLES)
        if prepayment_percent not in {0, 50, 100}:
            raise InvalidInput("Неизвестный размер предоплаты.")
        values = {
            key: value
            for key, value in asdict(command).items()
            if value or key not in {"occasion", "source", "relation", "point_id"}
        }
        if origin or prepayment_percent or custom_lines:
            values["creation_context"] = {
                "origin": origin,
                "prepayment_percent": prepayment_percent,
                "payment_due_at": payment_due_at,
                "custom_lines": [asdict(line) for line in custom_lines],
            }
        if scope.point_id and not command.point_id:
            values["point_id"] = scope.point_id
        fingerprint = hashlib.sha256(
            json.dumps(
                values,
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        with self.uow() as work:
            # One lock serializes number allocation and retries for this business only.
            work.orders.lock_business(scope.business_id)
            existing = work.orders.by_request(scope.business_id, request_key)
            if existing:
                ensure_point_access(self.access, scope, existing.point_id)
                if existing.request_hash != fingerprint:
                    raise Conflict("Этот ключ запроса уже использован для другого заказа.")
                return existing
            customer = self.customers.get(scope.business_id, command.customer_id)
            point_id = self.access.order_point(scope, command.point_id)
            fee = work.delivery.lock(
                scope.business_id,
                command.delivery_date,
                command.window_start,
                command.window_end,
                point_id=point_id,
            ).quote(command.fulfillment)
            lines = []
            for item in command.items:
                product = self.products.get(scope.business_id, item.product_id)
                if not product.active:
                    raise InvalidInput("Позиция скрыта из прайса.")
                lines.append(OrderLine(product.id, product.name, product.price, item.quantity))
            lines.extend(custom_lines)
            required = (
                (sum((line.total for line in lines), start=fee) * prepayment_percent) / 100
            ).quantize(Decimal("1"), rounding=ROUND_CEILING)
            required = min(required, sum((line.total for line in lines), start=fee))
            if required > 0 and payment_due_at is None:
                raise InvalidInput("Укажите срок оплаты заказа.")
            order = Order(
                id=uuid4(),
                business_id=scope.business_id,
                point_id=point_id,
                number=work.orders.next_number(scope.business_id),
                customer_id=customer.id,
                customer_name=customer.name,
                customer_phone=customer.phone,
                recipient_name=command.recipient_name,
                recipient_phone=command.recipient_phone,
                fulfillment=command.fulfillment,
                delivery_date=command.delivery_date,
                window_start=command.window_start,
                window_end=command.window_end,
                address=command.address,
                notes=command.notes,
                card=command.card,
                occasion=command.occasion,
                source=command.source,
                relation=command.relation,
                lines=tuple(lines),
                created_by=scope.user_id,
                created_at=self.clock(),
                request_key=request_key,
                request_hash=fingerprint,
                delivery_fee=fee,
                status="pending" if required > 0 else "new",
                prepayment_percent=prepayment_percent,
                prepayment_required=required,
                payment_due_at=payment_due_at if required > 0 else None,
            )
            work.orders.add(order)
            return order

    def get(self, scope: Scope, order_id: UUID) -> Order:
        authorize(self.access, scope, OFFICE_ROLES)
        order = self.reads.get(scope.business_id, order_id)
        ensure_point_access(self.access, scope, order.point_id)
        return order

    def list(
        self,
        scope: Scope,
        day: date | None = None,
        limit: int = 50,
        offset: int = 0,
        search: str = "",
        status: str = "",
        customer_id: UUID | None = None,
    ) -> Page[Order]:
        authorize(self.access, scope, OFFICE_ROLES)
        page_bounds(limit, offset)
        return self.reads.list(
            scope.business_id,
            day,
            limit,
            offset,
            search,
            status,
            customer_id,
            self.access.point_ids(scope),
        )
