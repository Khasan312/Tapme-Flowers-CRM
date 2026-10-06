import io
import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from tapme.accounts.models import User
from tapme.businesses.management.commands.seed_demo import LABEL, DemoSeed
from tapme.businesses.models import Membership
from tapme.catalog.models import ProductRecord
from tapme.customers.models import CustomerRecord
from tapme.feedback.models import FeedbackRecord
from tapme.orders.infrastructure.repository import to_domain
from tapme.orders.models import OfficeTask, OrderRecord
from tapme.payments.models import PaymentRecord
from tapme.reminders.models import ReminderRecord


def seed(monkeypatch, owner="owner"):
    monkeypatch.setattr(
        "tapme.businesses.management.commands.seed_demo.timezone.now",
        lambda: datetime(2026, 10, 6, 11, tzinfo=UTC),
    )
    output = io.StringIO()
    call_command("seed_demo", owner=owner, stdout=output)
    return json.loads(output.getvalue())


def test_demo_is_consistent_scoped_and_preserves_edits_on_repeat(setup, payload, base, monkeypatch):
    # A pre-existing customer/order and another store must not be repurposed as demo data.
    response = setup["client"].post(
        base + "/orders/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="894f548c-3743-4f78-8cdb-ea83a1169581",
    )
    assert response.status_code == 201
    original_order = OrderRecord.objects.filter(id=response.json()["id"]).values().get()
    original_customer = CustomerRecord.objects.filter(id=setup["customer"].id).values().get()
    result = seed(monkeypatch)
    demo = OrderRecord.objects.filter(business=setup["business"], notes__startswith=LABEL)
    assert set(demo.values_list("status", flat=True)) == {
        "new",
        "work",
        "ready",
        "route",
        "done",
        "cancelled",
    }
    assert result["created"]["orders"] == demo.count()
    assert not OrderRecord.objects.filter(business=setup["other_business"]).exists()
    assert CustomerRecord.objects.filter(business=setup["other_business"]).count() == 1
    assert ProductRecord.objects.filter(business=setup["other_business"]).count() == 1
    assert OrderRecord.objects.filter(id=original_order["id"]).values().get() == original_order
    assert (
        CustomerRecord.objects.filter(id=original_customer["id"]).values().get()
        == original_customer
    )
    for row in demo.prefetch_related("lines", "payments", "events"):
        order = to_domain(row)
        assert order.total == row.total
        assert Decimal("0") <= order.paid_amount <= order.total
        assert row.events.filter(kind="created").exists()
        assert (
            row.completed_at <= datetime(2026, 10, 6, 11, tzinfo=UTC)
            if row.status == "done"
            else row.completed_at is None
        )
        if row.status in {"work", "ready", "route", "done"}:
            assert row.florist_id
        if row.status == "route":
            assert row.fulfillment == "courier" and row.courier_id
        if row.status == "cancelled":
            assert row.cancellation_reason and order.paid_amount == 0
    reminders = ReminderRecord.objects.filter(business=setup["business"])
    assert reminders.filter(key__startswith="date:", state="wait").exists()
    assert reminders.filter(key__startswith="inactive:", state="wait").exists()
    assert set(reminders.values_list("state", flat=True)) == {
        "wait",
        "sent",
        "answered",
        "ordered",
        "skipped",
    }
    assert demo.filter(status="route", delivery_issue__gt="").exists()
    assert demo.filter(status="done").exists()
    assert FeedbackRecord.objects.filter(kind="complaint", status="open").exists()
    assert OfficeTask.objects.filter(business=setup["business"]).exists()
    assert not any(
        u.has_usable_password() for u in User.objects.filter(username__startswith="demo_")
    )
    customer = CustomerRecord.objects.filter(
        business=setup["business"], tags__contains=["Демо"]
    ).first()
    customer.notes = "Пользовательская правка"
    customer.save(update_fields=["notes"])
    order = demo.first()
    order.notes = "Правка демонстрационного заказа"
    order.save(update_fields=["notes"])
    models = (
        User,
        Membership,
        CustomerRecord,
        ProductRecord,
        OrderRecord,
        PaymentRecord,
        ReminderRecord,
        FeedbackRecord,
        OfficeTask,
    )
    counts = [model.objects.count() for model in models]
    second = seed(monkeypatch)
    assert not any(second["created"].values())
    assert [model.objects.count() for model in models] == counts
    customer.refresh_from_db()
    order.refresh_from_db()
    assert customer.notes == "Пользовательская правка"
    assert order.notes == "Правка демонстрационного заказа"


def test_demo_rolls_back_whole_batch_on_failure(setup, monkeypatch):
    models = (User, Membership, CustomerRecord, ProductRecord, OrderRecord, ReminderRecord)
    counts = [model.objects.count() for model in models]

    def fail(self, *args):
        raise CommandError("Test failure after creating customers and staff")

    monkeypatch.setattr(DemoSeed, "orders", fail)
    with pytest.raises(CommandError):
        seed(monkeypatch)
    assert [model.objects.count() for model in models] == counts


def test_demo_requires_store_owner_and_respects_delivery_capacity(setup, monkeypatch):
    with pytest.raises(CommandError):
        seed(monkeypatch, owner="manager")
    shop = setup["business"].shop
    shop.enforce_capacity = True
    shop.delivery_windows = [{"start": "10:00", "end": "12:00", "capacity": 1, "price": "100.00"}]
    shop.save()
    with pytest.raises(CommandError, match="изменения отменены"):
        seed(monkeypatch)
    assert not User.objects.filter(username__startswith="demo_").exists()
    assert not OrderRecord.objects.exists()
    assert not CustomerRecord.objects.filter(tags__contains=["Демо"]).exists()
