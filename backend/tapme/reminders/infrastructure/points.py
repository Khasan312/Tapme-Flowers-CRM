"""Branch routing for the shared customer reminder queue."""

from django.db.models import Q

from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.businesses.models import Shop
from tapme.reminders.models import ReminderRecord


def scoped_reminders(scope):
    ids = DjangoMembershipReader().point_ids(scope)
    primary = Shop.objects.filter(business_id=scope.business_id, is_primary=True).first()
    condition = Q(point_id__in=ids)
    # Null only occurs for legacy integrations; it belongs to the primary branch.
    if primary and primary.id in ids:
        condition |= Q(point__isnull=True)
    return ReminderRecord.objects.filter(condition, business_id=scope.business_id)
