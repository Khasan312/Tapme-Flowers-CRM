from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from tapme.shared.domain import money, text


@dataclass(frozen=True)
class Product:
    id: UUID
    business_id: UUID
    name: str
    price: Decimal
    version: int = 1
    active: bool = True
    photo_key: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", text(self.name, "Название", 200))
        object.__setattr__(self, "price", money(self.price))
