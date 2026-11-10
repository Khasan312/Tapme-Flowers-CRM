import json
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from tapme.customers.models import CustomerRecord

pytestmark = pytest.mark.django_db

VCF = """BEGIN:VCARD
VERSION:3.0
FN:Первый контакт
TEL:0555111222
TEL:0700111222
NOTE:Заметка контакта
END:VCARD
BEGIN:VCARD
VERSION:4.0
FN:Второй контакт
TEL;VALUE=uri:tel:+996555222333
END:VCARD
BEGIN:VCARD
VERSION:2.1
FN:Без телефона
END:VCARD
""".encode()


def upload(setup, base, data=VCF, name="contacts.vcf", commit=False, selected=None):
    body = dict(file=SimpleUploadedFile(name, data), commit=str(commit).lower())
    if selected is not None:
        body["selected_rows"] = json.dumps(selected)
    return setup["client"].post(base + "/customers/import/", body, format="multipart")


def test_vcf_preview_selection_duplicates_and_no_consent(setup, base):
    initial = CustomerRecord.objects.count()
    preview = upload(setup, base)
    assert preview.status_code == 200, preview.data
    assert CustomerRecord.objects.count() == initial
    assert [r["status"] for r in preview.json()["results"]] == ["ready", "ready", "error"]
    assert preview.json()["results"][0]["additional_phones"] == ["+996700111222"]
    result = upload(setup, base, commit=True, selected=[2, 3])
    assert result.status_code == 200, result.data
    assert result.json()["created"] == 2
    assert [r["status"] for r in result.json()["results"]] == [
        "created",
        "created",
        "unselected",
    ]
    created = CustomerRecord.objects.filter(business=setup["business"]).exclude(
        id=setup["customer"].id
    )
    assert set(created.values_list("phone", flat=True)) == {"+996555111222", "+996555222333"}
    assert not created.filter(consent=True).exists()
    assert created.get(phone="+996555111222").notes == "Заметка контакта"
    assert created.get(phone="+996555111222").additional_phones == ["+996700111222"]
    assert upload(setup, base, commit=True, selected=[2, 3]).json()["created"] == 0
    assert CustomerRecord.objects.count() == initial + 2
    assert upload(setup, base, commit=True, selected=[]).json()["created"] == 0


@pytest.mark.parametrize(
    "selection", ["2", {"row": 2}, [True], [1], [999], [2, 2], [2, "3"], [[2]]]
)
def test_invalid_selection_never_creates_contacts(setup, base, selection):
    initial = CustomerRecord.objects.count()
    response = upload(setup, base, commit=True, selected=selection)
    assert response.status_code == 400, response.data
    assert CustomerRecord.objects.count() == initial


def test_unselected_duplicate_does_not_block_selected_phone(setup, base):
    data = b"name,phone\nFirst,0555111222\nSecond,+996555111222\n"
    response = upload(setup, base, data, "contacts.csv", True, [3])
    assert response.status_code == 200, response.data
    assert response.json()["created"] == 1
    assert (
        CustomerRecord.objects.get(phone="+996555111222", business=setup["business"]).name
        == "Second"
    )


def test_xlsx_selected_rows_and_legacy_import_without_selection(setup, base):
    workbook = Workbook()
    workbook.active.append(["name", "phone"])
    workbook.active.append(["Не выбран", "555111222"])
    workbook.active.append(["Выбран", "555222333"])
    content = BytesIO()
    workbook.save(content)
    workbook.close()
    response = upload(setup, base, content.getvalue(), "contacts.xlsx", True, [3])
    assert response.status_code == 200, response.data
    assert response.json()["created"] == 1
    # Existing clients can still import all validated rows without selected_rows.
    assert upload(setup, base, content.getvalue(), "contacts.xlsx", True).json()["created"] == 1


@pytest.mark.parametrize("coordinates", ["A1000000", "XFD3"])
@pytest.mark.parametrize("trustworthy_dimensions", [False, True])
def test_xlsx_import_rejects_sparse_rows_and_columns(
    setup, base, coordinates, trustworthy_dimensions
):
    workbook = Workbook()
    workbook.active.append(["name", "phone"])
    workbook.active.append(["Контакт", "555111222"])
    workbook.active[coordinates] = "x"
    source = BytesIO()
    workbook.save(source)
    workbook.close()
    if not trustworthy_dimensions:
        patched = BytesIO()
        with ZipFile(source) as original, ZipFile(patched, "w", ZIP_DEFLATED) as output:
            for name in original.namelist():
                data = original.read(name)
                if name == "xl/worksheets/sheet1.xml":
                    data = data.replace(
                        f'<dimension ref="A1:{coordinates}"'.encode(), b'<dimension ref="A1:B2"'
                    )
                output.writestr(name, data)
        source = patched
    response = upload(setup, base, source.getvalue(), "contacts.xlsx", True)
    assert response.status_code == 400
    assert not CustomerRecord.objects.filter(phone="+996555111222").exists()


def test_vcf_permissions_and_business_isolation(setup, base):
    CustomerRecord.objects.create(
        business=setup["other_business"], name="Другой магазин", phone="+996555111222"
    )
    setup["client"].force_login(setup["florist"])
    assert upload(setup, base).status_code == 403
    setup["client"].force_login(setup["other_owner"])
    assert upload(setup, base, commit=True).status_code == 403
    setup["client"].force_login(setup["manager"])
    assert upload(setup, base, commit=True, selected=[2]).json()["created"] == 1


@pytest.mark.parametrize(
    "data", [VCF + b"BEGIN:VCARD\nVERSION:3.0\nFN:Broken", b"x" * (2 * 1024 * 1024 + 1)]
)
def test_whole_file_validated_before_creating_any_contacts(setup, base, data):
    initial = CustomerRecord.objects.count()
    assert upload(setup, base, data=data, commit=True).status_code == 400
    assert CustomerRecord.objects.count() == initial
