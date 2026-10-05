import sys
from pathlib import PurePosixPath
from zipfile import ZIP_STORED, ZipFile

from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError

from tapme.media.models import PhotoRecord


class Command(BaseCommand):
    help = "Stream a ZIP archive of referenced photos from the configured private storage."

    def handle(self, *args, **options):
        storage = storages["photos"]
        with ZipFile(sys.stdout.buffer, "w", compression=ZIP_STORED) as archive:
            for key in PhotoRecord.objects.values_list("key", flat=True).iterator():
                path = PurePosixPath(key)
                if path.is_absolute() or ".." in path.parts:
                    raise CommandError("Invalid photo key.")
                with storage.open(key, "rb") as source:
                    archive.writestr(key, source.read())
