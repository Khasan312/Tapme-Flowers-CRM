import ast
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from tapme.businesses.application.contracts import Role, Scope, authorize
from tapme.catalog.domain import Product
from tapme.customers.domain import Customer
from tapme.orders.domain import OrderLine
from tapme.shared.domain import Forbidden, InvalidInput


@pytest.mark.parametrize("price", ["-1", "1.001", "NaN", "Infinity", "10000000000"])
def test_invalid_money(price):
    with pytest.raises(InvalidInput):
        Product(uuid4(), uuid4(), "Букет", Decimal(price))


def test_exact_decimal_calculation():
    line = OrderLine(uuid4(), "Роза", Decimal("0.10"), 3)
    assert line.total == Decimal("0.30")


@pytest.mark.parametrize("quantity", [0, -1, 1000, 1.5, True])
def test_invalid_quantity(quantity):
    with pytest.raises(InvalidInput):
        OrderLine(uuid4(), "Роза", Decimal("1.00"), quantity)


def test_normalized_customer():
    customer = Customer(uuid4(), uuid4(), "  Айбек  ", "+996 (555) 12-34-56")
    assert customer.name == "Айбек"
    assert customer.phone == "+996555123456"
    assert customer.consent is False


def test_application_role_policy_without_django():
    class Access:
        def role_for(self, scope):
            return Role.COURIER

    with pytest.raises(Forbidden):
        authorize(Access(), Scope(uuid4(), uuid4()), frozenset({Role.OWNER}))


def test_core_import_boundaries():
    root = Path(__file__).resolve().parents[2] / "tapme"
    files = [*root.glob("*/domain.py"), *root.glob("*/application/*.py")]
    assert files
    for path in files:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, f"Use absolute core imports: {path}"
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                assert not module.startswith(
                    ("django", "rest_framework", "config", "psycopg", "celery", "boto")
                ), (path, module)
                assert not any(
                    part in module.split(".") for part in ("models", "infrastructure", "api")
                ), (path, module)
