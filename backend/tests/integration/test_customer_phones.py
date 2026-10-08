from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from rest_framework.test import APIClient

from tapme.customers.models import CustomerRecord

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(transaction=True)
def test_concurrent_primary_and_additional_phone_collision(setup, base):
    barrier = Barrier(2)

    def submit(index):
        close_old_connections()
        try:
            client = APIClient()
            client.force_authenticate(setup["owner"])
            barrier.wait(timeout=10)
            return client.post(
                base + "/customers/",
                {
                    "name": f"Конкурент {index}",
                    "phone": "+996700800001" if index else "+996700800002",
                    "additional_phones": [] if index else ["+996700800001"],
                },
                format="json",
            ).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, range(2))) == [201, 409]


def create(setup, base, **overrides):
    return setup["client"].post(
        base + "/customers/",
        {
            "name": "Иван Иванов",
            "phone": "0555800001",
            "additional_phones": ["0312123456", "+996555800001", "+996312123456", ""],
            **overrides,
        },
        format="json",
    )


def test_multiple_numbers_normalized_deduplicated_and_searchable(setup, base):
    response = create(setup, base)
    assert response.status_code == 201, response.data
    customer = response.json()
    assert customer["phone"] == "+996555800001"
    assert customer["additional_phones"] == ["+996312123456"]
    for endpoint in ["customers", "customers/directory"]:
        for search in ["+996 (312) 123-456", "312123456", "Иван Иванов"]:
            rows = setup["client"].get(base + f"/{endpoint}/", {"search": search}).json()
            assert rows["count"] == 1
            assert rows["results"][0]["id"] == customer["id"]
            assert rows["results"][0]["additional_phones"] == ["+996312123456"]


@pytest.mark.parametrize(
    "phone,additional",
    [
        ("+996312123456", []),
        ("+996700800002", ["+996555800001"]),
        ("+996700800002", ["+996312123456"]),
    ],
)
def test_any_phone_collision_rejected_on_create_and_edit(setup, base, phone, additional):
    assert create(setup, base).status_code == 201
    initial = CustomerRecord.objects.count()
    result = create(setup, base, phone=phone, additional_phones=additional)
    assert result.status_code == 409, result.data
    assert CustomerRecord.objects.count() == initial
    url = base + f"/customers/{setup['customer'].id}/"
    profile = setup["client"].get(url).json()
    profile.pop("id")
    profile.update(phone=phone, additional_phones=additional)
    assert setup["client"].put(url, profile, format="json").status_code == 409
    setup["customer"].refresh_from_db()
    assert setup["customer"].additional_phones == []


def test_primary_swap_removal_and_legacy_edit_preserve_phones(setup, base):
    customer = create(setup, base).json()
    url = base + f"/customers/{customer['id']}/"
    profile = setup["client"].get(url).json()
    profile.pop("id")
    profile.pop("additional_phones")
    profile["notes"] = "Старая версия клиента"
    response = setup["client"].put(url, profile, format="json")
    assert response.status_code == 200, response.data
    assert response.json()["additional_phones"] == ["+996312123456"]
    profile.update(
        version=response.json()["version"],
        phone="+996312123456",
        additional_phones=["+996555800001"],
    )
    response = setup["client"].put(url, profile, format="json")
    assert response.status_code == 200
    assert response.json()["additional_phones"] == ["+996555800001"]
    profile.update(version=response.json()["version"], additional_phones=[])
    assert setup["client"].put(url, profile, format="json").status_code == 200
    assert create(setup, base, additional_phones=[]).status_code == 201


def test_additional_phone_limits_validation_and_isolation(setup, base):
    assert create(setup, base, additional_phones=["incorrect"]).status_code == 400
    assert (
        create(setup, base, additional_phones=[f"+996700800{i:03}" for i in range(10)]).status_code
        == 400
    )
    CustomerRecord.objects.create(
        business=setup["other_business"],
        name="Чужой",
        phone="+996555800001",
        additional_phones=["+996312123456"],
    )
    assert create(setup, base).status_code == 201
    setup["client"].force_login(setup["florist"])
    assert create(setup, base).status_code == 403


def test_vcf_one_contact_all_categories_no_duplicate_numbers(setup, base):
    vcf = b"BEGIN:VCARD\nVERSION:3.0\nFN:Ivan\nN:Ivanov;Ivan;;;\nTEL;TYPE=CELL:\nTEL;TYPE=HOME:+996312123456\nTEL;TYPE=WORK:0312123456\nitem1.TEL;TYPE=CELL:0555800001\nEND:VCARD\n"
    result = setup["client"].post(
        base + "/customers/import/",
        {
            "file": SimpleUploadedFile("contacts.vcf", vcf),
            "commit": "true",
        },
        format="multipart",
    )
    assert result.status_code == 200, result.data
    assert result.json()["created"] == 1
    row = CustomerRecord.objects.get(business=setup["business"], name="Ivan Ivanov")
    assert row.phone == "+996312123456"
    assert row.additional_phones == ["+996555800001"]
    duplicate = setup["client"].post(
        base + "/customers/import/",
        {
            "file": SimpleUploadedFile("new.csv", b"name,phone\nDuplicate,0555800001\n"),
            "commit": "true",
        },
        format="multipart",
    )
    assert duplicate.json()["created"] == 0
    assert duplicate.json()["results"][0]["status"] == "duplicate"


@pytest.mark.parametrize("kind", ["csv", "xlsx"])
def test_export_import_roundtrip_preserves_every_phone(setup, base, kind):
    assert create(setup, base).status_code == 201
    content = setup["client"].get(base + "/customers/export/", {"kind": kind}).content
    setup["client"].force_login(setup["other_owner"])
    other = f"/api/v1/businesses/{setup['other_business'].id}"
    response = setup["client"].post(
        other + "/customers/import/",
        {
            "file": SimpleUploadedFile(f"contacts.{kind}", content),
            "commit": "true",
        },
        format="multipart",
    )
    assert response.status_code == 200, response.data
    row = CustomerRecord.objects.get(business=setup["other_business"], name="Иван Иванов")
    assert row.phone == "+996555800001"
    assert row.additional_phones == ["+996312123456"]
