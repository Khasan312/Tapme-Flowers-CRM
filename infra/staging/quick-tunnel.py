"""Manage the protected staging Quick Tunnel and reconcile its changing URL."""

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CONTAINER = "flower-crm-staging-tunnel"
LABEL = "com.flower-crm.staging.tunnel"
IMAGE = (
    "cloudflare/cloudflared@sha256:"
    "4955524aeaa379e154023d5a027c250f7b35041a2e7e950cf13f144bc9b9c5ba"
)
URL_PATTERN = re.compile(r"https://([a-z0-9]+(?:-[a-z0-9]+)+\.trycloudflare\.com)\b")


def run(args, *, env=None, timeout=240, check=True):
    return subprocess.run(
        args, env=env, text=True, capture_output=True, timeout=timeout, check=check
    )


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class QuickTunnel:
    def __init__(self, root):
        self.root = root
        self.state = root / "state"
        self.env_file = root / ".env.staging"

    def emails(self):
        values = json.loads((self.root / "tunnel-access.json").read_text())[
            "allowed_emails"
        ]
        if not isinstance(values, list) or not 1 <= len(values) <= 10:
            raise ValueError(
                "Configure 1–10 explicit email addresses in tunnel-access.json."
            )
        pattern = r"[A-Za-z0-9.!#$%&'+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
        if any(
            not isinstance(value, str) or not re.fullmatch(pattern, value)
            for value in values
        ):
            raise ValueError("Use explicit email addresses; wildcards are not allowed.")
        return list(dict.fromkeys(value.lower() for value in values))

    def inspect(self):
        result = run(["docker", "container", "inspect", CONTAINER], check=False)
        if result.returncode:
            if (
                "No such container" in result.stderr
                or "No such object" in result.stderr
            ):
                return None
            raise RuntimeError("Cannot inspect the staging tunnel; check Docker.")
        info = json.loads(result.stdout)[0]
        if info.get("Config", {}).get("Labels", {}).get(LABEL) != "protected-quick":
            raise ValueError(
                "Refusing to modify a container not managed by this script."
            )
        return info

    def forget_url(self):
        for name in ("tunnel-url", "tunnel-applied.json"):
            (self.state / name).unlink(missing_ok=True)

    def start(self, restart=False):
        emails = (
            self.emails()
        )  # Never create an unrestricted tunnel, even with bad config.
        if not (self.root / ".deploy-enabled").exists():
            raise ValueError("Staging deployment must be enabled first.")
        info = self.inspect()
        if restart and info:
            run(["docker", "stop", "--time", "30", CONTAINER])
            run(["docker", "rm", CONTAINER])
            info = None
        if info:
            args = info["Config"].get("Cmd", [])
            if (
                "--allowed-mail" not in args
                or args.index("--allowed-mail") + 1 >= len(args)
                or args[args.index("--allowed-mail") + 1] != ",".join(emails)
            ):
                raise ValueError(
                    "Email configuration changed; use restart to apply it."
                )
            run(["docker", "start", CONTAINER])
        else:
            self.forget_url()
            run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    CONTAINER,
                    "--label",
                    f"{LABEL}=protected-quick",
                    "--restart",
                    "unless-stopped",
                    "--network",
                    "flower-crm-staging_edge",
                    "--read-only",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges:true",
                    "--log-driver",
                    "json-file",
                    "--log-opt",
                    "max-size=10m",
                    "--log-opt",
                    "max-file=3",
                    IMAGE,
                    "tunnel",
                    "--no-autoupdate",
                    "--protocol",
                    "http2",
                    "--metrics",
                    "127.0.0.1:20241",
                    "--url",
                    "http://web:80",
                    "--allowed-mail",
                    ",".join(emails),
                ]
            )
        for _ in range(20):
            if self.sync():
                return
            time.sleep(1)
        raise RuntimeError(
            "Tunnel is starting. Cron will retry; inspect its Docker logs if needed."
        )

    def sync(self):
        info = self.inspect()
        if not info or not info["State"]["Running"]:
            self.forget_url()
            return False
        # Read only this process's logs: a previous process has a different URL.
        identity = {
            "container_id": info["Id"],
            "started_at": info["State"]["StartedAt"],
        }
        marker = self.state / "tunnel-applied.json"
        applied = json.loads(marker.read_text()) if marker.exists() else {}
        if any(applied.get(key) != value for key, value in identity.items()):
            self.forget_url()
        logs = run(
            [
                "docker",
                "logs",
                "--since",
                identity["started_at"],
                "--tail",
                "500",
                CONTAINER,
            ]
        )
        hosts = URL_PATTERN.findall(logs.stdout + logs.stderr)
        if not hosts:
            # Startup messages may rotate out; keep a previously verified URL for this process.
            if all(applied.get(key) == value for key, value in identity.items()):
                hosts = [applied["hostname"]]
            else:
                return False
        hostname = hosts[-1]
        if not (self.root / ".deploy-enabled").exists():
            raise ValueError("Staging deployment is disabled; URL was not applied.")
        if self.env_file.stat().st_mode & 0o777 != 0o600:
            raise ValueError("Staging environment must have mode 600.")
        original = self.env_file.read_text()
        if len(re.findall(r"^PUBLIC_DOMAIN=", original, re.MULTILINE)) != 1:
            raise ValueError("Expected exactly one PUBLIC_DOMAIN in .env.staging.")
        updated = re.sub(
            r"^PUBLIC_DOMAIN=[^\n]*",
            f"PUBLIC_DOMAIN={hostname}",
            original,
            flags=re.MULTILINE,
        )
        desired = {**identity, "hostname": hostname}
        if applied == desired and updated == original:
            return True
        sha = (self.state / "current").read_text().strip()
        if not re.fullmatch(r"[a-f0-9]{40}", sha):
            raise ValueError("Missing valid deployed revision.")
        prefix = (self.state / "image-prefix").read_text().strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9./_-]*", prefix):
            raise ValueError("Invalid deployed image prefix.")
        compose = self.root / "releases" / sha / "staging" / "compose.yaml"
        if not compose.is_file():
            raise ValueError("Deployed Compose configuration is missing.")
        atomic_write(self.env_file, updated)
        env = {
            **os.environ,
            "PUBLIC_DOMAIN": hostname,
            "IMAGE_TAG": sha,
            "TAPME_STAGING_ROOT": str(self.root),
            "TAPME_STAGING_IMAGE_PREFIX": prefix,
        }
        # Keep the existing images and volumes; never migrate or pull during URL changes.
        run(
            [
                "docker",
                "compose",
                "--env-file",
                str(self.env_file),
                "-p",
                "flower-crm-staging",
                "-f",
                str(compose),
                "up",
                "-d",
                "--no-deps",
                "--pull",
                "never",
                "--wait",
                "--wait-timeout",
                "180",
                "api",
                "web",
                "worker",
                "beat",
            ],
            env=env,
        )
        run(
            [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--max-time",
                "10",
                "--output",
                "/dev/null",
                "http://127.0.0.1:8090/health/",
            ]
        )
        atomic_write(marker, json.dumps(desired) + "\n")
        atomic_write(self.state / "tunnel-url", f"https://{hostname}/crm-flowers/\n")
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "restart", "sync", "url", "stop"])
    args = parser.parse_args()
    root = Path(
        os.environ.get(
            "TAPME_STAGING_ROOT", str(Path.home() / "apps/flower-crm-staging")
        )
    )
    tunnel = QuickTunnel(root)
    tunnel.state.mkdir(parents=True, exist_ok=True)
    # Share the deployment lock so a URL update cannot race a new develop deployment.
    with (tunnel.state / "deploy.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if args.action == "sync":
                return
            raise RuntimeError(
                "A staging update is running; retry in a minute."
            ) from None
        if args.action == "stop":
            if tunnel.inspect():
                run(["docker", "stop", "--time", "30", CONTAINER])
            tunnel.forget_url()
            return
        if args.action in ("start", "restart"):
            tunnel.start(restart=args.action == "restart")
        else:
            tunnel.sync()
        if args.action != "sync":
            url = tunnel.state / "tunnel-url"
            if not url.exists():
                raise RuntimeError("No ready tunnel URL. Try again after startup.")
            print(url.read_text().strip())


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as exc:
        # Do not echo Docker commands or config values, which can contain private emails.
        message = (
            "Docker or health check failed; inspect staging services."
            if isinstance(exc, subprocess.SubprocessError)
            else str(exc)
        )
        print(message, file=sys.stderr)
        sys.exit(1)
