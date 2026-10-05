from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from tapme.shared.domain import InvalidInput, money, text


@dataclass(frozen=True)
class Payment:
    id: UUID
    business_id: UUID
    order_id: UUID
    amount: Decimal
    kind: str
    method: str
    note: str
    actor_id: UUID
    created_at: datetime
    request_key: UUID
    request_hash: str

    def __post_init__(self) -> None:
        money(self.amount)
        if self.amount <= 0:
            raise InvalidInput("Сумма должна быть больше нуля.")
        if self.kind not in {"payment", "refund"}:
            raise InvalidInput("Неизвестный вид операции.")
        if self.method not in {"cash", "transfer", "card"}:
            raise InvalidInput("Выберите способ оплаты.")
        text(self.note, "Комментарий", 1000, required=self.kind == "refund")

    def check_balance(self, balance: Decimal, total: Decimal, cancelled: bool) -> None:
        if self.kind == "refund" and self.amount > balance:
            raise InvalidInput("Возврат превышает полученную оплату.")
        if self.kind == "payment" and (cancelled or self.amount + balance > total):
            raise InvalidInput("Оплата превышает остаток либо заказ отменён.")
