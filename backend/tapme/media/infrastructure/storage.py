import warnings
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import storages
from PIL import Image, ImageOps, UnidentifiedImageError

from tapme.shared.domain import InvalidInput, NotFound


class DjangoPhotoStorage:
    def __init__(self):
        self.storage = storages["photos"]

    def save(self, key, content):
        if not content or len(content) > 10 * 1024 * 1024:
            raise InvalidInput("Фото должно занимать не более 10 МБ.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as original:
                    if (
                        original.format not in {"JPEG", "PNG", "WEBP"}
                        or original.width * original.height > 24_000_000
                    ):
                        raise InvalidInput("Используйте JPEG, PNG или WebP до 24 мегапикселей.")
                    original.load()
                    picture = ImageOps.exif_transpose(original).convert("RGB")
                    picture.thumbnail((2400, 2400))
                    out = BytesIO()
                    picture.save(out, format="JPEG", quality=88)
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise InvalidInput("Файл не является допустимой фотографией.") from None
        return self.storage.save(key, ContentFile(out.getvalue()))

    def read(self, key):
        try:
            with self.storage.open(key, "rb") as handle:
                return handle.read()
        except FileNotFoundError:
            raise NotFound("Фотография не найдена.") from None

    def delete(self, key):
        self.storage.delete(key)
