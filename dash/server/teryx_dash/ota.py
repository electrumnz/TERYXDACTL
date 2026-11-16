"""Over-the-air updates for the dash (and the control box firmware), over the Pi's Wi-Fi.

How it works on the Pi (see dash/README.md for setup):

    /opt/teryx/repo        a git clone of the project (fetches new tags)
    /opt/teryx/releases/   one folder per installed version (git worktrees, read only)
    /opt/teryx/current  -> releases/vX.Y.Z   (what the service runs)
    /opt/teryx/ota.json    state: current, previous, pending, boot attempts

Releases are git tags: `v1.2.0` is stable, `v1.3.0-beta.1` is beta.
Install = add a worktree for the tag, flip the `current` link, restart the service.
The new version must stay up for HEALTHY_AFTER_S seconds to be marked good. If it fails to
start twice, `python -m teryx_dash.ota boot-check` (run by systemd before each start) flips
back to the previous version. So a bad update can't leave the Teryx without a dash.

Control box firmware: the release's UF2 file is flashed over USB with picotool (or the
command in TERYX_PICO_FLASH_CMD). The Pico keeps every output off while in its bootloader.

Updates only install with the Teryx stopped. Checking is always allowed.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

HEALTHY_AFTER_S = 60
MAX_BOOT_ATTEMPTS = 2
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-beta\.(\d+))?$")


def parse_tag(tag: str) -> tuple | None:
    m = TAG_RE.match(tag.strip())
    if not m:
        return None
    a, b, c, beta = m.groups()
    # A beta sorts before its release: v1.3.0-beta.2 < v1.3.0
    return (int(a), int(b), int(c), 0 if beta else 1, int(beta or 0))


def newest(tags: list[str], channel: str) -> str | None:
    ok = [t for t in tags if parse_tag(t) and (channel == "beta" or "-beta" not in t)]
    return max(ok, key=parse_tag) if ok else None


@dataclass
class OtaConfig:
    root: Path = Path(os.environ.get("TERYX_OTA_ROOT", "/opt/teryx"))
    remote: str = os.environ.get("TERYX_OTA_REMOTE", "origin")
    restart_cmd: str = os.environ.get("TERYX_RESTART_CMD", "sudo -n systemctl restart teryx-dash")
    pico_flash_cmd: str = os.environ.get("TERYX_PICO_FLASH_CMD", "picotool load -x -f {uf2}")
    uf2_glob: str = os.environ.get("TERYX_PICO_UF2", "firmware/**/*.uf2")

    @property
    def repo(self) -> Path: return self.root / "repo"
    @property
    def releases(self) -> Path: return self.root / "releases"
    @property
    def current_link(self) -> Path: return self.root / "current"
    @property
    def state_file(self) -> Path: return self.root / "ota.json"


async def run(*args: str, cwd: Path | None = None, timeout: float = 300) -> str:
    proc = await asyncio.create_subprocess_exec(*args, cwd=str(cwd) if cwd else None,
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"{args[0]} timed out")
    text = out.decode(errors="replace").strip()
    if proc.returncode != 0:
        raise RuntimeError(text.splitlines()[-1] if text else f"{args[0]} failed ({proc.returncode})")
    return text


def load_state(cfg: OtaConfig) -> dict:
    try:
        return json.loads(cfg.state_file.read_text())
    except Exception:
        return {}


def save_state(cfg: OtaConfig, st: dict) -> None:
    cfg.root.mkdir(parents=True, exist_ok=True)
    tmp = cfg.state_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=2))
    os.replace(tmp, cfg.state_file)  # atomic, so a power cut can't leave half a file


def current_version(cfg: OtaConfig) -> str:
    try:
        return Path(os.readlink(cfg.current_link)).name
    except OSError:
        return load_state(cfg).get("current") or os.environ.get("TERYX_VERSION", "dev")


def switch_to(cfg: OtaConfig, version: str) -> None:
    target = cfg.releases / version
    if not target.is_dir():
        raise RuntimeError(f"version {version} isn't installed")
    tmp = cfg.root / "current.new"
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    tmp.symlink_to(target)
    os.replace(tmp, cfg.current_link)  # atomic link swap


@dataclass
class Ota:
    cfg: OtaConfig = field(default_factory=OtaConfig)
    is_stopped: Callable[[], bool] = lambda: True
    pico_version: Callable[[], str | None] = lambda: None
    state: str = "idle"          # idle | checking | downloading | installing | flashing | restarting | error
    message: str = ""
    progress: int | None = None
    available: str | None = None
    notes: str = ""
    channel: str = "stable"
    pico_available: str | None = None
    _task: asyncio.Task | None = None

    def status(self) -> dict:
        st = load_state(self.cfg)
        cur = current_version(self.cfg)
        return {
            "state": self.state, "message": self.message, "progress": self.progress,
            "dash": {"current": cur, "available": self.available if self.available != cur else None,
                     "notes": self.notes, "previous": st.get("previous")},
            "pico": {"current": self.pico_version() or "?", "available": self.pico_available},
        }

    def _busy(self) -> bool:
        return self._task is not None and not self._task.done()

    def _start(self, coro) -> None:
        if self._busy():
            raise RuntimeError("an update job is already running")
        self._task = asyncio.ensure_future(self._guard(coro))

    async def _guard(self, coro) -> None:
        try:
            await coro
        except Exception as e:  # shown on the Updates screen
            self.state, self.message, self.progress = "error", f"Update failed: {e}", None

    # ---- check ----
    def check(self, channel: str = "stable") -> None:
        self.channel = channel
        self._start(self._check())

    async def _check(self) -> None:
        self.state, self.message, self.progress = "checking", "Checking for updates…", None
        if not (self.cfg.repo / ".git").exists():
            raise RuntimeError(f"updates aren't set up on this machine (no {self.cfg.repo}). See dash/README.md")
        await run("git", "fetch", "--tags", "--force", "--prune", self.cfg.remote, cwd=self.cfg.repo, timeout=60)
        tags = (await run("git", "tag", "--list", "v*", cwd=self.cfg.repo)).split()
        best = newest(tags, self.channel)
        cur = current_version(self.cfg)
        if best and parse_tag(cur) and parse_tag(best) <= parse_tag(cur):
            best = None
        self.available = best
        self.notes = ""
        if best:
            try:
                self.notes = (await run("git", "tag", "-l", "--format=%(contents:subject)", best, cwd=self.cfg.repo))[:140]
            except RuntimeError:
                pass
        self.pico_available = await self._pico_update_in(best or cur)
        self.state = "idle"
        self.message = f"{best} is ready to install." if best else "You're on the latest version."

    async def _pico_update_in(self, version: str) -> str | None:
        """A newer control box firmware ships with a release if its version file differs from what the Pico reports."""
        try:
            fw = (await run("git", "show", f"{version}:firmware/VERSION", cwd=self.cfg.repo)).strip()
        except RuntimeError:
            return None
        return fw if fw and fw != (self.pico_version() or "") else None

    # ---- install ----
    def install(self, target: str = "dash") -> None:
        if not self.is_stopped():
            raise RuntimeError("stop the Teryx before installing updates")
        if target == "pico":
            self._start(self._flash_pico())
        else:
            if not self.available:
                raise RuntimeError("nothing to install, check for updates first")
            self._start(self._install(self.available))

    async def _install(self, version: str) -> None:
        cfg = self.cfg
        self.state, self.message, self.progress = "downloading", f"Getting {version}…", 10
        dest = cfg.releases / version
        cfg.releases.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            await run("git", "worktree", "add", "--detach", "--force", str(dest), version, cwd=cfg.repo, timeout=300)
        self.state, self.message, self.progress = "installing", f"Installing {version}…", 60
        setup = dest / "dash" / "deploy" / "post-install.sh"
        if setup.exists():
            await run("bash", str(setup), cwd=dest, timeout=600)
        self.progress = 90
        if not self.is_stopped():
            raise RuntimeError("the Teryx moved, update stopped before switching over")
        prev = current_version(cfg)
        switch_to(cfg, version)
        save_state(cfg, {"current": version, "previous": prev if prev != version else load_state(cfg).get("previous"),
                         "pending": version, "attempts": 0, "since": time.time()})
        self.state, self.message, self.progress = "restarting", f"Restarting on {version}…", 100
        self.available = None
        await asyncio.sleep(1)
        await run(*shlex.split(cfg.restart_cmd), timeout=30)

    def rollback(self) -> None:
        if not self.is_stopped():
            raise RuntimeError("stop the Teryx first")
        self._start(self._rollback())

    async def _rollback(self) -> None:
        st = load_state(self.cfg)
        prev = st.get("previous")
        if not prev:
            raise RuntimeError("no earlier version to go back to")
        cur = current_version(self.cfg)
        switch_to(self.cfg, prev)
        save_state(self.cfg, {"current": prev, "previous": cur, "pending": None, "attempts": 0})
        self.state, self.message = "restarting", f"Going back to {prev}…"
        await run(*shlex.split(self.cfg.restart_cmd), timeout=30)

    async def _flash_pico(self) -> None:
        here = self.cfg.current_link if self.cfg.current_link.exists() else Path.cwd()
        uf2s = sorted(here.glob(self.cfg.uf2_glob))
        if not uf2s:
            raise RuntimeError("no control box firmware (.uf2) in this release")
        self.state, self.message, self.progress = "flashing", "Updating the control box. Everything it runs is off until it's back…", 30
        cmd = [a.replace("{uf2}", str(uf2s[-1])) for a in shlex.split(self.cfg.pico_flash_cmd)]
        await run(*cmd, timeout=180)
        self.state, self.message, self.progress = "idle", "Control box updated.", None
        self.pico_available = None

    # ---- after a restart ----
    async def confirm_when_healthy(self, healthy: Callable[[], bool]) -> None:
        """Called once at start up. Marks a pending update as good after it's been up a while."""
        st = load_state(self.cfg)
        if not st.get("pending"):
            return
        await asyncio.sleep(HEALTHY_AFTER_S)
        if healthy():
            st = load_state(self.cfg)
            st["pending"], st["attempts"] = None, 0
            save_state(self.cfg, st)


def boot_check(cfg: OtaConfig | None = None) -> str:
    """Run by systemd before each start (ExecStartPre). Rolls back an update that keeps failing."""
    cfg = cfg or OtaConfig()
    st = load_state(cfg)
    if not st.get("pending"):
        return "ok"
    st["attempts"] = int(st.get("attempts", 0)) + 1
    if st["attempts"] > MAX_BOOT_ATTEMPTS and st.get("previous"):
        bad = st["pending"]
        switch_to(cfg, st["previous"])
        st = {"current": st["previous"], "previous": None, "pending": None, "attempts": 0, "rolled_back_from": bad}
        save_state(cfg, st)
        return f"rolled back from {bad}"
    save_state(cfg, st)
    return f"pending, attempt {st['attempts']}"


if __name__ == "__main__":
    if sys.argv[1:] == ["boot-check"]:
        print(boot_check())
    else:
        print("usage: python -m teryx_dash.ota boot-check")
