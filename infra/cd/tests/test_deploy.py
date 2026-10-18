"""Exercise deployment ordering and rollback without a Docker daemon or server."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]
OLD_SHA = "a" * 40
NEW_SHA = "b" * 40
DOCKER = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
root = pathlib.Path(os.environ["FAKE_ROOT"])
with (root / "calls.jsonl").open("a") as log:
    log.write(json.dumps(args) + "\n")
if args[0] == "login":
    sys.stdin.read()
if "tapme-core" in args and "create" in args and "gateway" in args:
    (root / "edge-network").touch()
if "tapme-core" not in args and ("run" in args or "up" in args):
    if not (root / "edge-network").exists():
        print("network tapme-edge declared as external, but could not be found", file=sys.stderr)
        sys.exit(1)
if "ps" in args and "gateway" in args and (root / "state/current").exists():
    print("existing-gateway-container")
stage = os.environ.get("FAKE_FAIL", "")
if stage == "cancel" and "migrate" in args:
    import signal
    os.kill(os.getppid(), signal.SIGTERM)
    sys.exit(0)
is_new = os.environ.get("IMAGE_TAG") == "b" * 40
failure = (
    (stage == "migrate" and "migrate" in args)
    or (stage == "candidate" and is_new and "up" in args and "api" in args)
    or (stage == "jobs" and is_new and "up" in args and "worker" in args)
    or (stage == "reload" and "reload" in args)
)
flag = root / "failed-once"
if failure and not flag.exists():
    flag.touch()
    sys.exit(23)
if any("pg_dump" in arg for arg in args) and stage != "empty-backup":
    print("fake custom-format PostgreSQL dump")
'''
CURL = r'''#!/usr/bin/env python3
import json, os, sys
if any(arg.endswith("/health/") for arg in sys.argv):
    print(json.dumps({"status": "unavailable" if os.environ.get("FAKE_FAIL") == "health" else "ok"}))
'''


PYTHON = f'''#!{sys.executable}
import os, pathlib, sys
if len(sys.argv) > 1 and sys.argv[1].endswith("check_web_routes.py"):
    pathlib.Path(os.environ["FAKE_ROOT"], "web-checked").touch()
    sys.exit(23 if os.environ.get("FAKE_FAIL") == "assets" else 0)
os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])
'''


class DeployTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, content in (("docker", DOCKER), ("curl", CURL), ("python3", PYTHON)):
            path = self.bin / name
            path.write_text(content)
            path.chmod(0o755)
        self.env_file = self.root / ".env.production"
        self.env_file.write_text("PUBLIC_DOMAIN=tapme.example\nPOSTGRES_PASSWORD=secret\n")
        self.env_file.chmod(0o600)
        (self.root / ".deploy-enabled").touch()
        (self.root / "state").mkdir()
        (self.root / "state/current").write_text(f"blue {OLD_SHA}\n")
        (self.root / "edge-network").touch()
        (self.root / "gateway").mkdir()
        self.old_route = "reverse_proxy tapme-web-blue:80\n"
        (self.root / "gateway/active.caddy").write_text(self.old_route)
        (self.root / "gateway/Caddyfile").write_text("old working configuration\n")
        old = self.root / "releases" / OLD_SHA
        old.mkdir(parents=True)
        shutil.copy(SOURCE / "release.yaml", old / "release.yaml")

    def run_deploy(self, failure="", sha=NEW_SHA):
        env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "TAPME_DEPLOY_ROOT": str(self.root),
            "GHCR_TOKEN": "test-token-must-never-be-printed",
            "FAKE_ROOT": str(self.root),
            "FAKE_FAIL": failure,
        }
        result = subprocess.run(
            ["bash", str(SOURCE / "deploy.sh"), sha],
            env=env,
            text=True,
            capture_output=True,
            timeout=15,
        )
        self.assertNotIn(env["GHCR_TOKEN"], result.stdout + result.stderr)
        self.assertEqual(list(self.root.glob(".deployment.*")), [])
        return result

    def calls(self):
        path = self.root / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_previous_release(self):
        self.assertEqual((self.root / "state/current").read_text(), f"blue {OLD_SHA}\n")
        self.assertEqual((self.root / "gateway/active.caddy").read_text(), self.old_route)

    def test_requires_explicit_server_enablement(self):
        (self.root / ".deploy-enabled").unlink()
        self.assertEqual(self.run_deploy().returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_rejects_arbitrary_revision(self):
        self.assertEqual(self.run_deploy(sha="main;touch /tmp/unsafe").returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_rejects_exposed_secrets(self):
        self.env_file.chmod(0o644)
        self.assertEqual(self.run_deploy().returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_repeated_deployment_is_noop(self):
        self.assertEqual(self.run_deploy(sha=OLD_SHA).returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_success_backs_up_before_migration_and_retains_old_api(self):
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.calls()
        backup = next(i for i, args in enumerate(calls) if any("pg_dump" in a for a in args))
        migration = next(i for i, args in enumerate(calls) if "migrate" in args)
        candidate = next(i for i, args in enumerate(calls) if "up" in args and "api" in args)
        reload = next(i for i, args in enumerate(calls) if "reload" in args)
        self.assertLess(backup, migration)
        self.assertLess(candidate, reload)
        self.assertEqual((self.root / "state/current").read_text(), f"green {NEW_SHA}\n")
        self.assertEqual((self.root / "state/previous").read_text(), f"blue {OLD_SHA}\n")
        self.assertTrue(list((self.root / "backups").glob("*.dump")))
        for args in calls:
            self.assertNotIn("-v", args)
            self.assertNotIn("--volumes", args)
            self.assertFalse("up" in args and "gateway" in args)
            if "create" in args and "gateway" in args:
                self.assertIn("--no-recreate", args)
            if "tapme-blue" in args and "stop" in args:
                self.assertEqual(args[-2:], ["beat", "worker"])

    def test_migration_failure_does_not_touch_live_release(self):
        self.assertNotEqual(self.run_deploy("migrate").returncode, 0)
        self.assert_previous_release()
        self.assertFalse(any("reload" in args for args in self.calls()))
        self.assertFalse(any("tapme-blue" in args and "stop" in args for args in self.calls()))

    def test_empty_backup_prevents_migration(self):
        self.assertNotEqual(self.run_deploy("empty-backup").returncode, 0)
        self.assert_previous_release()
        self.assertFalse(any("migrate" in args for args in self.calls()))

    def test_cancelled_deployment_preserves_previous_release(self):
        self.assertEqual(self.run_deploy("cancel").returncode, 143)
        self.assert_previous_release()

    def test_unhealthy_candidate_keeps_live_release(self):
        self.assertNotEqual(self.run_deploy("candidate").returncode, 0)
        self.assert_previous_release()
        self.assertFalse(any("reload" in args for args in self.calls()))

    def test_worker_failure_restores_previous_jobs(self):
        self.assertNotEqual(self.run_deploy("jobs").returncode, 0)
        self.assert_previous_release()
        self.assertTrue(any("tapme-blue" in a and "up" in a and "worker" in a for a in self.calls()))

    def test_reload_failure_restores_gateway_and_jobs(self):
        self.assertNotEqual(self.run_deploy("reload").returncode, 0)
        self.assert_previous_release()
        self.assertEqual((self.root / "gateway/Caddyfile").read_text(), "old working configuration\n")
        self.assertEqual(sum("reload" in a for a in self.calls()), 2)

    def test_failed_gateway_health_restores_previous_release(self):
        self.assertNotEqual(self.run_deploy("health").returncode, 0)
        self.assert_previous_release()

    def test_missing_web_assets_restores_previous_release(self):
        self.assertNotEqual(self.run_deploy("assets").returncode, 0)
        self.assertTrue((self.root / "web-checked").exists())
        self.assert_previous_release()
        self.assertEqual(sum("reload" in a for a in self.calls()), 2)

    def test_first_deployment_selects_blue(self):
        (self.root / "state/current").unlink()
        (self.root / "edge-network").unlink()
        for path in (self.root / "gateway").iterdir():
            path.unlink()
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / "state/current").read_text(), f"blue {NEW_SHA}\n")


if __name__ == "__main__":
    unittest.main()
