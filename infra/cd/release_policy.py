"""Validate a new production tag before publishing images or deploying."""

import argparse
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path

TAG = re.compile(r"(release|hotfix-release)-(\d{4}-\d{2}-\d{2})(?:\.([1-9]\d*))?")
SHA = re.compile(r"[0-9a-f]{40}")


def release_kind(tag: str) -> str:
    match = TAG.fullmatch(tag)
    if match is None:
        raise ValueError(
            "Expected release-YYYY-MM-DD[.N] or hotfix-release-YYYY-MM-DD[.N]."
        )
    date.fromisoformat(match[2])
    return match[1]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def is_ancestor(ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant]
    )
    if result.returncode not in (0, 1):
        raise ValueError(
            "Cannot verify release history; a complete checkout is required."
        )
    return result.returncode == 0


def validate_release(
    event: dict, expected_sha: str, state_file: Path | None = None
) -> str:
    ref = event.get("ref", "")
    if (
        not ref.startswith("refs/tags/")
        or not event.get("created", False)
        or event.get("deleted", False)
        or event.get("forced", False)
    ):
        raise ValueError("Production deployment requires a new tag push.")
    tag = ref.removeprefix("refs/tags/")
    release_kind(tag)
    if not SHA.fullmatch(expected_sha):
        raise ValueError("Expected a full commit SHA.")
    if git("rev-parse", "HEAD") != expected_sha:
        raise ValueError("Checkout does not match the workflow commit.")
    if git("rev-parse", f"refs/tags/{tag}^{{commit}}") != expected_sha:
        raise ValueError("Release tag does not match the workflow commit.")
    if not is_ancestor(expected_sha, "refs/remotes/origin/main"):
        raise ValueError("Release commit must be merged into main first.")
    if state_file is not None and state_file.exists():
        state = state_file.read_text().split()
        if (
            len(state) != 2
            or state[0] not in {"blue", "green"}
            or not SHA.fullmatch(state[1])
        ):
            raise ValueError("Invalid production deployment state.")
        if not is_ancestor(state[1], expected_sha):
            raise ValueError(
                "Release would discard deployed commits; create a new fix release."
            )
    return tag


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", type=Path)
    args = parser.parse_args()
    try:
        if os.environ.get("GITHUB_EVENT_NAME") != "push":
            raise ValueError("Production deployment requires a new tag push.")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        tag = validate_release(event, os.environ["GITHUB_SHA"], args.state_file)
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Release validation failed: {exc}\n")
    print(f"Validated {tag} at {os.environ['GITHUB_SHA']}")


if __name__ == "__main__":
    main()
