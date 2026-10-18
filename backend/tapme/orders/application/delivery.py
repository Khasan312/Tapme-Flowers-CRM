from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from tapme.shared.domain import InvalidInput


@dataclass(frozen=True)
class DeliverySlot:
    price: Decimal
    capacity: int
    occupied: int
    enforce: bool
    pickup_unlimited: bool
    configured: bool = True

    def quote(self, fulfillment: str) -> Decimal:
        if fulfillment == "pickup" and self.pickup_unlimited:
            return Decimal("0.00")
        if self.enforce and not self.configured:
            raise InvalidInput("Выберите одно из окон доставки магазина.")
        if self.enforce and self.occupied >= self.capacity:
            raise InvalidInput("Это окно уже заполнено. Выберите другое время.")
        return self.price if fulfillment == "courier" else Decimal("0.00")


class DeliverySlots(Protocol):
    def timezone(self, business_id: UUID) -> str: ...

    def lock(
        self, business_id: UUID, day: date, start: time, end: time, exclude_id: UUID | None = None
    ) -> DeliverySlot: ...
