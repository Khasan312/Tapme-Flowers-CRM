#!/usr/bin/env python3
"""PostgreSQL and private photo backup; never deletes source data."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def docker(options, *args, **kwargs):
    return subprocess.run(
        ["docker", "compose", *options, "--profile", "app", *args],
        cwd=ROOT,
        check=True,
        **kwargs,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=ROOT / "backups")
    parser.add_argument("--compose-file", type=Path)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    options = []
    if args.compose_file:
        options += ["-f", str(args.compose_file.resolve())]
    if args.env_file:
        options += ["--env-file", str(args.env_file.resolve())]
    os.umask(0o077)
    folder = args.directory.resolve() / datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    folder.mkdir(parents=True, exist_ok=False)
    dump = folder / "database.dump"
    with dump.open("wb") as output:
        docker(
            options,
            "exec",
            "-T",
            "postgres",
            "sh",
            "-c",
            'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges',
            stdout=output,
        )
    with (folder / "photos.zip").open("wb") as output:
        docker(
            options,
            "exec",
            "-T",
            "api",
            "python",
            "manage.py",
            "export_photos",
            stdout=output,
        )
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "files": {}}
    for file in folder.rglob("*"):
        if file.is_file():
            manifest["files"][str(file.relative_to(folder))] = hashlib.sha256(
                file.read_bytes()
            ).hexdigest()
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(folder)


if __name__ == "__main__":
    main()
