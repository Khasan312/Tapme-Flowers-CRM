import uuid

from django.db import models, transaction


class CustomerCounter(models.Model):
    business = models.OneToOneField(
        "businesses.Business", primary_key=True, on_delete=models.CASCADE
    )
    value = models.PositiveIntegerField(default=100000)


class CustomerRecord(models.Model):
    code = models.PositiveIntegerField(default=0, editable=False)
    source = models.CharField(max_length=80, blank=True)
    tags = models.JSONField(default=list)

    def save(self, *args, **kwargs):
        if not self.code:
            from tapme.businesses.models import Business

            with transaction.atomic():
                Business.objects.select_for_update().get(id=self.business_id)
                counter, _ = CustomerCounter.objects.get_or_create(business_id=self.business_id)
                counter.value += 1
                counter.save(update_fields=["value"])
                self.code = counter.value
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    version = models.PositiveIntegerField(default=1)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=16)
    notes = models.TextField(blank=True)
    consent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business", "code"], name="unique_customer_code_per_business"
            ),
            models.UniqueConstraint(
                fields=["business", "phone"], name="unique_customer_phone_per_business"
            ),
        ]
        indexes = [models.Index(fields=["business", "name", "id"])]


class RecipientRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        CustomerRecord, on_delete=models.CASCADE, related_name="recipients"
    )
    name = models.CharField(max_length=150)
    relation = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)


class ImportantDateRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(CustomerRecord, on_delete=models.CASCADE, related_name="dates")
    label = models.CharField(max_length=150)
    person = models.CharField(max_length=150)
    month = models.PositiveSmallIntegerField()
    day = models.PositiveSmallIntegerField()
