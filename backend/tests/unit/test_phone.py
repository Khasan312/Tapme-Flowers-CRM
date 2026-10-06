import pytest

from tapme.shared.domain import InvalidInput, phone


@pytest.mark.parametrize(
    "value",
    [
        "555123456",
        "0555123456",
        "555 12-34-56",
        "996555123456",
        "+996 (555) 123-456",
        "+9960555123456",
    ],
)
def test_local_numbers_get_kyrgyz_country_code(value):
    assert phone(value) == "+996555123456"


@pytest.mark.parametrize("value", ["+12025550100", "+77011234567", "+447700900123"])
def test_international_numbers_keep_their_country(value):
    assert phone(value) == value


@pytest.mark.parametrize("value", ["", "+996"])
def test_optional_phone_can_be_left_empty(value):
    assert phone(value, required=False) == ""
    with pytest.raises(InvalidInput):
        phone(value)


@pytest.mark.parametrize(
    "value",
    [
        "abc",
        "55512345",
        "5551234567",
        "+99655512345",
        "+9965551234567",
        "+996000000000",
        "555123456доб123",
        "++996555123456",
    ],
)
def test_malformed_or_incomplete_phone_is_still_rejected(value):
    with pytest.raises(InvalidInput):
        phone(value)
