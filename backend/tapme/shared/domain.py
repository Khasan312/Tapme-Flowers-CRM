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
    if not value and not required:
        return ""
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
        raise InvalidInput("Телефон должен содержать код страны, например +996555123456.")
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
