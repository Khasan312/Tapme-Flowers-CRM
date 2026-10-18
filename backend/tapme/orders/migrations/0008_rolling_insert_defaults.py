"""Repair pilot databases that applied the expand migrations before SQL defaults.

Fresh installations already get these defaults in the unpublished expand
migrations. Keeping them there also protects old workers during deployment.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0007_orderrecord_payment_due_at_and_more"),
        ("catalog", "0005_productrecord_system_kind_and_more"),
        ("reminders", "0006_reminder_scenarios"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE businesses_shop ALTER COLUMN payment_qr_key SET DEFAULT '';
                ALTER TABLE businesses_shop ALTER COLUMN payment_note SET DEFAULT '';
                ALTER TABLE businesses_shop ALTER COLUMN payment_message SET DEFAULT
                    'Заказ №{номер} · к оплате {сумма} сом. Пришлите, пожалуйста, скриншот оплаты';
                ALTER TABLE businesses_shop ALTER COLUMN payment_version SET DEFAULT 1;
                ALTER TABLE catalog_productrecord ALTER COLUMN system_kind SET DEFAULT '';
                ALTER TABLE customers_customerrecord ALTER COLUMN origin SET DEFAULT 'manual';
                ALTER TABLE orders_orderrecord ALTER COLUMN prepayment_percent SET DEFAULT 0;
                ALTER TABLE orders_orderrecord ALTER COLUMN prepayment_required SET DEFAULT 0;
                ALTER TABLE reminders_reminderrecord ALTER COLUMN occurrence_key SET DEFAULT '';
                ALTER TABLE reminders_remindersettings ALTER COLUMN min_days_between SET DEFAULT 7;
                ALTER TABLE reminders_remindersettings ALTER COLUMN scenarios_initialized SET DEFAULT false;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
