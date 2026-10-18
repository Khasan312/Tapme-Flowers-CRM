from typing import Any, Protocol

from tapme.businesses.application.contracts import (
    OFFICE_ROLES,
    MembershipReader,
    Role,
    Scope,
    authorize,
)


class ChatRepository(Protocol):
    def run(self, operation: str, scope: Scope, **data: Any) -> Any: ...


class ChatService:
    def __init__(self, access: MembershipReader, repository: ChatRepository):
        self.access, self.repository = access, repository

    def run(self, operation: str, scope: Scope, **data: Any) -> Any:
        roles = (
            frozenset({Role.OWNER})
            if operation
            in {
                "connect",
                "disconnect",
                "register",
                "subscribe",
                "save_autoreply",
                "save_payment",
                "simulate",
                "simulate_verify",
            }
            else OFFICE_ROLES
        )
        authorize(self.access, scope, roles)
        if operation in {"register", "subscribe", "check"}:
            return self.repository.run("channel_action", scope, action=operation, **data)
        return self.repository.run(operation, scope, **data)
