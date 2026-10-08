import quopri

import pytest

from tapme.customers.infrastructure.vcards import read_vcards
from tapme.shared.domain import InvalidInput


def card(body, version="3.0"):
    return f"BEGIN:VCARD\r\nVERSION:{version}\r\n{body}\r\nEND:VCARD\r\n"


@pytest.mark.parametrize("version", ["2.1", "3.0", "4.0"])
def test_phone_exports_with_multiple_numbers_and_escaped_text(version):
    content = card(
        "FN:Алия\\, мама\r\nN:Тест;Алия;;;\r\nTEL;TYPE=CELL:+996555111222\r\nitem1.TEL;TYPE=HOME:0700222333\r\nNOTE:Любит розы\\nБез лилий\r\nPHOTO;VALUE=URI:https://example.invalid/private.jpg",
        version,
    )
    assert read_vcards(content.encode()) == [
        dict(
            name="Алия Тест",
            phone="+996555111222",
            additional_phones=["0700222333"],
            notes="Любит розы\nБез лилий",
        ),
    ]


def test_folded_lines_uri_phone_and_name_fallback():
    content = card("FN:Очень длинное имя\r\n  клиента\r\nTEL;VALUE=uri:tel:%2B996555111222", "4.0")
    content += card("N:Иванов;Иван;;;\r\nTEL:+996700222333")
    content += card("ORG:Цветочная мастерская\r\nTEL:+996700222334")
    rows = read_vcards(content.encode())
    assert rows[0]["name"] == "Очень длинное имя клиента"
    assert rows[0]["phone"] == "+996555111222"
    assert rows[1]["name"] == "Иван Иванов"
    assert rows[2]["name"] == "Цветочная мастерская"


@pytest.mark.parametrize("charset", ["UTF-8", "Windows-1251"])
def test_old_android_quoted_printable_names(charset):
    encoded = quopri.encodestring("Александра Иванова".encode(charset)).decode("ascii")
    content = card(
        f"FN;CHARSET={charset};ENCODING=QUOTED-PRINTABLE:{encoded}\r\nTEL:0555111222", "2.1"
    )
    assert read_vcards(content.encode())[0]["name"] == "Александра Иванова"


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16"])
def test_export_with_bom(encoding):
    assert read_vcards(card("FN:Алия\r\nTEL:+996555111222").encode(encoding))[0]["name"] == "Алия"


def test_missing_fields_stay_in_preview_for_validation():
    rows = read_vcards((card("FN:Без телефона") + card("TEL:abc")).encode())
    assert rows == [
        dict(name="Без телефона", phone="", additional_phones=[], notes=""),
        dict(name="", phone="abc", additional_phones=[], notes=""),
    ]


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"not a vcard",
        b"BEGIN:VCARD\nVERSION:3.0\nFN:Broken",
        b"BEGIN:VCARD\nVERSION:99\nEND:VCARD",
        b"BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR",
        b"BEGIN:VCARD\nVERSION:3.0\nFN:\xff\nEND:VCARD",
        b"BEGIN:VCARD\nVERSION:3.0\nFN;CHARSET=invalid;ENCODING=QUOTED-PRINTABLE:=FF\nEND:VCARD",
    ],
)
def test_broken_or_unsupported_files_rejected(content):
    with pytest.raises(InvalidInput):
        read_vcards(content)


def test_number_limit_counts_multiple_phones():
    with pytest.raises(InvalidInput, match="1000"):
        read_vcards(
            card(
                "FN:Слишком много\r\n" + "\r\n".join(f"TEL:+996555{i:06}" for i in range(1001))
            ).encode()
        )


def test_structured_first_and_last_name_and_empty_phone_categories():
    rows = read_vcards(
        card(
            "FN:Иван\r\nN:Иванов;Иван;;;\r\nTEL;TYPE=CELL:\r\nTEL;TYPE=HOME:+996312123456\r\nTEL;TYPE=WORK:\r\nitem1.TEL:+996555123456"
        ).encode()
    )
    assert rows == [
        dict(
            name="Иван Иванов", phone="+996312123456", additional_phones=["+996555123456"], notes=""
        )
    ]


def test_formatted_name_retained_when_structured_name_empty():
    assert (
        read_vcards(card("FN:Иван Иванов\r\nN:;;;;\r\nTEL:0555123456").encode())[0]["name"]
        == "Иван Иванов"
    )
