import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from uuid import UUID, uuid4

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize
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

    def create(self, scope: Scope, command: CreateOrder, request_key: UUID) -> Order:
        authorize(self.access, scope, OFFICE_ROLES)
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    key: value
                    for key, value in asdict(command).items()
                    if value or key not in {"occasion", "source", "relation"}
                },
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        with self.uow() as work:
            # One lock serializes number allocation and retries for this business only.
            work.orders.lock_business(scope.business_id)
            existing = work.orders.by_request(scope.business_id, request_key)
            if existing:
                if existing.request_hash != fingerprint:
                    raise Conflict("Этот ключ запроса уже использован для другого заказа.")
                return existing
            customer = self.customers.get(scope.business_id, command.customer_id)
            fee = work.delivery.lock(
                scope.business_id, command.delivery_date, command.window_start, command.window_end
            ).quote(command.fulfillment)
            lines = []
            for item in command.items:
                product = self.products.get(scope.business_id, item.product_id)
                if not product.active:
                    raise InvalidInput("Позиция скрыта из прайса.")
                lines.append(OrderLine(product.id, product.name, product.price, item.quantity))
            order = Order(
                id=uuid4(),
                business_id=scope.business_id,
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
            )
            work.orders.add(order)
            return order

    def get(self, scope: Scope, order_id: UUID) -> Order:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.reads.get(scope.business_id, order_id)

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
        return self.reads.list(scope.business_id, day, limit, offset, search, status, customer_id)
