import django.db.models.deletion
from django.db import migrations, models


def populate(apps, schema_editor):
    Shop = apps.get_model("businesses", "Shop")
    Order = apps.get_model("orders", "OrderRecord")
    Membership = apps.get_model("businesses", "Membership")
    MembershipPoint = apps.get_model("businesses", "MembershipPoint")
    for shop in Shop.objects.filter(is_primary=True).iterator():
        Order.objects.filter(business_id=shop.business_id, point_id=None).update(point_id=shop.id)
        for member in Membership.objects.filter(
            business_id=shop.business_id, role__in=["florist", "courier"]
        ):
            MembershipPoint.objects.get_or_create(membership_id=member.id, point_id=shop.id)


class Migration(migrations.Migration):
    dependencies = [("orders", "0009_officetask_point_orderrecord_point")]
    operations = [
        migrations.RunPython(populate, migrations.RunPython.noop),
        # Previous releases omit point_id. Keep their single-point inserts valid;
        # the NOT NULL constraint still rejects ambiguous multi-point inserts.
        migrations.RunSQL(
            """
            CREATE FUNCTION tapme_default_order_point() RETURNS trigger AS $$
            BEGIN
                IF NEW.point_id IS NULL THEN
                    SELECT id INTO NEW.point_id FROM businesses_shop
                    WHERE business_id = NEW.business_id AND active
                    AND (SELECT count(*) FROM businesses_shop WHERE business_id = NEW.business_id AND active) = 1;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER tapme_order_point_insert BEFORE INSERT ON orders_orderrecord
            FOR EACH ROW EXECUTE FUNCTION tapme_default_order_point();
        """,
            "DROP TRIGGER IF EXISTS tapme_order_point_insert ON orders_orderrecord; DROP FUNCTION IF EXISTS tapme_default_order_point();",
        ),
        migrations.AlterField(
            model_name="orderrecord",
            name="point",
            field=models.ForeignKey(
                to="businesses.shop", on_delete=django.db.models.deletion.PROTECT
            ),
        ),
    ]
