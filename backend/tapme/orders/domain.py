from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from tapme.shared.domain import InvalidInput, money, phone, text


class Fulfillment(StrEnum):
    PICKUP = "pickup"
    COURIER = "courier"


@dataclass(frozen=True)
class OrderLine:
    product_id: UUID
    name: str
    unit_price: Decimal
    quantity: int

    def __post_init__(self) -> None:
        if type(self.quantity) is not int or not 1 <= self.quantity <= 999:
            raise InvalidInput("Количество должно быть целым числом от 1 до 999.")
        money(self.unit_price)
        money(self.total)

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass(frozen=True)
class Order:
    id: UUID
    business_id: UUID
    number: int
    customer_id: UUID
    customer_name: str
    customer_phone: str
    recipient_name: str
    recipient_phone: str
    fulfillment: Fulfillment
    delivery_date: date
    window_start: time
    window_end: time
    address: str
    notes: str
    card: str
    lines: tuple[OrderLine, ...]
    created_by: UUID
    created_at: datetime
    request_key: UUID
    request_hash: str
    status: str = "new"
    version: int = 1
    florist_id: UUID | None = None
    courier_id: UUID | None = None
    completed_at: datetime | None = None
    cancellation_reason: str = ""
    delivery_issue: str = ""
    occasion: str = ""
    source: str = ""
    relation: str = ""
    delivery_fee: Decimal = Decimal("0.00")
    paid_amount: Decimal = Decimal("0.00")
    prepayment_percent: int = 0
    prepayment_required: Decimal = Decimal("0.00")
    payment_due_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.fulfillment not in (Fulfillment.PICKUP, Fulfillment.COURIER):
            raise InvalidInput("Неизвестный способ получения заказа.")
        if not 1 <= len(self.lines) <= 50:
            raise InvalidInput("Добавьте от 1 до 50 позиций в заказ.")
        if len({line.product_id for line in self.lines}) != len(self.lines):
            raise InvalidInput("Товар повторяется. Измените количество в одной позиции.")
        if self.window_start >= self.window_end:
            raise InvalidInput("Конец окна должен быть позже начала.")
        object.__setattr__(self, "recipient_name", text(self.recipient_name, "Получатель", 150))
        object.__setattr__(self, "recipient_phone", phone(self.recipient_phone, required=False))
        object.__setattr__(
            self,
            "address",
            text(self.address, "Адрес", 500, required=self.fulfillment == Fulfillment.COURIER),
        )
        object.__setattr__(self, "notes", text(self.notes, "Заметка", 2000, required=False))
        object.__setattr__(self, "card", text(self.card, "Открытка", 1000, required=False))
        text(self.occasion, "Повод", 100, required=False)
        text(self.source, "Источник", 80, required=False)
        text(self.relation, "Кем приходится", 80, required=False)
        money(self.total)

    def check_transition(self, target: str, reason: str = "") -> None:
        transitions = {
            "pending": {"new", "cancelled"},
            "new": {"work", "cancelled"},
            "work": {"ready", "cancelled"},
            "ready": {"route", "done", "cancelled"},
            "route": {"done", "cancelled"},
            "done": set(),
            "cancelled": set(),
        }
        if target not in transitions.get(self.status, set()):
            raise InvalidInput("Этот переход статуса недоступен. Обновите заказ.")
        if target in {"work", "ready"} and not self.florist_id:
            raise InvalidInput("Сначала назначьте флориста.")
        if target == "route" and (self.fulfillment != Fulfillment.COURIER or not self.courier_id):
            raise InvalidInput("Для отправки назначьте курьера и выберите доставку.")
        if target == "done" and self.fulfillment == Fulfillment.COURIER and self.status != "route":
            raise InvalidInput("Сначала передайте заказ курьеру.")
        if target == "cancelled":
            text(reason, "Причина отмены", 1000)

    @property
    def total(self) -> Decimal:
        money(self.delivery_fee)
        return sum((line.total for line in self.lines), start=self.delivery_fee)
