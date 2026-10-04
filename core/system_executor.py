"""
Subprocess execution manager with real-time stdout/stderr streaming and encoding handling.
"""

import os
import sys
import subprocess
import threading
from typing import Callable, Optional, List, Tuple


def get_windows_encoding() -> str:
    """Return appropriate Windows OEM encoding (typically cp850 or cp1252 on Italian/Western Windows)."""
    try:
        import ctypes
        oem_cp = ctypes.windll.kernel32.GetOEMCP()
        return f"cp{oem_cp}"
    except Exception:
        return "cp850"


def run_command(
    cmd: List[str] | str,
    on_line: Optional[Callable[[str], None]] = None,
    on_error_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    cwd: Optional[str] = None,
    shell: bool = False
) -> Tuple[int, str]:
    """
    Execute a system command and stream its output in real-time.
    
    Args:
        cmd: List of command arguments or shell command string.
        on_line: Callback invoked for each stdout line.
        on_error_line: Callback invoked for each stderr line (defaults to on_line if None).
        cancel_event: Optional threading.Event to abort execution.
        cwd: Working directory.
        shell: Run command via shell.
        
    Returns:
        Tuple of (exit_code, full_combined_output)
    """
    if on_error_line is None:
        on_error_line = on_line

    startupinfo = None
    creationflags = 0

    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Combine stdout and stderr for unified sequential stream
        stdin=subprocess.PIPE,
        cwd=cwd,
        shell=shell,
        startupinfo=startupinfo,
        creationflags=creationflags
    )

    encoding = get_windows_encoding()
    output_lines = []

    def decode_bytes(raw: bytes) -> str:
        for enc in [encoding, "utf-8", "cp1252", "latin-1", "ascii"]:
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("latin-1", errors="replace")

    # Read line by line or character chunk
    try:
        while True:
            if cancel_event and cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                return -1, "\n".join(output_lines) + "\n[Operation cancelled by user]"

            # Read raw line
            raw_line = process.stdout.readline() if process.stdout else b""
            if not raw_line and process.poll() is not None:
                break

            if raw_line:
                # Some Windows tools like DISM update progress via carriage return '\r'
                # Handle \r split
                text = decode_bytes(raw_line)
                # If there are \r inside, process sub-parts
                subparts = text.replace("\r\n", "\n").split("\r")
                for part in subparts:
                    cleaned = part.strip()
                    if cleaned:
                        output_lines.append(cleaned)
                        if on_line:
                            on_line(cleaned)

        exit_code = process.wait()
        return exit_code, "\n".join(output_lines)

    except Exception as e:
        if process.poll() is None:
            process.kill()
        error_msg = f"Execution error: {str(e)}"
        if on_error_line:
            on_error_line(error_msg)
        return -1, "\n".join(output_lines) + f"\n{error_msg}"
