from uuid import uuid4

import pytest

from tapme.businesses.models import Membership, Shop
from tapme.customers.models import CustomerRecord
from tapme.orders.models import OrderRecord

pytestmark = pytest.mark.django_db


def test_local_phones_normalized_in_shop_staff_customer_recipient_and_order(setup, base, payload):
    client = setup["client"]
    settings_url = base + "/settings/"
    settings = client.get(settings_url).json()
    result = client.put(
        settings_url, {**settings, "phone": "0555 222 333", "whatsapp": "700222333"}, format="json"
    )
    assert result.status_code == 200, result.data
    shop = Shop.objects.get(business=setup["business"])
    assert (shop.phone, shop.whatsapp) == ("+996555222333", "+996700222333")
    result = client.put(
        base + f"/staff/{setup['florist'].id}/",
        {"role": "florist", "is_active": True, "staff_phone": "555 222 333"},
        format="json",
    )
    assert result.status_code == 204
    assert (
        Membership.objects.get(business=setup["business"], user=setup["florist"]).phone
        == "+996555222333"
    )
    result = client.post(
        base + "/customers/", {"name": "Новый", "phone": "555 222 333"}, format="json"
    )
    assert result.status_code == 201
    assert CustomerRecord.objects.get(id=result.json()["id"]).phone == "+996555222333"
    duplicate = client.post(
        base + "/customers/", {"name": "Повтор", "phone": "+996555222333"}, format="json"
    )
    assert duplicate.status_code == 409
    profile_url = base + f"/customers/{setup['customer'].id}/"
    profile = client.get(profile_url).json()
    profile.pop("id")
    profile["recipients"] = [
        {"name": "Мама", "relation": "", "phone": "0700222333", "address": "", "notes": ""}
    ]
    result = client.put(profile_url, profile, format="json")
    assert result.status_code == 200, result.data
    assert client.get(profile_url).json()["recipients"][0]["phone"] == "+996700222333"
    for recipient_phone, expected in [("555222333", "+996555222333"), ("+996", "")]:
        result = client.post(
            base + "/orders/",
            {**payload, "recipient_phone": recipient_phone},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        )
        assert result.status_code == 201, result.data
        assert OrderRecord.objects.get(id=result.json()["id"]).recipient_phone == expected


def test_custom_templates_persist_edit_remove_and_do_not_affect_defaults(setup, base):
    client = setup["client"]
    url = base + "/reminder-rules/"
    rules = client.get(url).json()
    assert rules["custom_templates"] == []
    custom = {
        "id": str(uuid4()),
        "name": "Спасибо за заказ",
        "text": "{имя}, спасибо! Ваш {магазин}.",
    }
    result = client.put(url, {**rules, "custom_templates": [custom]}, format="json")
    assert result.status_code == 200, result.data
    assert client.get(url).json() == {
        **rules,
        "custom_templates": [custom],
        "version": rules["version"] + 1,
    }
    rules = result.json()
    # Editing rules from a client that does not know the new field preserves messages.
    rules.pop("custom_templates")
    assert client.put(url, rules, format="json").status_code == 200
    assert client.get(url).json()["custom_templates"] == [custom]
    rules = client.get(url).json()
    custom["text"] = "{имя}, забрать заказ №{номер} можно завтра."
    assert (
        client.put(url, {**rules, "custom_templates": [custom]}, format="json").status_code == 200
    )
    assert client.get(url).json()["custom_templates"][0]["text"] == custom["text"]
    rules = client.get(url).json()
    assert client.put(url, {**rules, "custom_templates": []}, format="json").status_code == 200
    assert client.get(url).json()["custom_templates"] == []


def test_custom_templates_owner_permissions_and_shop_isolation(setup, base):
    client = setup["client"]
    url = base + "/reminder-rules/"
    rules = client.get(url).json()
    rules["custom_templates"] = [
        {"id": str(uuid4()), "name": "Мой шаблон", "text": "Здравствуйте, {имя}!"}
    ]
    assert client.put(url, rules, format="json").status_code == 200
    client.force_login(setup["manager"])
    assert client.get(url).json()["custom_templates"] == rules["custom_templates"]
    assert client.put(url, rules, format="json").status_code == 403
    client.force_login(setup["other_owner"])
    assert client.get(url).status_code == 403
    assert client.put(url, rules, format="json").status_code == 403
    assert (
        client.get(f"/api/v1/businesses/{setup['other_business'].id}/reminder-rules/").json()[
            "custom_templates"
        ]
        == []
    )


@pytest.mark.parametrize(
    "change",
    [
        {"name": ""},
        {"name": " "},
        {"name": "я" * 101},
        {"text": ""},
        {"text": "я" * 2001},
        {"text": "{имя.__class__}"},
        {"text": "{unknown}"},
        {"text": "{имя:20000000}"},
        {"id": "wrong"},
    ],
)
def test_invalid_custom_templates_rejected_without_overwriting(setup, base, change):
    client = setup["client"]
    url = base + "/reminder-rules/"
    rules = client.get(url).json()
    template = {"id": str(uuid4()), "name": "Шаблон", "text": "Здравствуйте, {имя}!", **change}
    assert (
        client.put(url, {**rules, "custom_templates": [template]}, format="json").status_code == 400
    )
    assert client.get(url).json() == rules


def test_custom_template_count_and_duplicate_ids(setup, base):
    client = setup["client"]
    url = base + "/reminder-rules/"
    rules = client.get(url).json()
    templates = [{"id": str(uuid4()), "name": f"Текст {i}", "text": "Привет!"} for i in range(51)]
    for entries in (templates, [templates[0], templates[0]]):
        assert (
            client.put(url, {**rules, "custom_templates": entries}, format="json").status_code
            == 400
        )
