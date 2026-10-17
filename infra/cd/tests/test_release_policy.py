"""Check release naming and Git history using temporary repositories."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import chdir
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_policy import release_kind, validate_release  # noqa: E402


class ReleasePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Release test")
        self.git("config", "user.email", "release-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.base = self.commit("deployed baseline")
        self.current = self.commit("next release")
        self.git("update-ref", "refs/remotes/origin/main", self.current)
        self.tag = "release-2026-10-18"
        self.git("tag", self.tag)
        self.state = self.root / "production-state"

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-c", "core.hooksPath=/dev/null", *args],
            cwd=self.root,
            text=True,
            stderr=subprocess.PIPE,
        ).strip()

    def commit(self, message, filename="changes.txt"):
        (self.root / filename).write_text(message)
        self.git("add", filename)
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def event(self, **overrides):
        return {
            "ref": f"refs/tags/{self.tag}",
            "created": True,
            "deleted": False,
            "forced": False,
            **overrides,
        }

    def validate(self, event=None, sha=None):
        with chdir(self.root):
            return validate_release(
                event or self.event(), sha or self.current, self.state
            )

    def test_accepts_planned_release_and_forward_deployment(self):
        self.state.write_text(f"blue {self.base}\n")
        self.assertEqual(self.validate(), self.tag)

    def test_accepts_annotated_tag_and_same_commit_retry(self):
        self.tag = "release-2026-10-18.1"
        self.git("-c", "tag.gpgsign=false", "tag", "-a", self.tag, "-m", "retry")
        self.state.write_text(f"green {self.current}\n")
        self.assertEqual(self.validate(), self.tag)

    def test_accepts_hotfix_and_multiple_releases_per_day(self):
        for tag in (
            "hotfix-release-2026-10-18",
            "hotfix-release-2026-10-18.1",
            "hotfix-release-2026-10-18.2",
            "release-2026-10-18.2",
        ):
            with self.subTest(tag=tag):
                self.assertIn(release_kind(tag), {"release", "hotfix-release"})

    def test_rejects_invalid_tag_names_dates_and_sequences(self):
        for tag in (
            "v1.0.0",
            "release-2026-02-29",
            "release-2026-13-01",
            "release-2026-1-01",
            "release-2026-10-18.0",
            "release-2026-10-18.01",
            "hotfix-release-2026-10-18*",
            "release-2026-10-18\n",
            "main",
        ):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release_kind(tag)

    def test_rejects_tag_updates_and_deletion(self):
        for overrides in ({"created": False}, {"deleted": True}, {"forced": True}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.validate(self.event(**overrides))

    def test_rejects_branch_push(self):
        with self.assertRaisesRegex(ValueError, "new tag push"):
            self.validate(self.event(ref="refs/heads/main"))

    def test_rejects_unmerged_commit(self):
        self.git("checkout", "-q", "-b", "feature")
        sha = self.commit("unmerged change")
        self.tag = "hotfix-release-2026-10-18"
        self.git("tag", self.tag)
        with self.assertRaisesRegex(ValueError, "merged into main"):
            self.validate(sha=sha)

    def test_rejects_moved_tag(self):
        self.git("tag", "-f", self.tag, self.base)
        with self.assertRaisesRegex(ValueError, "tag does not match"):
            self.validate()

    def test_rejects_wrong_checkout(self):
        self.git("checkout", "-q", "--detach", self.base)
        with self.assertRaisesRegex(ValueError, "Checkout does not match"):
            self.validate()

    def test_rejects_older_release_than_production(self):
        self.state.write_text(f"blue {self.current}\n")
        self.git("checkout", "-q", "--detach", self.base)
        self.tag = "release-2026-10-17"
        self.git("tag", self.tag)
        with self.assertRaisesRegex(ValueError, "discard deployed commits"):
            self.validate(sha=self.base)

    def test_rejects_malformed_production_state(self):
        self.state.write_text("unknown; not-a-commit\n")
        with self.assertRaisesRegex(ValueError, "Invalid production"):
            self.validate()

    def test_isolated_hotfix_does_not_include_unreleased_main_changes(self):
        self.git("checkout", "-q", "-b", "hotfix/urgent", self.base)
        hotfix = self.commit("only urgent fix", "urgent-fix.txt")
        self.git("checkout", "-q", "main")
        self.git("merge", "--no-ff", "hotfix/urgent", "-m", "Merge hotfix")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.git("checkout", "-q", "--detach", hotfix)
        self.tag = "hotfix-release-2026-10-18.1"
        self.git("tag", self.tag)
        self.state.write_text(f"blue {self.base}\n")
        self.assertEqual(self.validate(sha=hotfix), self.tag)
        self.assertEqual((self.root / "changes.txt").read_text(), "deployed baseline")
        self.assertEqual((self.root / "urgent-fix.txt").read_text(), "only urgent fix")

    def test_cli_rejects_non_release_invocation(self):
        for event_name in ("workflow_dispatch", "release"):
            with self.subTest(event_name=event_name):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).resolve().parents[1] / "release_policy.py"),
                    ],
                    env={**os.environ, "GITHUB_EVENT_NAME": event_name},
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("requires a new tag push", result.stderr)

    def test_cli_accepts_tag_push_without_a_github_release(self):
        event_file = self.root / "event.json"
        event_file.write_text(json.dumps(self.event()))
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "release_policy.py"),
            ],
            cwd=self.root,
            env={
                **os.environ,
                "GITHUB_EVENT_NAME": "push",
                "GITHUB_EVENT_PATH": str(event_file),
                "GITHUB_SHA": self.current,
            },
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.tag, result.stdout)


if __name__ == "__main__":
    unittest.main()
