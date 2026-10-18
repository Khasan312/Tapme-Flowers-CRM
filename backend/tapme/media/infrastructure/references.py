from itertools import chain

from tapme.businesses.models import Shop
from tapme.catalog.models import ProductRecord
from tapme.media.models import PhotoRecord
from tapme.messaging.models import Message


def photo_keys(business_id=None):
    shops = Shop.objects.exclude(payment_qr_key="")
    photos = PhotoRecord.objects.all()
    products = ProductRecord.objects.exclude(photo_key="")
    messages = Message.objects.exclude(media_key="")
    if business_id is not None:
        shops = shops.filter(business_id=business_id)
        photos = photos.filter(business_id=business_id)
        products = products.filter(business_id=business_id)
        messages = messages.filter(conversation__channel__business_id=business_id)
    return chain(
        shops.values_list("payment_qr_key", flat=True).iterator(),
        photos.values_list("key", flat=True).iterator(),
        products.values_list("photo_key", flat=True).iterator(),
        messages.values_list("media_key", flat=True).iterator(),
    )


def photo_is_referenced(key):
    return (
        Shop.objects.filter(payment_qr_key=key).exists()
        or PhotoRecord.objects.filter(key=key).exists()
        or ProductRecord.objects.filter(photo_key=key).exists()
        or Message.objects.filter(media_key=key).exists()
    )
