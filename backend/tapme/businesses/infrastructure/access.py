from dataclasses import replace

from tapme.businesses.application.contracts import Role
from tapme.businesses.models import Business, Membership, Shop
from tapme.shared.domain import Forbidden, InvalidInput


def business_ids():
    return Business.objects.values_list("id", flat=True).iterator()


class DjangoMembershipReader:
    def points(self, scope):
        member = Membership.objects.filter(
            business_id=scope.business_id,
            user_id=scope.user_id,
            is_active=True,
            user__is_active=True,
        ).first()
        points = Shop.objects.filter(business_id=scope.business_id)
        if not member:
            return points.none()
        if member.role != Role.OWNER:
            assigned = member.points.values_list("id", flat=True)
            if assigned.exists():
                points = points.filter(id__in=assigned)
            elif member.role != Role.MANAGER:
                if points.filter(active=True).count() != 1:
                    return points.none()
                points = points.filter(active=True)
        return points

    def point_ids(self, scope):
        points = self.points(scope)
        if scope.point_id:
            if not points.filter(id=scope.point_id).exists():
                raise Forbidden("Нет доступа к выбранной точке.")
            points = points.filter(id=scope.point_id)
        return tuple(points.values_list("id", flat=True))

    def order_point(self, scope, point_id):
        points = self.points(replace(scope, point_id=None)).filter(active=True)
        selected = point_id or scope.point_id
        if selected:
            if not points.filter(id=selected).exists():
                raise InvalidInput("Выберите доступную активную точку.")
            return selected
        if Shop.objects.filter(business_id=scope.business_id, active=True).count() != 1:
            raise InvalidInput("Выберите точку для заказа.")
        point = points.first()
        if not point:
            raise Forbidden("Владелец ещё не назначил вам точку.")
        return point.id

    def role_for(self, scope):
        if scope.point_id and not self.points(scope).filter(id=scope.point_id).exists():
            return None
        role = (
            Membership.objects.filter(
                business_id=scope.business_id,
                user_id=scope.user_id,
                is_active=True,
                user__is_active=True,
            )
            .values_list("role", flat=True)
            .first()
        )
        return Role(role) if role else None
