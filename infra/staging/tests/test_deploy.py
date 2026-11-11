"""Exercise staging failure boundaries without touching a Docker daemon."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy.sh"
SHA = "a" * 40


class StagingDeployTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.calls = self.root / "calls"
        self.calls.touch()
        self.env_file = self.root / ".env.staging"
        self.env_file.write_text("PUBLIC_DOMAIN=staging.example\n")
        self.env_file.chmod(0o600)
        (self.root / ".deploy-enabled").touch()
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "TAPME_STAGING_ROOT": str(self.root),
            "TAPME_STAGING_LOCAL_IMAGES": "true",
            "STAGING_TEST_CALLS": str(self.calls),
            "STAGING_TEST_FAIL": "",
        }
        docker = self.bin / "docker"
        docker.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "args = sys.argv[1:]\n"
            "with open(os.environ['STAGING_TEST_CALLS'], 'a') as f:\n"
            "    f.write(' '.join(args) + '\\n')\n"
            "failure = os.environ['STAGING_TEST_FAIL']\n"
            "if failure == 'pull' and 'pull' in args: sys.exit(1)\n"
            "if failure == 'config' and 'config' in args: sys.exit(1)\n"
            "if 'exec' in args and any('pg_dump' in a for a in args):\n"
            "    if failure != 'backup': print('PGDMP-test-fixture')\n"
            "if failure == 'startup' and 'up' in args and 'worker' in args: sys.exit(1)\n"
        )
        docker.chmod(0o755)
        curl = self.bin / "curl"
        curl.write_text('#!/bin/sh\nprintf \'{"status":"ok"}\\n\'\n')
        curl.chmod(0o755)

    def run_deploy(self, sha=SHA):
        return subprocess.run(
            ["bash", str(DEPLOY), sha],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def test_invalid_revision_never_calls_docker(self):
        result = self.run_deploy("develop; unexpected-command")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls.read_text(), "")

    def test_disabled_deployment_never_calls_docker(self):
        (self.root / ".deploy-enabled").unlink()
        self.assertNotEqual(self.run_deploy().returncode, 0)
        self.assertEqual(self.calls.read_text(), "")

    def test_registry_failure_keeps_running_application(self):
        self.env.update(
            TAPME_STAGING_LOCAL_IMAGES="false",
            GHCR_TOKEN="test-fixture-only",
            STAGING_TEST_FAIL="pull",
        )
        self.assertNotEqual(self.run_deploy().returncode, 0)
        calls = self.calls.read_text()
        self.assertNotIn(" stop ", calls)
        self.assertNotIn(" migrate ", calls)

    def test_empty_backup_prevents_stopping_and_migrating(self):
        self.env["STAGING_TEST_FAIL"] = "backup"
        self.assertNotEqual(self.run_deploy().returncode, 0)
        calls = self.calls.read_text()
        self.assertNotIn(" stop ", calls)
        self.assertNotIn(" migrate ", calls)
        self.assertFalse((self.root / "state/current").exists())

    def test_failed_startup_preserves_last_successful_revision_and_backup(self):
        (self.root / "state").mkdir()
        current = self.root / "state/current"
        current.write_text("b" * 40 + "\n")
        self.env["STAGING_TEST_FAIL"] = "startup"
        self.assertNotEqual(self.run_deploy().returncode, 0)
        self.assertEqual(current.read_text(), "b" * 40 + "\n")
        self.assertTrue(list((self.root / "backups").glob("*.dump")))

    def test_success_records_revision_without_removing_volumes(self):
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "state/current").read_text(), SHA + "\n")
        calls = self.calls.read_text()
        self.assertNotIn(" down", calls)
        self.assertNotIn("prune", calls)
        self.assertNotIn("tapme-core", calls)
        self.assertNotIn("tapme-blue", calls)
        self.assertNotIn("tapme-green", calls)


if __name__ == "__main__":
    unittest.main()
