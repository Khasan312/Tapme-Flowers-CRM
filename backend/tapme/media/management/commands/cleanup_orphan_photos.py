from datetime import timedelta

from django.core.files.storage import storages
from django.core.management.base import BaseCommand
from django.utils import timezone

from tapme.media.models import PhotoRecord


class Command(BaseCommand):
    help = "Find unreferenced photos older than 24h; preview by default, --apply deletes them."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        storage = storages["photos"]
        cutoff = timezone.now() - timedelta(hours=24)
        count = 0
        pending = [""]
        while pending:
            prefix = pending.pop()
            directories, files = storage.listdir(prefix)
            pending.extend(f"{prefix}/{name}".lstrip("/") for name in directories)
            for filename in files:
                key = f"{prefix}/{filename}".lstrip("/")
                if (
                    storage.get_modified_time(key) < cutoff
                    and not PhotoRecord.objects.filter(key=key).exists()
                ):
                    count += 1
                    if options["apply"]:
                        storage.delete(key)
        self.stdout.write(
            f"{'Deleted' if options['apply'] else 'Found'} {count} old unreferenced photos."
        )
