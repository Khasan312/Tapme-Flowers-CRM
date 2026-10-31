from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import uuid4

import pytest

from tapme.businesses.application.contracts import Role, Scope
from tapme.catalog.domain import Product
from tapme.customers.domain import Customer
from tapme.orders.application.delivery import DeliverySlot
from tapme.orders.application.services import CreateOrder, ItemInput, OrderService
from tapme.orders.domain import Fulfillment
from tapme.shared.domain import Conflict, InvalidInput, NotFound


class MemoryDirectory:
    def __init__(self, entity):
        self.entity = entity

    def get(self, business_id, entity_id):
        if self.entity.id != entity_id or self.entity.business_id != business_id:
            raise NotFound("Не найдено.")
        return self.entity


class MemoryOrders:
    def __init__(self):
        self.records = {}
        self.counter = 0

    def lock_business(self, business_id):
        pass

    def next_number(self, business_id):
        self.counter += 1
        return self.counter

    def by_request(self, business_id, key):
        return self.records.get((business_id, key))

    def add(self, order):
        self.records[(order.business_id, order.request_key)] = order


class MemoryUow:
    def __init__(self, orders):
        self.orders = orders
        self.delivery = self

    def lock(self, business_id, day, start, end, exclude_id=None, point_id=None):
        return DeliverySlot(Decimal("0.00"), 6, 0, False, True)

    def __enter__(self):
        self.snapshot = deepcopy(self.orders.__dict__)
        return self

    def __exit__(self, kind, error, traceback):
        if error:
            self.orders.__dict__.update(self.snapshot)


@pytest.fixture
def scenario():
    scope = Scope(uuid4(), uuid4())
    customer = Customer(uuid4(), scope.business_id, "Айбек", "+996555123456")
    product = Product(uuid4(), scope.business_id, "Букет", Decimal("100.10"))

    class Access:
        def order_point(self, scope, point_id):
            return point_id

        def role_for(self, requested):
            return Role.OWNER if requested == scope else None

    records = MemoryOrders()
    service = OrderService(
        Access(),
        MemoryDirectory(customer),
        MemoryDirectory(product),
        lambda: MemoryUow(records),
        records,
        lambda: datetime(2026, 9, 21, tzinfo=UTC),
    )
    command = CreateOrder(
        customer.id,
        (ItemInput(product.id, 3),),
        "Получатель",
        "",
        Fulfillment.COURIER,
        date(2026, 9, 22),
        time(10),
        time(12),
        "Бишкек",
    )
    return scope, service, command, records


def test_create_and_retry_without_framework(scenario):
    scope, service, command, records = scenario
    key = uuid4()
    first = service.create(scope, command, key)
    assert first.total == Decimal("300.30")
    assert service.create(scope, command, key) == first
    assert records.counter == 1
    with pytest.raises(Conflict):
        service.create(scope, replace(command, notes="Другой заказ"), key)


def test_failed_scenario_rolls_back_unit_of_work(scenario):
    scope, service, command, records = scenario
    with pytest.raises(InvalidInput):
        service.create(scope, replace(command, address=""), uuid4())
    assert records.records == {}
    assert records.counter == 0


def test_foreign_customer_denied_without_database(scenario):
    scope, service, command, records = scenario
    with pytest.raises(NotFound):
        service.create(scope, replace(command, customer_id=uuid4()), uuid4())
    assert records.records == {}


def test_unknown_fulfillment_rejected_without_framework(scenario):
    scope, service, command, records = scenario
    with pytest.raises(InvalidInput):
        service.create(scope, replace(command, fulfillment="teleport"), uuid4())
    assert records.records == {}
