from itertools import chain

from tapme.catalog.models import ProductRecord
from tapme.media.models import PhotoRecord


def photo_keys(business_id=None):
    photos = PhotoRecord.objects.all()
    products = ProductRecord.objects.exclude(photo_key="")
    if business_id is not None:
        photos = photos.filter(business_id=business_id)
        products = products.filter(business_id=business_id)
    return chain(
        photos.values_list("key", flat=True).iterator(),
        products.values_list("photo_key", flat=True).iterator(),
    )


def photo_is_referenced(key):
    return (
        PhotoRecord.objects.filter(key=key).exists()
        or ProductRecord.objects.filter(photo_key=key).exists()
    )
