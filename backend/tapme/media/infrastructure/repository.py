from dataclasses import asdict, fields

from tapme.media.application.ports import Photo
from tapme.media.models import PhotoRecord
from tapme.shared.domain import NotFound


def to_domain(row):
    return Photo(**{f.name: getattr(row, f.name) for f in fields(Photo)})


class DjangoPhotoRepository:
    def add(self, photo):
        PhotoRecord.objects.create(**asdict(photo))

    def delete(self, business_id, order_id, photo_id):
        PhotoRecord.objects.filter(business_id=business_id, order_id=order_id, id=photo_id).delete()

    def list(self, business_id, order_id):
        return tuple(
            to_domain(r)
            for r in PhotoRecord.objects.filter(
                business_id=business_id, order_id=order_id
            ).order_by("created_at")
        )

    def get(self, business_id, order_id, photo_id):
        row = PhotoRecord.objects.filter(
            business_id=business_id, order_id=order_id, id=photo_id
        ).first()
        if row is None:
            raise NotFound("Фотография не найдена.")
        return to_domain(row)
