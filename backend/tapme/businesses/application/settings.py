from dataclasses import dataclass
from datetime import time
from decimal import Decimal, InvalidOperation
from typing import Protocol, TypedDict
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tapme.businesses.application.contracts import (
    OFFICE_ROLES,
    MembershipReader,
    Role,
    Scope,
    authorize,
)
from tapme.shared.domain import InvalidInput, money, phone, text


class DeliveryWindow(TypedDict):
    start: str
    end: str
    capacity: int
    price: str


@dataclass(frozen=True)
class ShopSettings:
    name: str
    address: str
    phone: str
    timezone: str
    windows: list[DeliveryWindow]
    city: str = ""
    whatsapp: str = ""
    opening_hours: str = ""
    pickup_unlimited: bool = True
    enforce_capacity: bool = False

    def validate(self) -> None:
        text(self.name, "Название", 150)
        text(self.address, "Адрес", 500, required=False)
        phone(self.phone, required=False)
        phone(self.whatsapp, required=False)
        text(self.city, "Город", 100, required=False)
        text(self.opening_hours, "Часы работы", 150, required=False)
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise InvalidInput("Неизвестный часовой пояс.") from None
        if not 1 <= len(self.windows) <= 24:
            raise InvalidInput("Укажите от 1 до 24 окон доставки.")
        seen: set[tuple[str, str]] = set()
        for window in self.windows:
            try:
                start, end = window["start"], window["end"]
                if time.fromisoformat(start) >= time.fromisoformat(end) or (start, end) in seen:
                    raise ValueError
                seen.add((start, end))
                if type(window["capacity"]) is not int or not 1 <= window["capacity"] <= 999:
                    raise ValueError
                money(Decimal(window["price"]))
            except (KeyError, ValueError, TypeError, InvalidOperation):
                raise InvalidInput("Проверьте начало, конец и повторение окон доставки.") from None


class BusinessSettingsRepository(Protocol):
    def get(self, business_id: UUID) -> ShopSettings: ...
    def save(self, business_id: UUID, settings: ShopSettings) -> ShopSettings: ...
    def staff(self, business_id: UUID) -> list[dict[str, object]]: ...
    def create_staff(
        self,
        business_id: UUID,
        username: str,
        password: str,
        name: str,
        role: Role,
        phone: str = "",
    ) -> dict[str, object]: ...
    def update_staff(
        self, business_id: UUID, user_id: UUID, role: Role, active: bool, phone: str | None = None
    ) -> None: ...
    def reset_staff(self, business_id: UUID, user_id: UUID, password: str) -> None: ...


class BusinessSettingsService:
    def __init__(self, access: MembershipReader, repository: BusinessSettingsRepository):
        self.access, self.repository = access, repository

    def get(self, scope: Scope) -> ShopSettings:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.get(scope.business_id)

    def save(self, scope: Scope, settings: ShopSettings) -> ShopSettings:
        authorize(self.access, scope, frozenset({Role.OWNER}))
        settings.validate()
        return self.repository.save(scope.business_id, settings)

    def staff(self, scope: Scope) -> list[dict[str, object]]:
        authorize(self.access, scope, OFFICE_ROLES)
        return self.repository.staff(scope.business_id)

    def create_staff(
        self,
        scope: Scope,
        username: str,
        password: str,
        name: str,
        role: Role,
        staff_phone: str = "",
    ) -> dict[str, object]:
        authorize(self.access, scope, frozenset({Role.OWNER}))
        if role == Role.OWNER:
            raise InvalidInput("Создание ещё одного владельца недоступно в этом сценарии.")
        return self.repository.create_staff(
            scope.business_id,
            text(username, "Логин", 150),
            password,
            text(name, "Имя", 150),
            role,
            phone(staff_phone, required=False),
        )

    def update_staff(
        self,
        scope: Scope,
        user_id: UUID,
        role: Role,
        is_active: bool,
        staff_phone: str | None = None,
    ) -> None:
        authorize(self.access, scope, frozenset({Role.OWNER}))
        current = self.access.role_for(Scope(user_id, scope.business_id))
        if user_id == scope.user_id or current == Role.OWNER or role == Role.OWNER:
            raise InvalidInput("Изменение владельца через эту форму недоступно.")
        self.repository.update_staff(
            scope.business_id,
            user_id,
            role,
            is_active,
            phone(staff_phone, required=False) if staff_phone is not None else None,
        )

    def reset_staff(self, scope: Scope, user_id: UUID, password: str) -> None:
        authorize(self.access, scope, frozenset({Role.OWNER}))
        if user_id == scope.user_id:
            raise InvalidInput("Свой пароль меняйте в личном профиле.")
        self.repository.reset_staff(scope.business_id, user_id, password)
