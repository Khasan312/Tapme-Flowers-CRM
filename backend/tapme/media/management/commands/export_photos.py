import sys
from pathlib import PurePosixPath
from zipfile import ZIP_STORED, ZipFile

from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError

from tapme.media.infrastructure.references import photo_keys


class Command(BaseCommand):
    help = "Stream a ZIP archive of referenced photos from the configured private storage."

    def handle(self, *args, **options):
        storage = storages["photos"]
        with ZipFile(sys.stdout.buffer, "w", compression=ZIP_STORED) as archive:
            for key in photo_keys():
                path = PurePosixPath(key)
                if path.is_absolute() or ".." in path.parts:
                    raise CommandError("Invalid photo key.")
                with storage.open(key, "rb") as source:
                    archive.writestr(key, source.read())
