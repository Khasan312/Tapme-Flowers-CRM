from django.core.files.base import ContentFile
from django.core.files.storage import storages

from tapme.media.infrastructure.storage import DjangoPhotoStorage
from tapme.shared.domain import InvalidInput, NotFound


class DjangoAttachmentStorage:
    def save(self, key, content, mime):
        if not content or len(content) > 16 * 1024 * 1024:
            raise InvalidInput("Вложение должно быть не больше 16 МБ.")
        mime = mime.split(";")[0].strip().lower()
        if mime in {"image/jpeg", "image/png", "image/webp"}:
            if len(content) > 5 * 1024 * 1024:
                raise InvalidInput("Изображение должно быть не больше 5 МБ.")
            key = DjangoPhotoStorage().save(key + ".jpg", content)
            return key, "image/jpeg"
        allowed = {
            "application/pdf",
            "audio/aac",
            "audio/mp4",
            "audio/mpeg",
            "audio/amr",
            "audio/ogg",
            "video/mp4",
        }
        if mime not in allowed or (mime == "application/pdf" and not content.startswith(b"%PDF-")):
            raise InvalidInput("Поддерживаются фотографии, PDF, аудио и MP4 до 16 МБ.")
        return storages["photos"].save(key, ContentFile(content)), mime

    def read(self, key):
        try:
            with storages["photos"].open(key, "rb") as handle:
                return handle.read()
        except FileNotFoundError:
            raise NotFound("Вложение не найдено.") from None

    def delete(self, key):
        storages["photos"].delete(key)
