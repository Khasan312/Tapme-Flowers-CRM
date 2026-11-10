from dataclasses import asdict

from django.db import transaction
from django.db.models import F, Q

from tapme.businesses.application.settings import ShopSettings
from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.businesses.models import Business, Membership, MembershipPoint, Shop
from tapme.orders.models import OrderRecord
from tapme.shared.domain import Conflict, InvalidInput, NotFound, phone, text


def point_data(point):
    return {
        **asdict(
            ShopSettings(
                point.name,
                point.address,
                point.phone,
                point.business.timezone,
                [{"capacity": 6, "price": "0.00", **w} for w in point.delivery_windows],
                point.city,
                point.whatsapp,
                point.opening_hours,
                point.pickup_unlimited,
                point.enforce_capacity,
                point.version,
            )
        ),
        "id": str(point.id),
        "short_name": point.short_name,
        "active": point.active,
        "is_primary": point.is_primary,
        "sort": point.sort,
    }


class DjangoPointRepository:
    def list(self, scope):
        return [
            dict(
                id=str(p.id),
                name=p.name,
                short_name=p.short_name,
                address=p.address,
                city=p.city,
                is_primary=p.is_primary,
                active=p.active,
                version=p.version,
                sort=p.sort,
                windows=[{"capacity": 6, "price": "0.00", **w} for w in p.delivery_windows],
            )
            for p in DjangoMembershipReader().points(scope)
        ]

    def get(self, scope, point_id):
        point = (
            DjangoMembershipReader()
            .points(scope)
            .select_related("business")
            .filter(id=point_id)
            .first()
        )
        if not point:
            raise NotFound("Точка не найдена.")
        return point_data(point)

    @transaction.atomic
    def save(self, scope, point_id, values):
        # Serialize primary switches, point creation and membership expansion in this company.
        business = Business.objects.select_for_update().get(id=scope.business_id)
        if point_id:
            point = Shop.objects.select_for_update().filter(business=business, id=point_id).first()
            if not point:
                raise NotFound("Точка не найдена.")
            if values.get("version") != point.version:
                raise Conflict(
                    "Точка уже изменена в другой вкладке. Загрузите актуальные настройки."
                )
        else:
            point = Shop(business=business, is_primary=False)
            # Preserve the scope of legacy staff when the second point is added.
            if business.points.filter(active=True).count() == 1:
                primary = business.points.get(active=True)
                for member in Membership.objects.select_for_update().filter(
                    business=business, role__in=["florist", "courier"]
                ):
                    if not member.points.exists():
                        MembershipPoint.objects.get_or_create(membership=member, point=primary)
        current = point_data(point)
        for field in (
            "name",
            "address",
            "phone",
            "city",
            "whatsapp",
            "opening_hours",
            "pickup_unlimited",
            "enforce_capacity",
            "windows",
        ):
            if field in values:
                current[field] = values[field]
        current["phone"] = phone(current["phone"], required=False)
        current["whatsapp"] = phone(current["whatsapp"], required=False)
        settings = ShopSettings(**{k: current[k] for k in ShopSettings.__dataclass_fields__})
        settings.validate()
        for field in (
            "name",
            "address",
            "phone",
            "city",
            "whatsapp",
            "opening_hours",
            "pickup_unlimited",
            "enforce_capacity",
        ):
            setattr(point, field, getattr(settings, field))
        point.delivery_windows = settings.windows
        point.short_name = text(values.get("short_name", point.short_name), "Короткое название", 40)
        point.sort = values.get("sort", point.sort)
        if values.get("is_primary"):
            if not point.active:
                raise InvalidInput("Архивную точку нельзя сделать основной.")
            previous = (
                Shop.objects.filter(business=business, is_primary=True).exclude(id=point.id).first()
            )
            if previous:
                # A legacy settings tab carries only a version, not a point id.
                # Do not let a stale primary's version match the newly selected primary.
                point.version = max(point.version, previous.version) + (0 if point_id else 1)
            Shop.objects.filter(business=business, is_primary=True).exclude(id=point.id).update(
                is_primary=False, version=F("version") + 1
            )
            point.is_primary = True
        elif point.is_primary and values.get("is_primary") is False:
            raise InvalidInput("Сначала назначьте другую основную точку.")
        point.version += 1 if point_id else 0
        point.save()
        return point_data(point)

    @transaction.atomic
    def archive(self, scope, point_id, version):
        Business.objects.select_for_update().get(id=scope.business_id)
        point = (
            Shop.objects.select_for_update()
            .filter(id=point_id, business_id=scope.business_id)
            .first()
        )
        if not point:
            raise NotFound("Точка не найдена.")
        if point.version != version:
            raise Conflict("Точка уже изменена. Обновите настройки.")
        if point.is_primary:
            raise Conflict(
                "Основную точку нельзя архивировать. Сначала назначьте другую основную точку."
            )
        numbers = list(
            OrderRecord.objects.filter(point=point)
            .exclude(status__in=["done", "cancelled"])
            .values_list("number", flat=True)[:20]
        )
        if numbers:
            raise Conflict("Сначала завершите заказы точки: " + ", ".join(f"№{n}" for n in numbers))
        point.active = False
        point.version += 1
        point.save(update_fields=["active", "version"])

    @transaction.atomic
    def staff_points(self, scope, user_id, point_ids):
        Business.objects.select_for_update().get(id=scope.business_id)
        member = (
            Membership.objects.select_for_update()
            .filter(business_id=scope.business_id, user_id=user_id)
            .first()
        )
        if not member:
            raise NotFound("Сотрудник не найден.")
        if member.role == "owner":
            raise InvalidInput("Владелец всегда имеет доступ ко всем точкам.")
        points = Shop.objects.filter(business_id=scope.business_id, id__in=point_ids, active=True)
        if points.count() != len(set(point_ids)):
            raise InvalidInput("Выберите активные точки своей компании.")
        if member.role in {"florist", "courier"} and not point_ids:
            raise InvalidInput("Выберите хотя бы одну точку сотрудника.")
        orders = (
            OrderRecord.objects.filter(business_id=scope.business_id)
            .filter(Q(florist_id=user_id) | Q(courier_id=user_id))
            .exclude(status__in=["done", "cancelled"])
        )
        if point_ids and orders.exclude(point_id__in=point_ids).exists():
            raise Conflict(
                "У сотрудника есть незавершённые заказы в исключаемой точке. Сначала передайте их другому сотруднику."
            )
        member.points.set(points)
