from tapme.businesses.application.contracts import Role
from tapme.businesses.models import Business, Membership


def business_ids():
    return Business.objects.values_list("id", flat=True).iterator()


class DjangoMembershipReader:
    def role_for(self, scope):
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
