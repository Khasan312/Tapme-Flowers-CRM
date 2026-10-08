from typing import TypedDict
from uuid import uuid4

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize
from tapme.customers.application.ports import CustomerRepository
from tapme.customers.domain import Customer
from tapme.shared.domain import Conflict, InvalidInput


class CustomerImportRow(TypedDict, total=False):
    name: str
    phone: str
    additional_phones: list[str]
    notes: str


class CustomerTransferService:
    def __init__(self, access: MembershipReader, repository: CustomerRepository):
        self.access, self.repository = access, repository

    def import_rows(
        self,
        scope: Scope,
        rows: list[CustomerImportRow],
        commit: bool,
        selected_rows: list[int] | None = None,
    ) -> dict[str, object]:
        authorize(self.access, scope, OFFICE_ROLES)
        if not 1 <= len(rows) <= 1000:
            raise InvalidInput("Импорт поддерживает от 1 до 1000 строк за один раз.")
        selected = set(range(2, len(rows) + 2)) if selected_rows is None else set(selected_rows)
        if not selected.issubset(range(2, len(rows) + 2)):
            raise InvalidInput("Выбранных строк нет в этом файле. Проверьте файл заново.")
        results = []
        seen: set[str] = set()
        created = 0
        for number, row in enumerate(rows, 2):
            if number not in selected:
                results.append(
                    dict(
                        row=number,
                        name=row.get("name", ""),
                        phone=row.get("phone", ""),
                        additional_phones=row.get("additional_phones", []),
                        status="unselected",
                        error="",
                    )
                )
                continue
            try:
                customer = Customer(
                    uuid4(),
                    scope.business_id,
                    row.get("name", ""),
                    row.get("phone", "").removeprefix("'"),
                    row.get("notes", ""),
                    False,
                    additional_phones=tuple(
                        p.removeprefix("'") for p in row.get("additional_phones", [])
                    ),
                )
                duplicate = bool(seen.intersection(customer.phones)) or self.repository.has_phone(
                    scope.business_id, customer.phones
                )
                status = "duplicate" if duplicate else "ready"
                if commit and not duplicate:
                    try:
                        self.repository.add(customer)
                        status = "created"
                        created += 1
                    except Conflict:
                        status = "duplicate"
                if status in {"ready", "created"}:
                    seen.update(customer.phones)
                results.append(
                    dict(
                        row=number,
                        name=customer.name,
                        phone=customer.phone,
                        additional_phones=list(customer.additional_phones),
                        status=status,
                        error="Один из номеров уже есть у клиента или в выбранной строке файла. Данные не объединяются автоматически."
                        if status == "duplicate"
                        else "",
                    )
                )
            except InvalidInput as exc:
                results.append(
                    dict(
                        row=number,
                        name=row.get("name", ""),
                        phone=row.get("phone", ""),
                        additional_phones=row.get("additional_phones", []),
                        status="error",
                        error=str(exc),
                    )
                )
        return dict(created=created, results=results, count=len(results))

    def export_rows(self, scope: Scope) -> list[dict[str, str]]:
        authorize(self.access, scope, OFFICE_ROLES)
        rows: list[dict[str, str]] = []
        offset = 0
        while True:
            page = self.repository.list(scope.business_id, "", 100, offset)
            rows.extend(
                dict(
                    name=c.name,
                    phone=c.phone,
                    additional_phones="; ".join(c.additional_phones),
                    notes=c.notes,
                )
                for c in page.results
            )
            offset += len(page.results)
            if offset >= page.count or not page.results:
                return rows
