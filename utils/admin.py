"""
UAC Administrator privilege detection and elevation handling on Windows.
"""

import sys
import ctypes
import os
import subprocess


def is_admin() -> bool:
    """Check if the current process has administrative privileges."""
    try:
        if os.name != "nt":
            return os.geteuid() == 0  # type: ignore[attr-defined]
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin_elevation(params: str = "") -> bool:
    """
    Relaunch the current application requesting UAC elevation (Run as administrator).
    Returns True if elevation process was successfully spawned, False otherwise.
    """
    if is_admin():
        return True

    if os.name != "nt":
        return False

    try:
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen:
            executable = sys.executable
            args = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        else:
            executable = sys.executable
            script = os.path.abspath(sys.argv[0])
            args = f'"{script}" ' + " ".join([f'"{arg}"' for arg in sys.argv[1:]])

        if params:
            args = f"{args} {params}".strip()

        # Use ShellExecuteW with 'runas' verb to trigger UAC prompt
        hinstance = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            args.strip(),
            None,
            1  # SW_SHOWNORMAL
        )
        return int(hinstance) > 32
    except Exception as e:
        print(f"Failed to elevate process: {e}", file=sys.stderr)
        return False
