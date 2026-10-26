import re
from datetime import date, datetime, time, timedelta, tzinfo
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from tapme.shared.domain import InvalidInput, money, phone, text

TEXT_FIELDS = {
    "occasion": 100,
    "requested_time_text": 100,
    "address": 400,
    "address_details": 90,
    "recipient_name": 150,
    "recipient_phone": 40,
    "card_text": 1000,
    "notes": 1700,
}


def recipient_phone_is_empty(value: str) -> bool:
    # Clearing the input can leave formatting or the default country code only.
    return re.sub(r"[\s()+\-]", "", value) in {"", "996"}


def normalize_fields(raw: dict[str, Any]) -> dict[str, Any]:
    if set(raw) - (set(TEXT_FIELDS) | {"items", "fulfillment", "date", "window", "point_id"}):
        raise InvalidInput("Неизвестное поле черновика.")
    result: dict[str, Any] = {}
    point_id = raw.get("point_id", "")
    try:
        result["point_id"] = str(UUID(str(point_id))) if point_id else ""
    except (ValueError, TypeError):
        raise InvalidInput("Выберите точку из списка.") from None
    for key, size in TEXT_FIELDS.items():
        value = raw.get(key, "")
        if not isinstance(value, str):
            raise InvalidInput("Поля черновика должны содержать текст.")
        result[key] = text(value, key, size, required=False)
    if recipient_phone_is_empty(result["recipient_phone"]):
        result["recipient_phone"] = ""
    else:
        try:
            result["recipient_phone"] = phone(result["recipient_phone"], required=False)
        except InvalidInput:
            pass  # Incomplete contact details may be saved; conversion validates them.
    result["fulfillment"] = raw.get("fulfillment", "courier")
    if not isinstance(result["fulfillment"], str) or result["fulfillment"] not in {
        "courier",
        "pickup",
    }:
        raise InvalidInput("Выберите доставку или самовывоз.")
    result["date"] = raw.get("date", "")
    if not isinstance(result["date"], str):
        raise InvalidInput("Проверьте дату получения.")
    window = raw.get("window", {"start": "", "end": ""})
    if (
        not isinstance(window, dict)
        or set(window) != {"start", "end"}
        or any(not isinstance(value, str) for value in window.values())
    ):
        raise InvalidInput("Укажите начало и конец окна.")
    try:
        if result["date"]:
            result["date"] = date.fromisoformat(result["date"]).isoformat()
        result["window"] = {
            k: time.fromisoformat(v).strftime("%H:%M") if v else "" for k, v in window.items()
        }
    except (TypeError, ValueError):
        raise InvalidInput("Проверьте дату и время получения.") from None
    if all(result["window"].values()) and result["window"]["start"] >= result["window"]["end"]:
        raise InvalidInput("Конец окна должен быть позже начала.")
    items = raw.get("items", [])
    if not isinstance(items, list) or len(items) > 50:
        raise InvalidInput("В черновике может быть до 50 позиций.")
    cleaned, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise InvalidInput("Некорректная позиция черновика.")
        if item.get("kind") == "product":
            if set(item) != {"kind", "product_id", "quantity"}:
                raise InvalidInput("Цена позиции определяется прайсом магазина.")
            try:
                product_id = str(UUID(str(item["product_id"])))
            except ValueError:
                raise InvalidInput("Выберите позицию из прайса.") from None
            quantity = item["quantity"]
            if type(quantity) is not int or not 1 <= quantity <= 999:
                raise InvalidInput("Количество: от 1 до 999.")
            key = product_id
            cleaned.append({"kind": "product", "product_id": product_id, "quantity": quantity})
        elif item.get("kind") == "budget":
            if set(item) != {"kind", "amount", "description"}:
                raise InvalidInput("Укажите бюджет и описание букета.")
            try:
                amount = money(Decimal(str(item["amount"])))
            except (InvalidOperation, ValueError, InvalidInput):
                raise InvalidInput("Проверьте сумму бюджета.") from None
            if amount <= 0:
                raise InvalidInput("Бюджет должен быть больше нуля.")
            if not isinstance(item["description"], str):
                raise InvalidInput("Введите описание букета.")
            cleaned.append(
                {
                    "kind": "budget",
                    "amount": str(amount),
                    "description": text(item["description"], "Описание", 150, required=False),
                }
            )
            key = "budget"
        else:
            raise InvalidInput("Выберите позицию прайса или букет по бюджету.")
        if key in seen:
            raise InvalidInput("Позиция повторяется. Измените количество.")
        seen.add(key)
    result["items"] = cleaned
    return result


def missing_fields(fields: dict[str, Any]) -> list[str]:
    missing = []
    if not fields["items"]:
        missing.append("Состав заказа")
    if not fields["date"]:
        missing.append("Дата получения")
    if not all(fields["window"].values()):
        missing.append("Окно получения")
    if not fields["recipient_name"]:
        missing.append("Имя получателя")
    if fields["fulfillment"] == "courier":
        if not fields["address"]:
            missing.append("Адрес доставки")
        if not fields["recipient_phone"]:
            missing.append("Телефон получателя")
    if fields["recipient_phone"]:
        try:
            phone(fields["recipient_phone"])
        except InvalidInput:
            missing.append("Корректный телефон получателя")
    return missing


def receiving_at(day: date, start: time, zone: tzinfo | None) -> datetime:
    return datetime.combine(day, start, tzinfo=zone)


def payment_deadline(
    now: datetime, receiving: datetime, override: datetime | None = None
) -> datetime:
    if override is not None:
        if override.tzinfo is None or not now < override < receiving:
            raise InvalidInput("Срок оплаты должен быть в будущем и до начала получения.")
        return override
    due = min(now + timedelta(minutes=60), receiving - timedelta(hours=2))
    if due <= now:
        raise InvalidInput(
            "Срочный заказ: укажите будущий срок оплаты до получения или подтвердите без предоплаты с причиной."
        )
    return due
