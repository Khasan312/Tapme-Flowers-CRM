import re
from dataclasses import dataclass
from decimal import Decimal


class BusinessError(Exception):
    """Errors crossing the application boundary never expose database details."""


class InvalidInput(BusinessError):
    pass


class Forbidden(BusinessError):
    pass


class NotFound(BusinessError):
    pass


class Conflict(BusinessError):
    pass


@dataclass(frozen=True)
class Page[T]:
    results: tuple[T, ...]
    count: int


def text(value: str, label: str, limit: int, *, required: bool = True) -> str:
    value = value.strip()
    if (required and not value) or len(value) > limit:
        raise InvalidInput(f"{label}: заполните поле, максимум {limit} символов.")
    return value


def phone(value: str, *, required: bool = True) -> str:
    value = re.sub(r"[\s()\-]", "", value)
    if value in {"", "+996"} and not required:
        return ""
    if re.fullmatch(r"[1-9][0-9]{8}", value):
        value = "+996" + value
    elif re.fullmatch(r"0[1-9][0-9]{8}", value):
        value = "+996" + value[1:]
    elif re.fullmatch(r"996[1-9][0-9]{8}", value):
        value = "+" + value
    elif re.fullmatch(r"\+9960[1-9][0-9]{8}", value):
        value = "+996" + value[5:]
    if value.startswith("+996"):
        if not re.fullmatch(r"\+996[1-9][0-9]{8}", value):
            raise InvalidInput("Введите 9 цифр номера после +996, например 555 123 456.")
    elif not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
        raise InvalidInput("Проверьте номер телефона, например 555 123 456.")
    return value


def money(value: Decimal) -> Decimal:
    if not value.is_finite() or value < 0 or value > Decimal("9999999999.99"):
        raise InvalidInput("Сумма должна быть от 0 до 9 999 999 999,99.")
    if value != value.quantize(Decimal("0.01")):
        raise InvalidInput("Сумма не может содержать больше двух знаков после запятой.")
    return value.quantize(Decimal("0.01"))


def page_bounds(limit: int, offset: int) -> None:
    if not 1 <= limit <= 100 or offset < 0:
        raise InvalidInput("Некорректные параметры страницы.")
