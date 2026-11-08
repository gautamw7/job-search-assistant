"""Process lifecycle helpers for running as a desktop sidecar."""

import os
import sys
import threading
import time

from app.core.logging import get_logger

logger = get_logger(__name__)

PARENT_PID_ENV = "JOB_SEARCH_PARENT_PID"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)  # signal 0: existence check only
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def start_parent_watchdog(interval: float = 2.0) -> None:
    """Exit when the launching app dies.

    A onefile PyInstaller sidecar is a bootloader plus a child; killing the
    bootloader leaves the child (and its port) behind. Watching the app's pid
    guarantees we never outlive it, however it exits.
    """
    raw = os.environ.get(PARENT_PID_ENV)
    if not raw or sys.platform == "win32":
        return
    try:
        parent_pid = int(raw)
    except ValueError:
        return

    def _watch() -> None:
        while True:
            time.sleep(interval)
            if not _pid_alive(parent_pid):
                logger.warning("parent pid=%s gone, shutting down sidecar", parent_pid)
                os._exit(0)

    threading.Thread(target=_watch, name="parent-watchdog", daemon=True).start()
