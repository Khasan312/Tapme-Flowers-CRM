from decimal import Decimal

from tapme.businesses.models import Shop
from tapme.orders.application.delivery import DeliverySlot
from tapme.orders.models import OrderRecord


class DjangoDeliverySlots:
    def lock(self, business_id, day, start, end, exclude_id=None):
        # Shared row lock serializes reservations for a store across create and edit.
        shop = Shop.objects.select_for_update().get(business_id=business_id)
        window = next(
            (
                w
                for w in shop.delivery_windows
                if w["start"] == start.strftime("%H:%M") and w["end"] == end.strftime("%H:%M")
            ),
            None,
        )
        orders = OrderRecord.objects.filter(
            business_id=business_id, delivery_date=day, window_start=start, window_end=end
        ).exclude(status="cancelled")
        if shop.pickup_unlimited:
            orders = orders.exclude(fulfillment="pickup")
        if exclude_id:
            orders = orders.exclude(id=exclude_id)
        return DeliverySlot(
            Decimal(window.get("price", "0.00")) if window else Decimal("0.00"),
            window.get("capacity", 6) if window else 6,
            orders.count(),
            shop.enforce_capacity,
            shop.pickup_unlimited,
            window is not None,
        )
