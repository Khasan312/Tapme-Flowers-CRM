from uuid import uuid4

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize
from tapme.customers.application.ports import CustomerRepository
from tapme.customers.domain import Customer
from tapme.shared.domain import Conflict, InvalidInput


class CustomerTransferService:
    def __init__(self, access: MembershipReader, repository: CustomerRepository):
        self.access, self.repository = access, repository

    def import_rows(
        self, scope: Scope, rows: list[dict[str, str]], commit: bool
    ) -> dict[str, object]:
        authorize(self.access, scope, OFFICE_ROLES)
        if not 1 <= len(rows) <= 1000:
            raise InvalidInput("Импорт поддерживает от 1 до 1000 строк за один раз.")
        results = []
        seen: set[str] = set()
        created = 0
        for number, row in enumerate(rows, 2):
            try:
                customer = Customer(
                    uuid4(),
                    scope.business_id,
                    row.get("name", ""),
                    row.get("phone", "").removeprefix("'"),
                    row.get("notes", ""),
                    False,
                )
                matches = self.repository.list(scope.business_id, customer.phone, 100, 0)
                duplicate = customer.phone in seen or any(
                    c.phone == customer.phone for c in matches.results
                )
                seen.add(customer.phone)
                status = "duplicate" if duplicate else "ready"
                if commit and not duplicate:
                    try:
                        self.repository.add(customer)
                        status = "created"
                        created += 1
                    except Conflict:
                        status = "duplicate"
                results.append(
                    dict(
                        row=number,
                        name=customer.name,
                        phone=customer.phone,
                        status=status,
                        error="",
                    )
                )
            except InvalidInput as exc:
                results.append(
                    dict(
                        row=number,
                        name=row.get("name", ""),
                        phone=row.get("phone", ""),
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
            rows.extend(dict(name=c.name, phone=c.phone, notes=c.notes) for c in page.results)
            offset += len(page.results)
            if offset >= page.count or not page.results:
                return rows
