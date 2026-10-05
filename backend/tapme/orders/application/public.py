import hashlib
import secrets
from typing import Protocol
from uuid import UUID

from tapme.businesses.application.contracts import OFFICE_ROLES, MembershipReader, Scope, authorize
from tapme.shared.domain import InvalidInput, NotFound, text


class PublicOrderRepository(Protocol):
    def set_token(self, scope: Scope, order_id: UUID, digest: str) -> None: ...
    def get_public(self, digest: str) -> dict[str, object]: ...
    def feedback(self, digest: str, message: str, rating: int) -> None: ...


class PublicOrderService:
    def __init__(self, access: MembershipReader, repository: PublicOrderRepository):
        self.access, self.repository = access, repository

    def issue(self, scope: Scope, order_id: UUID, revoke: bool) -> str:
        authorize(self.access, scope, OFFICE_ROLES)
        token = "" if revoke else secrets.token_urlsafe(32)
        self.repository.set_token(
            scope, order_id, hashlib.sha256(token.encode()).hexdigest() if token else ""
        )
        return token

    def digest(self, token: str) -> str:
        if len(token) != 43 or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
            for c in token
        ):
            raise NotFound("Ссылка недействительна или отозвана.")
        return hashlib.sha256(token.encode()).hexdigest()

    def get(self, token: str) -> dict[str, object]:
        return self.repository.get_public(self.digest(token))

    def feedback(self, token: str, message: str, rating: int) -> None:
        if not 1 <= rating <= 5:
            raise InvalidInput("Выберите оценку от 1 до 5.")
        self.repository.feedback(
            self.digest(token), text(message, "Отзыв", 2000, required=False), rating
        )
