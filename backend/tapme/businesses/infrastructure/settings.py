from dataclasses import replace

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q

from tapme.accounts.models import User
from tapme.businesses.application.settings import ShopSettings
from tapme.businesses.models import Business, Membership, Shop
from tapme.orders.models import OrderRecord
from tapme.shared.domain import Conflict, InvalidInput, NotFound


class DjangoBusinessSettingsRepository:
    def get(self, business_id, point_ids=None):
        shop = Shop.objects.select_related("business").get(business_id=business_id, is_primary=True)
        if point_ids is not None and shop.id not in point_ids:
            raise NotFound("Основная точка недоступна. Выберите свою точку в настройках филиалов.")
        return ShopSettings(
            shop.business.name,
            shop.address,
            shop.phone,
            shop.business.timezone,
            [{"capacity": 6, "price": "0.00", **w} for w in shop.delivery_windows],
            shop.city,
            shop.whatsapp,
            shop.opening_hours,
            shop.pickup_unlimited,
            shop.enforce_capacity,
            shop.version,
        )

    def save(self, business_id, settings):
        with transaction.atomic():
            Business.objects.select_for_update().get(id=business_id)
            shop = Shop.objects.select_for_update().get(business_id=business_id, is_primary=True)
            if shop.version != settings.version:
                raise Conflict(
                    "Настройки уже изменены в другой вкладке. Ваши изменения не сохранены. "
                    "Загрузите актуальные настройки перед повторным редактированием."
                )
            Business.objects.filter(id=business_id).update(
                name=settings.name, timezone=settings.timezone
            )
            Shop.objects.filter(business_id=business_id, is_primary=True).update(
                name=settings.name,
                address=settings.address,
                phone=settings.phone,
                delivery_windows=settings.windows,
                city=settings.city,
                whatsapp=settings.whatsapp,
                opening_hours=settings.opening_hours,
                pickup_unlimited=settings.pickup_unlimited,
                enforce_capacity=settings.enforce_capacity,
                version=shop.version + 1,
            )
        return replace(settings, version=shop.version + 1)

    def staff(self, business_id):
        return [
            dict(
                id=r.user_id,
                username=r.user.username,
                name=r.user.first_name or r.user.username,
                role=r.role,
                is_active=r.is_active and r.user.is_active,
                phone=r.phone,
                point_ids=list(r.points.values_list("id", flat=True)),
            )
            for r in Membership.objects.filter(business_id=business_id)
            .select_related("user")
            .order_by("user__username")
        ]

    def create_staff(self, business_id, username, password, name, role, phone=""):
        user = User(username=username, first_name=name)
        try:
            user.full_clean(exclude=["password"])
            validate_password(password, user=user)
        except ValidationError as exc:
            raise InvalidInput(" ".join(exc.messages)) from None
        try:
            with transaction.atomic():
                user.set_password(password)
                user.save()
                member = Membership.objects.create(
                    business_id=business_id, user=user, role=role, phone=phone
                )
                if role in {"florist", "courier"}:
                    member.points.add(Shop.objects.get(business_id=business_id, is_primary=True))
        except IntegrityError:
            raise Conflict("Этот логин уже занят.") from None
        return dict(
            id=user.id, username=user.username, name=name, role=role, is_active=True, phone=phone
        )

    def update_staff(self, business_id, user_id, role, active, phone=None):
        with transaction.atomic():
            row = (
                Membership.objects.select_for_update()
                .filter(business_id=business_id, user_id=user_id)
                .first()
            )
            if row is None:
                raise NotFound("Сотрудник не найден.")
            if row.role == "owner":
                raise InvalidInput("Нельзя изменить владельца.")
            row.role, row.is_active = role, active
            if phone is not None:
                row.phone = phone
            row.save(update_fields=["role", "is_active", "phone"])

    def delete_staff(self, business_id, user_id):
        with transaction.atomic():
            row = (
                Membership.objects.select_for_update()
                .filter(business_id=business_id, user_id=user_id)
                .first()
            )
            if row is None:
                raise NotFound("Сотрудник не найден.")
            if row.role == "owner":
                raise InvalidInput("Нельзя удалить владельца магазина.")
            if (
                OrderRecord.objects.filter(business_id=business_id)
                .filter(Q(florist_id=user_id) | Q(courier_id=user_id))
                .exclude(status__in=["done", "cancelled"])
                .exists()
            ):
                raise Conflict(
                    "У сотрудника есть незавершённые заказы. Передайте их другому сотруднику "
                    "или завершите, затем повторите удаление. Курьера можно заменить и в заказе в пути."
                )
            # Keep the user: historical orders, payments and events reference this account.
            row.delete()

    def reset_staff(self, business_id, user_id, password):
        with transaction.atomic():
            user = User.objects.select_for_update().filter(id=user_id).first()
            membership = Membership.objects.filter(business_id=business_id, user_id=user_id).first()
            if not user or not membership:
                raise NotFound("Сотрудник не найден.")
            if (
                membership.role == "owner"
                or Membership.objects.filter(user_id=user_id)
                .exclude(business_id=business_id)
                .exists()
            ):
                raise InvalidInput(
                    "Для этой учётной записи доступ восстанавливается через администратора сервера."
                )
            try:
                validate_password(password, user=user)
            except ValidationError as exc:
                raise InvalidInput(" ".join(exc.messages)) from None
            user.set_password(password)
            user.save(update_fields=["password"])
