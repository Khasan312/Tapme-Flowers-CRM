from decimal import Decimal

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from tapme.accounts.models import User
from tapme.businesses.models import Business, Membership, Shop
from tapme.catalog.models import ProductRecord
from tapme.customers.models import CustomerRecord


@pytest.fixture
def setup(db):
    cache.clear()
    owner = User.objects.create_user(username="owner", password="test-owner-password")
    other_owner = User.objects.create_user(username="other", password="test-other-password")
    manager = User.objects.create_user(username="manager", password="test-manager-password")
    florist = User.objects.create_user(username="florist", password="test-florist-password")
    businesses = [
        Business.objects.create(name=name) for name in ["Первый магазин", "Второй магазин"]
    ]
    for business in businesses:
        Shop.objects.create(business=business, name=business.name)
    for user, biz, role in [
        (owner, businesses[0], "owner"),
        (manager, businesses[0], "manager"),
        (florist, businesses[0], "florist"),
        (other_owner, businesses[1], "owner"),
    ]:
        Membership.objects.create(user=user, business=biz, role=role)
    customers = [
        CustomerRecord.objects.create(business=b, name="Клиент", phone="+996555123456")
        for b in businesses
    ]
    products = [
        ProductRecord.objects.create(business=b, name="Букет", price=Decimal("1234.50"))
        for b in businesses
    ]
    client = APIClient()
    client.force_login(owner)
    return {
        "owner": owner,
        "manager": manager,
        "florist": florist,
        "other_owner": other_owner,
        "business": businesses[0],
        "other_business": businesses[1],
        "customer": customers[0],
        "other_customer": customers[1],
        "product": products[0],
        "other_product": products[1],
        "client": client,
    }


@pytest.fixture
def payload(setup):
    return {
        "customer_id": str(setup["customer"].id),
        "items": [{"product_id": str(setup["product"].id), "quantity": 2}],
        "recipient_name": "Получатель",
        "recipient_phone": "+996700123456",
        "fulfillment": "courier",
        "delivery_date": "2026-11-19",
        "window_start": "10:00",
        "window_end": "12:00",
        "address": "Бишкек, улица 1",
    }


@pytest.fixture
def base(setup):
    return f"/api/v1/businesses/{setup['business'].id}"
