"""Read contact exports without importing photos or following external URLs."""

from urllib.parse import unquote

import vobject
from vobject.base import VObjectError

from tapme.customers.application.transfers import CustomerImportRow
from tapme.shared.domain import InvalidInput


def read_vcards(data: bytes) -> list[CustomerImportRow]:
    try:
        content = data.decode(
            "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        )
        rows = []
        number_count = 0
        for card in vobject.readComponents(content, allowQP=True):
            if card.name != "VCARD":
                raise InvalidInput("Файл должен содержать контакты vCard.")
            version = (
                str(card.contents.get("version", [None])[0].value)
                if card.contents.get("version")
                else ""
            )
            if version not in {"2.1", "3.0", "4.0"}:
                raise InvalidInput("Поддерживаются контакты vCard 2.1, 3.0 и 4.0.")
            name = " ".join(str(card.n.value).split()) if "n" in card.contents else ""
            if not name and "fn" in card.contents:
                name = str(card.fn.value).strip()
            if not name and "org" in card.contents:
                value = card.org.value
                name = " ".join(value) if isinstance(value, list) else str(value)
            notes = "\n".join(str(item.value) for item in card.contents.get("note", []))
            phones = []
            for item in card.contents.get("tel", []):
                number = str(item.value).strip()
                if number.lower().startswith("tel:"):
                    number = unquote(number[4:]).strip()
                if number:
                    phones.append(number)
            number_count += max(1, len(phones))
            if number_count > 1000:
                raise InvalidInput(
                    "Не более 1000 номеров в одном импорте. Разделите файл контактов."
                )
            rows.append(
                CustomerImportRow(
                    name=name,
                    phone=phones[0] if phones else "",
                    additional_phones=phones[1:],
                    notes=notes,
                )
            )
        if not rows:
            raise InvalidInput("В файле VCF нет контактов.")
        return rows
    except (VObjectError, UnicodeError, ValueError, TypeError, LookupError, RecursionError):
        raise InvalidInput(
            "Не удалось прочитать VCF. Экспортируйте контакты заново в формате vCard."
        ) from None
