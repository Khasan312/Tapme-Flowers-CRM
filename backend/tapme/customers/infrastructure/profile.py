from dataclasses import asdict

from django.db import IntegrityError, transaction

from tapme.customers.infrastructure.repository import DjangoCustomerRepository, lock_customer_phones
from tapme.customers.models import CustomerRecord, ImportantDateRecord, RecipientRecord
from tapme.shared.domain import Conflict, NotFound


class DjangoProfileRepository:
    def get(self, business_id, customer_id):
        customer = DjangoCustomerRepository().get(business_id, customer_id)
        row = CustomerRecord.objects.get(business_id=business_id, id=customer_id)
        return dict(
            **asdict(customer),
            version=row.version,
            code=row.code,
            created_at=row.created_at,
            recipients=list(
                row.recipients.order_by("name").values(
                    "id", "name", "relation", "phone", "address", "notes"
                )
            ),
            dates=list(
                row.dates.order_by("month", "day").values("id", "label", "person", "month", "day")
            ),
        )

    def save(self, customer, version, recipients, dates):
        try:
            with transaction.atomic():
                lock_customer_phones(customer)
                row = (
                    CustomerRecord.objects.select_for_update()
                    .filter(id=customer.id, business_id=customer.business_id)
                    .first()
                )
                if row is None:
                    raise NotFound("Клиент не найден.")
                if row.version != version:
                    raise Conflict("Карточку уже изменили. Обновите её.")
                for field in (
                    "name",
                    "phone",
                    "notes",
                    "consent",
                    "source",
                    "tags",
                    "additional_phones",
                ):
                    setattr(row, field, getattr(customer, field))
                row.version += 1
                row.save()
                for model, entries in ((RecipientRecord, recipients), (ImportantDateRecord, dates)):
                    existing = set(model.objects.filter(customer=row).values_list("id", flat=True))
                    # An identifier owned by another customer must never be reassigned.
                    for entry in entries:
                        if entry.id not in existing and model.objects.filter(id=entry.id).exists():
                            raise NotFound("Запись карточки не найдена.")
                    model.objects.filter(customer=row).exclude(
                        id__in=[e.id for e in entries]
                    ).delete()
                    for entry in entries:
                        values = asdict(entry)
                        entry_id = values.pop("id")
                        model.objects.update_or_create(id=entry_id, customer=row, defaults=values)
        except IntegrityError:
            raise Conflict("Клиент с этим телефоном уже существует.") from None
        return self.get(customer.business_id, customer.id)
