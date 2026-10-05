from django.db import migrations, models


def populate(apps, schema_editor):
    Customer = apps.get_model("customers", "CustomerRecord")
    Counter = apps.get_model("customers", "CustomerCounter")
    for business_id in Customer.objects.values_list("business_id", flat=True).distinct():
        value = 100000
        for customer in Customer.objects.filter(business_id=business_id).order_by(
            "created_at", "id"
        ):
            value += 1
            Customer.objects.filter(id=customer.id).update(code=value)
        Counter.objects.update_or_create(business_id=business_id, defaults={"value": value})


class Migration(migrations.Migration):
    dependencies = [("customers", "0003_customercounter_customerrecord_code_and_more")]
    operations = [
        migrations.RunPython(populate, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="customerrecord",
            constraint=models.UniqueConstraint(
                fields=["business", "code"], name="unique_customer_code_per_business"
            ),
        ),
    ]
