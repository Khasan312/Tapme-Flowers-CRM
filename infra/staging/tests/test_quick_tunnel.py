"""Check protected tunnel creation and recovery when a temporary URL changes."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "quick_tunnel", Path(__file__).resolve().parents[1] / "quick-tunnel.py"
)
tunnel_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tunnel_module)
SHA = "a" * 40
HOST = "new-test-flower-server.trycloudflare.com"


class QuickTunnelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tunnel = tunnel_module.QuickTunnel(self.root)
        self.tunnel.state.mkdir()
        self.tunnel.env_file.write_text(
            "PUBLIC_DOMAIN=staging.invalid\nSECRET=keep-me\n"
        )
        self.tunnel.env_file.chmod(0o600)
        (self.root / ".deploy-enabled").touch()
        (self.root / "tunnel-access.json").write_text(
            json.dumps(
                {"allowed_emails": ["owner@example.com", "colleague@example.com"]}
            )
        )
        (self.tunnel.state / "current").write_text(SHA)
        (self.tunnel.state / "image-prefix").write_text("ghcr.io/example/flower")
        release = self.root / "releases" / SHA / "staging"
        release.mkdir(parents=True)
        (release / "compose.yaml").touch()
        self.info = {
            "Id": "test-container",
            "State": {"Running": True, "StartedAt": "2026-11-12T00:00:00.000Z"},
            "Config": {"Labels": {tunnel_module.LABEL: "protected-quick"}},
        }
        self.mock_run = patch.object(
            tunnel_module, "run", side_effect=self.command
        ).start()
        self.addCleanup(patch.stopall)
        self.fail_compose = False

    def command(self, args, **kwargs):
        if args[:3] == ["docker", "container", "inspect"]:
            return SimpleNamespace(
                returncode=0, stdout=json.dumps([self.info]), stderr=""
            )
        if args[:2] == ["docker", "logs"]:
            self.assertEqual(args[2:4], ["--since", self.info["State"]["StartedAt"]])
            return SimpleNamespace(stdout="", stderr=f"Visit https://{HOST}\n")
        if args[:2] == ["docker", "compose"] and self.fail_compose:
            raise subprocess.CalledProcessError(1, ["docker", "compose"])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def compose_calls(self):
        return [
            call
            for call in self.mock_run.call_args_list
            if call.args[0][:2] == ["docker", "compose"]
        ]

    def test_missing_or_wildcard_emails_never_start_a_tunnel(self):
        for emails in ([], ["*@example.com"], ["good@example.com,bad@example.com"]):
            (self.root / "tunnel-access.json").write_text(
                json.dumps({"allowed_emails": emails})
            )
            with self.assertRaises(ValueError):
                self.tunnel.start()
        self.mock_run.assert_not_called()

    def test_start_requires_both_exact_email_addresses(self):
        with (
            patch.object(self.tunnel, "inspect", return_value=None),
            patch.object(self.tunnel, "sync", return_value=True),
        ):
            self.tunnel.start()
        args = self.mock_run.call_args.args[0]
        self.assertEqual(
            args[args.index("--allowed-mail") + 1],
            "owner@example.com,colleague@example.com",
        )
        self.assertIn("flower-crm-staging_edge", args)
        self.assertNotIn("--publish", args)
        self.assertNotIn("--privileged", args)

    def test_foreign_container_is_never_changed(self):
        self.info["Config"]["Labels"] = {}
        with self.assertRaises(ValueError):
            self.tunnel.start(restart=True)
        self.assertEqual(self.mock_run.call_count, 1)

    def test_new_url_preserves_secrets_images_and_volumes(self):
        self.assertTrue(self.tunnel.sync())
        self.assertEqual(
            self.tunnel.env_file.read_text(), f"PUBLIC_DOMAIN={HOST}\nSECRET=keep-me\n"
        )
        self.assertEqual(self.tunnel.env_file.stat().st_mode & 0o777, 0o600)
        args = self.compose_calls()[0].args[0]
        self.assertIn("never", args)
        self.assertNotIn("down", args)
        self.assertNotIn("migrate", args)
        self.assertEqual(self.compose_calls()[0].kwargs["env"]["IMAGE_TAG"], SHA)
        self.assertEqual(
            (self.tunnel.state / "tunnel-url").read_text(),
            f"https://{HOST}/crm-flowers/\n",
        )

    def test_unchanged_url_does_not_restart_application(self):
        self.tunnel.sync()
        self.mock_run.reset_mock()
        self.tunnel.sync()
        self.assertEqual(self.compose_calls(), [])

    def test_interrupted_url_file_write_recovers_without_application_restart(self):
        self.tunnel.sync()
        (self.tunnel.state / "tunnel-url").unlink()
        self.mock_run.reset_mock()
        self.tunnel.sync()
        self.assertEqual(self.compose_calls(), [])
        self.assertEqual(
            (self.tunnel.state / "tunnel-url").read_text(),
            f"https://{HOST}/crm-flowers/\n",
        )

    def test_failed_application_update_is_retried_without_publishing_success(self):
        self.fail_compose = True
        with self.assertRaises(subprocess.CalledProcessError):
            self.tunnel.sync()
        self.assertFalse((self.tunnel.state / "tunnel-url").exists())
        self.assertFalse((self.tunnel.state / "tunnel-applied.json").exists())
        self.fail_compose = False
        self.tunnel.sync()
        self.assertEqual(len(self.compose_calls()), 2)
        self.assertTrue((self.tunnel.state / "tunnel-url").exists())

    def test_stop_state_removes_stale_link_and_does_not_start_tunnel(self):
        self.tunnel.sync()
        self.mock_run.reset_mock()
        self.info["State"]["Running"] = False
        self.assertFalse(self.tunnel.sync())
        self.assertFalse((self.tunnel.state / "tunnel-url").exists())
        self.assertEqual(self.mock_run.call_count, 1)

    def test_old_process_url_is_not_reused_after_restart(self):
        self.tunnel.sync()
        self.info["State"]["StartedAt"] = "2026-11-12T01:00:00.000Z"
        with patch.object(
            tunnel_module,
            "run",
            side_effect=[
                SimpleNamespace(
                    returncode=0, stdout=json.dumps([self.info]), stderr=""
                ),
                SimpleNamespace(stdout="", stderr="Starting tunnel..."),
            ],
        ):
            self.assertFalse(self.tunnel.sync())
        self.assertFalse((self.tunnel.state / "tunnel-url").exists())


if __name__ == "__main__":
    unittest.main()
