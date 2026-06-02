"""
Minimal system-tray app for wechat-acp on Windows.

Features:
- Green icon when daemon is running, gray when stopped.
- Tray menu: Start / Stop / Restart / Show log / Open config dir / Quit.
- Periodic status polling via `wechat-acp status`.
- Configurable agent preset / cwd / instance via CONFIG dict (or wechat-acp-tray.json).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

# ---------- config ----------

CONFIG_PATH = Path.home() / ".wechat-acp" / "tray-config.json"
DEFAULT_CONFIG = {
    "agent": "copilot",
    "cwd": "",          # empty = don't pass --cwd
    "instance": "",     # empty = default instance
    "poll_seconds": 5,
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[tray] failed to read {CONFIG_PATH}: {e}", file=sys.stderr)
    return cfg


CONFIG = load_config()


# ---------- wechat-acp wrappers ----------

# On Windows, npm global commands are .cmd files -> need shell=True.
USE_SHELL = os.name == "nt"


def _instance_args() -> list[str]:
    return ["--instance", CONFIG["instance"]] if CONFIG.get("instance") else []


def _run(args: list[str], capture: bool = True, **kw) -> subprocess.CompletedProcess:
    cmd = ["wechat-acp", *args]
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        shell=USE_SHELL,
        # Prevent console flash on Windows when launched from pythonw.
        creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        **kw,
    )


def acp_status() -> tuple[bool, str]:
    """Return (is_running, raw_text)."""
    try:
        r = _run(["status", *_instance_args()])
        out = (r.stdout or "").strip() + (r.stderr or "").strip()
        return ("Running" in out, out or "(no output)")
    except FileNotFoundError:
        return (False, "wechat-acp not found in PATH")
    except Exception as e:
        return (False, f"error: {e}")


def acp_start() -> str:
    args = ["--agent", CONFIG["agent"], "--daemon", *_instance_args()]
    # Resolve cwd: explicit config > tray's launch cwd
    cwd = CONFIG.get("cwd") or os.getcwd()
    args += ["--cwd", cwd]
    try:
        r = _run(args)
        return ((r.stdout or "") + (r.stderr or "")).strip() or f"started (cwd={cwd})"
    except Exception as e:
        return f"start error: {e}"


def acp_stop() -> str:
    try:
        r = _run(["stop", *_instance_args()])
        return ((r.stdout or "") + (r.stderr or "")).strip() or "stopped"
    except Exception as e:
        return f"stop error: {e}"


# ---------- icon rendering ----------

def make_icon(running: bool) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = (40, 200, 80, 255) if running else (140, 140, 140, 255)
    d.ellipse((6, 6, size - 6, size - 6), fill=color, outline=(30, 30, 30, 255), width=2)
    # White "W"
    d.text((18, 14), "W", fill=(255, 255, 255, 255))
    return img


# ---------- log / config helpers ----------

def _instance_dir() -> Path:
    base = Path.home() / ".wechat-acp"
    inst = CONFIG.get("instance")
    return base / "instances" / inst if inst else base


def open_log(_icon=None, _item=None):
    log = _instance_dir() / "daemon.log"
    if not log.exists():
        _notify(_icon, "Log not found", str(log))
        return
    os.startfile(str(log))  # noqa: SIM115  (Windows only API; that's fine here)


def open_config_dir(_icon=None, _item=None):
    d = _instance_dir()
    d.mkdir(parents=True, exist_ok=True)
    os.startfile(str(d))


def _notify(icon, title: str, msg: str):
    try:
        if icon is not None:
            icon.notify(msg, title)
    except Exception:
        pass
    print(f"[tray] {title}: {msg}")


# ---------- menu actions ----------

state_lock = threading.Lock()
last_running = False


def action_start(icon, item):
    msg = acp_start()
    _notify(icon, "wechat-acp start", msg)
    refresh_now(icon)


def action_stop(icon, item):
    msg = acp_stop()
    _notify(icon, "wechat-acp stop", msg)
    refresh_now(icon)


def action_restart(icon, item):
    acp_stop()
    time.sleep(1.0)
    msg = acp_start()
    _notify(icon, "wechat-acp restart", msg)
    refresh_now(icon)


def action_quit(icon, item):
    # Do NOT stop the daemon on quit by default; daemon is independent.
    # If you want quit-also-stops, uncomment:
    # acp_stop()
    icon.stop()


def refresh_now(icon):
    running, text = acp_status()
    with state_lock:
        global last_running
        last_running = running
    icon.icon = make_icon(running)
    icon.title = f"wechat-acp: {'Running ✅' if running else 'Stopped ⛔'}\n{text[:200]}"


def poll_loop(icon):
    while True:
        try:
            refresh_now(icon)
        except Exception as e:
            print(f"[tray] poll error: {e}", file=sys.stderr)
        time.sleep(max(2, int(CONFIG.get("poll_seconds", 5))))


# ---------- main ----------

def main():
    menu = pystray.Menu(
        pystray.MenuItem(
            lambda _: f"Status: {'Running ✅' if last_running else 'Stopped ⛔'}",
            None,
            enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start", action_start),
        pystray.MenuItem("Stop", action_stop),
        pystray.MenuItem("Restart", action_restart),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Show log", open_log),
        pystray.MenuItem("Open config dir", open_config_dir),
        pystray.MenuItem("Refresh", lambda icon, item: refresh_now(icon)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", action_quit),
    )

    icon = pystray.Icon(
        "wechat-acp-tray",
        make_icon(False),
        "wechat-acp: starting...",
        menu,
    )

    threading.Thread(target=poll_loop, args=(icon,), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    main()
