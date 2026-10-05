from dataclasses import dataclass
from uuid import UUID

from tapme.shared.domain import phone, text


@dataclass(frozen=True)
class Customer:
    id: UUID
    business_id: UUID
    name: str
    phone: str
    notes: str = ""
    consent: bool = False
    source: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        from tapme.shared.domain import InvalidInput

        object.__setattr__(self, "source", text(self.source, "Источник", 80, required=False))
        object.__setattr__(self, "tags", tuple(self.tags))
        if len(self.tags) > 10 or any(not 1 <= len(tag) <= 40 for tag in self.tags):
            raise InvalidInput("Не более 10 меток длиной до 40 символов.")

        object.__setattr__(self, "name", text(self.name, "Имя", 150))
        object.__setattr__(self, "phone", phone(self.phone))
        object.__setattr__(self, "notes", text(self.notes, "Заметка", 2000, required=False))


@dataclass(frozen=True)
class Recipient:
    id: UUID
    name: str
    relation: str
    phone: str
    address: str
    notes: str

    def validate(self) -> None:
        text(self.name, "Имя получателя", 150)
        text(self.relation, "Кем приходится", 80, required=False)
        phone(self.phone, required=False)
        text(self.address, "Адрес", 500, required=False)
        text(self.notes, "Заметка", 2000, required=False)


@dataclass(frozen=True)
class ImportantDate:
    id: UUID
    label: str
    person: str
    month: int
    day: int

    def validate(self) -> None:
        from datetime import date

        from tapme.shared.domain import InvalidInput

        text(self.label, "Событие", 150)
        text(self.person, "У кого", 150)
        try:
            date(2000, self.month, self.day)
        except ValueError:
            raise InvalidInput("Некорректная дата.") from None
