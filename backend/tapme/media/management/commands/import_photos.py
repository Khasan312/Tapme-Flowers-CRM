import hashlib
import shutil
import sys
from pathlib import PurePosixPath
from tempfile import TemporaryFile
from zipfile import ZipFile

from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError

from tapme.media.infrastructure.references import photo_keys


class Command(BaseCommand):
    help = (
        "Restore referenced photos from ZIP on stdin after database recovery; preview by default."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        storage = storages["photos"]
        keys = set(photo_keys())
        if any(
            PurePosixPath(key).is_absolute() or ".." in PurePosixPath(key).parts for key in keys
        ):
            raise CommandError("Invalid photo key.")
        restored = 0
        with TemporaryFile() as source:
            shutil.copyfileobj(sys.stdin.buffer, source)
            source.seek(0)
            with ZipFile(source) as archive:
                if not keys.issubset(archive.namelist()) or archive.testzip() is not None:
                    raise CommandError("Archive is incomplete or corrupt.")
                for key in keys:
                    content = archive.read(key)
                    if storage.exists(key):
                        with storage.open(key, "rb") as current:
                            if (
                                hashlib.sha256(current.read()).digest()
                                != hashlib.sha256(content).digest()
                            ):
                                raise CommandError(
                                    "A different photo already exists; use an empty recovery storage."
                                )
                        continue
                    restored += 1
                    if options["apply"]:
                        saved = storage.save(key, ContentFile(content))
                        if saved != key:
                            storage.delete(saved)
                            raise CommandError(
                                "Storage renamed a key; stop writes during recovery."
                            )
        self.stdout.write(
            f"{'Restored' if options['apply'] else 'Would restore'} {restored} photos."
        )
