"""The old release can still write while an additive migration is deployed."""

import uuid
from datetime import date, time

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.utils import timezone

from tapme.businesses.models import Business, Shop
from tapme.catalog.models import ProductRecord
from tapme.customers.models import CustomerRecord
from tapme.orders.models import OrderRecord
from tapme.reminders.models import ReminderRecord, ReminderSettings


@pytest.mark.django_db
def test_previous_release_can_insert_into_expanded_schema(setup):
    apps = (
        MigrationLoader(connection)
        .project_state(
            [
                ("businesses", "0004_settings_versions_and_recovery"),
                ("catalog", "0004_productrecord_photo_key"),
                ("customers", "0005_additional_phones"),
                ("orders", "0006_orderrecord_occasion_orderrecord_relation_and_more"),
                ("reminders", "0005_settings_versions_and_recovery"),
            ]
        )
        .apps
    )
    business = Business.objects.create(name="Rolling release")
    shop = apps.get_model("businesses", "Shop").objects.create(
        business_id=business.id, name=business.name
    )
    customer = apps.get_model("customers", "CustomerRecord").objects.create(
        business_id=business.id, code=1, name="Legacy customer", phone="+996555999888"
    )
    product = apps.get_model("catalog", "ProductRecord").objects.create(
        business_id=business.id, name="Legacy bouquet", price=1000
    )
    order = apps.get_model("orders", "OrderRecord").objects.create(
        id=uuid.uuid4(),
        business_id=business.id,
        number=1,
        customer_id=customer.id,
        customer_name=customer.name,
        customer_phone=customer.phone,
        recipient_name="Recipient",
        fulfillment="pickup",
        delivery_date=date(2026, 11, 19),
        window_start=time(10),
        window_end=time(12),
        total=1000,
        created_by_id=setup["owner"].id,
        created_at=timezone.now(),
        request_key=uuid.uuid4(),
        request_hash="legacy",
    )
    apps.get_model("reminders", "ReminderSettings").objects.create(business_id=business.id)
    reminder = apps.get_model("reminders", "ReminderRecord").objects.create(
        business_id=business.id,
        customer_id=customer.id,
        key="legacy",
        event="Birthday",
        due_date=date(2026, 11, 19),
    )

    current_shop = Shop.objects.get(pk=shop.pk)
    assert current_shop.payment_note == current_shop.payment_qr_key == ""
    assert current_shop.payment_message.startswith("Заказ №")
    assert current_shop.payment_version == 1
    assert CustomerRecord.objects.get(pk=customer.pk).origin == "manual"
    assert ProductRecord.objects.get(pk=product.pk).system_kind == ""
    current_order = OrderRecord.objects.get(pk=order.pk)
    assert current_order.prepayment_percent == current_order.prepayment_required == 0
    assert ReminderRecord.objects.get(pk=reminder.pk).occurrence_key == ""
    reminder_settings = ReminderSettings.objects.get(pk=business.id)
    assert reminder_settings.min_days_between == 7
    assert reminder_settings.scenarios_initialized is False


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("repair_existing", [False, True])
def test_old_shop_insert_between_branch_migrations(repair_existing):
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    previous = [("businesses", "0005_shop_payment_message_shop_payment_note_and_more")]
    expanded = [("businesses", "0006_membershippoint_alter_shop_options_shop_active_and_more")]
    try:
        executor.migrate(previous)
        old = executor.loader.project_state(previous).apps
        business = old.get_model("businesses", "Business").objects.create(name="Old API store")
        executor = MigrationExecutor(connection)
        executor.migrate(expanded)
        if repair_existing:
            with connection.cursor() as cursor:
                cursor.execute("""ALTER TABLE businesses_shop
                    ALTER COLUMN active DROP DEFAULT,
                    ALTER COLUMN is_primary DROP DEFAULT,
                    ALTER COLUMN short_name DROP DEFAULT,
                    ALTER COLUMN sort DROP DEFAULT""")
            executor = MigrationExecutor(connection)
            expanded = [
                ("businesses", "0007_alter_membership_is_active_alter_shop_active_and_more")
            ]
            executor.migrate(expanded)
        shop = old.get_model("businesses", "Shop").objects.create(
            business_id=business.id, name="Old API point"
        )
        current = executor.loader.project_state(expanded).apps
        point = current.get_model("businesses", "Shop").objects.get(id=shop.id)
        assert point.active and point.is_primary
        assert point.short_name == "Основная" and point.sort == 0
    finally:
        MigrationExecutor(connection).migrate(latest)
