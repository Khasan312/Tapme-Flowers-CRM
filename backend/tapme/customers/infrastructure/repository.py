import re
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Q, TextField
from django.db.models.functions import Cast

from tapme.businesses.models import Business
from tapme.customers.domain import Customer
from tapme.customers.models import CustomerRecord
from tapme.shared.domain import Conflict, NotFound, Page


def to_domain(row):
    return Customer(
        row.id,
        row.business_id,
        row.name,
        row.phone,
        row.notes,
        row.consent,
        row.source,
        tuple(row.tags),
        tuple(row.additional_phones),
    )


def matching_phones(business_id, phones):
    match = Q(phone__in=phones)
    for number in phones:
        match |= Q(additional_phones__contains=[number])
    return CustomerRecord.objects.filter(business_id=business_id).filter(match)


def lock_customer_phones(customer):
    # All API creates/edits take this lock before checking primary and additional phones.
    Business.objects.select_for_update().get(id=customer.business_id)
    if matching_phones(customer.business_id, customer.phones).exclude(id=customer.id).exists():
        raise Conflict("Клиент с одним из этих телефонов уже существует.")


class DjangoCustomerRepository:
    def get(self, business_id, customer_id):
        row = CustomerRecord.objects.filter(business_id=business_id, id=customer_id).first()
        if row is None:
            raise NotFound("Клиент не найден.")
        return to_domain(row)

    def add(self, customer):
        try:
            with transaction.atomic():
                lock_customer_phones(customer)
                CustomerRecord.objects.create(
                    id=customer.id,
                    business_id=customer.business_id,
                    name=customer.name,
                    phone=customer.phone,
                    notes=customer.notes,
                    consent=customer.consent,
                    source=customer.source,
                    tags=list(customer.tags),
                    additional_phones=list(customer.additional_phones),
                )
        except IntegrityError:
            if CustomerRecord.objects.filter(
                business_id=customer.business_id, phone=customer.phone
            ).exists():
                raise Conflict("Клиент с этим телефоном уже существует.") from None
            raise
        return customer

    def has_phone(self, business_id, phones):
        return matching_phones(business_id, phones).exists()

    def search(self, business_id, search):
        query = CustomerRecord.objects.filter(business_id=business_id).alias(
            other_phones=Cast("additional_phones", TextField())
        )
        if search:
            match = (
                Q(name__icontains=search)
                | Q(phone__icontains=search)
                | Q(other_phones__icontains=search)
                | Q(recipients__name__icontains=search)
                | Q(recipients__phone__icontains=search)
            )
            if search.isdigit():
                match |= Q(code=int(search))
            digits = re.sub(r"\D", "", search)
            if len(digits) >= 3:
                match |= (
                    Q(phone__contains=digits)
                    | Q(other_phones__contains=digits)
                    | Q(recipients__phone__contains=digits)
                )
            try:
                match |= Q(id=UUID(search)) | Q(recipients__id=UUID(search))
            except ValueError:
                pass
            query = query.filter(match).distinct()
        return query

    def list(self, business_id, search, limit, offset):
        query = self.search(business_id, search).order_by("name", "id")
        return Page(tuple(to_domain(r) for r in query[offset : offset + limit]), query.count())
