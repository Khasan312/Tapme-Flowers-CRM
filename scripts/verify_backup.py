#!/usr/bin/env python3
"""Restore into a new disposable database, check schema and photos, then drop only it."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def command(options, script, database, **kwargs):
    return subprocess.run(
        [
            "docker",
            "compose",
            *options,
            "exec",
            "-T",
            "postgres",
            "sh",
            "-c",
            script,
            "sh",
            database,
        ],
        cwd=ROOT,
        check=True,
        **kwargs,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("backup", type=Path)
    parser.add_argument("--compose-file", type=Path)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    options = []
    if args.compose_file:
        options += ["-f", str(args.compose_file.resolve())]
    if args.env_file:
        options += ["--env-file", str(args.env_file.resolve())]
    folder = args.backup.resolve()
    manifest = json.loads((folder / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        path = (folder / name).resolve()
        if (
            not path.is_relative_to(folder)
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise SystemExit("Backup integrity check failed.")
    database = "tapme_restore_check_" + uuid4().hex[:16]
    command(options, 'createdb -U "$POSTGRES_USER" "$1"', database)
    try:
        with (folder / "database.dump").open("rb") as source:
            command(
                options,
                'pg_restore --exit-on-error --no-owner --no-privileges -U "$POSTGRES_USER" -d "$1"',
                database,
                stdin=source,
            )
        result = command(
            options,
            'psql -X -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -c "SELECT count(*) FROM django_migrations; SELECT count(*) FROM orders_orderrecord; SELECT count(*) FROM customers_customerrecord;"',
            database,
            capture_output=True,
            text=True,
        )
        counts = result.stdout.splitlines()
        if (
            len(counts) != 3
            or not all(c.isdigit() for c in counts)
            or int(counts[0]) < 1
        ):
            raise SystemExit("Restored schema verification failed.")
        if (folder / "photos.zip").exists():
            keys = command(
                options,
                'psql -X -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -c "SELECT key FROM media_photorecord;"',
                database,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            has_product_photos = (
                command(
                    options,
                    'psql -X -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -c "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name=\'catalog_productrecord\' AND column_name=\'photo_key\');"',
                    database,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                == "t"
            )
            if has_product_photos:
                keys.extend(
                    command(
                        options,
                        'psql -X -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -c "SELECT photo_key FROM catalog_productrecord WHERE photo_key <> \'\';"',
                        database,
                        capture_output=True,
                        text=True,
                    ).stdout.splitlines()
                )
            with (
                ZipFile(folder / "photos.zip") as archive,
                TemporaryDirectory(prefix="tapme-photo-restore-") as tmp,
            ):
                target = Path(tmp)
                for name in archive.namelist():
                    if not (target / name).resolve().is_relative_to(target):
                        raise SystemExit("Unsafe photo archive path.")
                if archive.testzip() is not None or not set(keys).issubset(
                    archive.namelist()
                ):
                    raise SystemExit("Photo archive is incomplete or corrupt.")
                archive.extractall(target)
                if not all((target / key).is_file() for key in keys):
                    raise SystemExit("Photo restore failed.")
        print(
            "Backup restored successfully into an isolated database; schema, record counts and photo archive verified."
        )
    finally:
        command(options, 'dropdb -U "$POSTGRES_USER" "$1"', database)


if __name__ == "__main__":
    main()
