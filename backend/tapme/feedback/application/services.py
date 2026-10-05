from typing import Protocol
from uuid import UUID

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize
from tapme.shared.domain import InvalidInput, text


class FeedbackRepository(Protocol):
    def list(self, business_id: UUID, order_id: UUID) -> list[dict[str, object]]: ...
    def create(
        self,
        business_id: UUID,
        order_id: UUID,
        actor_id: UUID | None,
        kind: str,
        message: str,
        rating: int | None,
    ) -> dict[str, object]: ...
    def resolve(
        self, business_id: UUID, feedback_id: UUID, outcome: str, actor_id: UUID
    ) -> None: ...


class FeedbackService:
    def __init__(self, access: MembershipReader, repository: FeedbackRepository):
        self.access, self.repository = access, repository

    def list(self, scope: Scope, order_id: UUID) -> list[dict[str, object]]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.list(scope.business_id, order_id)

    def create(
        self, scope: Scope, order_id: UUID, kind: str, message: str, rating: int | None = None
    ) -> dict[str, object]:
        authorize(self.access, scope, OFFICE_ROLES)
        if kind not in {"review", "complaint"} or (rating is not None and not 1 <= rating <= 5):
            raise InvalidInput("Проверьте вид обращения и оценку.")
        return self.repository.create(
            scope.business_id,
            order_id,
            scope.user_id,
            kind,
            text(message, "Обращение", 2000),
            rating,
        )

    def resolve(self, scope: Scope, feedback_id: UUID, outcome: str) -> None:
        authorize(self.access, scope, OFFICE_ROLES)
        self.repository.resolve(
            scope.business_id, feedback_id, text(outcome, "Результат", 2000), scope.user_id
        )
