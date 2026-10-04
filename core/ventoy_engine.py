"""
Ventoy USB drive detection, plugin management (ventoy_vhdboot.img), and VHDX deployment.
"""

import os
import sys
import time
import shutil
import ctypes
import threading
import requests
import psutil
from typing import List, Dict, Any, Optional, Tuple, Callable
from utils.constants import (
    VENTOY_VHDBOOT_FILENAME,
    VENTOY_VHDBOOT_SUBDIR,
    VENTOY_VHDBOOT_DOWNLOAD_URL,
    VENTOY_VHDBOOT_FALLBACK_URL,
)
from utils.disk_info import format_size, get_filesystem_type


def get_volume_label_windows(drive_letter: str) -> str:
    """Get Windows volume label for a drive (e.g. 'C:\\' -> 'Windows')."""
    if os.name != "nt":
        return ""
    try:
        clean_drive = drive_letter.strip().rstrip("\\") + "\\"
        kernel32 = ctypes.windll.kernel32
        volume_name_buf = ctypes.create_unicode_buffer(1024)
        fs_name_buf = ctypes.create_unicode_buffer(1024)
        serial_num = ctypes.c_ulong()
        max_comp_len = ctypes.c_ulong()
        flags = ctypes.c_ulong()

        res = kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(clean_drive),
            volume_name_buf,
            ctypes.sizeof(volume_name_buf),
            ctypes.byref(serial_num),
            ctypes.byref(max_comp_len),
            ctypes.byref(flags),
            fs_name_buf,
            ctypes.sizeof(fs_name_buf),
        )
        if res:
            return volume_name_buf.value
    except Exception:
        pass
    return ""


def detect_ventoy_drives() -> List[Dict[str, Any]]:
    """
    Detect connected Ventoy USB drives.
    Returns list of dicts with:
      - drive_letter (e.g. 'E:')
      - mount_point (e.g. 'E:\\')
      - label (e.g. 'Ventoy')
      - fstype (e.g. 'NTFS', 'exFAT')
      - is_ntfs (bool)
      - total_size_bytes
      - free_size_bytes
      - is_ventoy_candidate (bool)
      - has_vhdboot_plugin (bool)
      - display_text
    """
    drives = []

    try:
        partitions = psutil.disk_partitions(all=True)
    except Exception:
        partitions = []

    for p in partitions:
        mount = p.mountpoint
        if not mount or not os.path.exists(mount):
            continue

        letter = mount[:2].upper()
        label = get_volume_label_windows(mount)
        fstype = (p.fstype or get_filesystem_type(mount)).upper()

        # Check for presence of Ventoy indicators
        ventoy_dir = os.path.join(mount, VENTOY_VHDBOOT_SUBDIR)
        has_ventoy_dir = os.path.isdir(ventoy_dir)
        is_ventoy_labeled = "VENTOY" in label.upper()

        # Check if plugin is already present
        has_plugin, vhdboot_file, _ = check_vhdboot_plugin(mount)

        # Get size info
        try:
            usage = shutil.disk_usage(mount)
            total = usage.total
            free = usage.free
        except Exception:
            total = 0
            free = 0

        # Don't include tiny bootloader partition (e.g. VTOYEFI ~32MB)
        if total < 500 * 1024 * 1024 and "VTOYEFI" in label.upper():
            continue

        is_candidate = is_ventoy_labeled or has_ventoy_dir or ("removable" in p.opts.lower())

        is_ntfs = (fstype == "NTFS")
        display_label = label if label else "Removable Disk"
        display = f"{letter} [{display_label}] - {fstype} ({format_size(free)} free of {format_size(total)})"
        if is_ventoy_labeled or has_ventoy_dir:
            display = f"★ {display}"

        drives.append({
            "drive_letter": letter,
            "mount_point": mount,
            "label": label,
            "fstype": fstype,
            "is_ntfs": is_ntfs,
            "total_size_bytes": total,
            "free_size_bytes": free,
            "is_ventoy_candidate": is_candidate,
            "has_vhdboot_plugin": has_plugin,
            "plugin_path": vhdboot_file,
            "display_text": display
        })

    # Sort so known Ventoy drives appear at the top
    drives.sort(key=lambda d: (not d["is_ventoy_candidate"], d["drive_letter"]))
    return drives


def check_vhdboot_plugin(ventoy_root: str) -> Tuple[bool, str, int]:
    """
    Check if ventoy_vhdboot.img is installed in <ventoy_root>/ventoy/.
    Returns: Tuple (exists: bool, file_path: str, size_bytes: int)
    """
    plugin_path = os.path.join(ventoy_root, VENTOY_VHDBOOT_SUBDIR, VENTOY_VHDBOOT_FILENAME)
    if os.path.isfile(plugin_path):
        try:
            size = os.path.getsize(plugin_path)
            return True, plugin_path, size
        except Exception:
            return True, plugin_path, 0
    return False, plugin_path, 0


def install_vhdboot_plugin(
    ventoy_root: str,
    on_progress: Optional[Callable[[float, str], None]] = None,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    """
    Download and install ventoy_vhdboot.img plugin into <ventoy_root>/ventoy/.
    """
    ventoy_dir = os.path.join(ventoy_root, VENTOY_VHDBOOT_SUBDIR)
    os.makedirs(ventoy_dir, exist_ok=True)
    target_file = os.path.join(ventoy_dir, VENTOY_VHDBOOT_FILENAME)

    urls = [VENTOY_VHDBOOT_DOWNLOAD_URL, VENTOY_VHDBOOT_FALLBACK_URL]

    if on_line:
        on_line(f"Starting download of {VENTOY_VHDBOOT_FILENAME} into {ventoy_dir}...")

    downloaded = False
    last_err = ""

    for url in urls:
        if cancel_event and cancel_event.is_set():
            return False, "Installation cancelled by user."

        try:
            if on_line:
                on_line(f"Connecting to: {url}")

            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            bytes_written = 0
            chunk_size = 64 * 1024  # 64 KB

            with open(target_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if cancel_event and cancel_event.is_set():
                        f.close()
                        if os.path.exists(target_file):
                            os.remove(target_file)
                        return False, "Installation cancelled by user."

                    if chunk:
                        f.write(chunk)
                        bytes_written += len(chunk)
                        if total_size > 0 and on_progress:
                            pct = (bytes_written / total_size) * 100.0
                            on_progress(pct, f"Downloaded {format_size(bytes_written)} / {format_size(total_size)}")

            downloaded = True
            break
        except Exception as e:
            last_err = str(e)
            if on_line:
                on_line(f"Download attempt from {url} failed: {e}. Trying fallback...")

    if not downloaded:
        return False, f"Failed to download ventoy_vhdboot.img: {last_err}"

    if on_line:
        on_line(f"Plugin successfully installed at: {target_file}")
    if on_progress:
        on_progress(100.0, "Plugin installed successfully")

    return True, f"ventoy_vhdboot.img installed successfully in {ventoy_dir}"


def copy_vhdx_file(
    source_path: str,
    target_dir: str,
    move: bool = False,
    on_progress: Optional[Callable[[float, str], None]] = None,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    """
    Copy or Move large VHDX file to target directory with real-time speed and progress reporting.
    """
    clean_src = os.path.abspath(source_path)
    if not os.path.isfile(clean_src):
        return False, f"Source file does not exist: {clean_src}"

    os.makedirs(target_dir, exist_ok=True)
    filename = os.path.basename(clean_src)
    dest_path = os.path.join(target_dir, filename)

    total_bytes = os.path.getsize(clean_src)
    action_str = "Moving" if move else "Copying"

    if on_line:
        on_line(f"{action_str} '{filename}' ({format_size(total_bytes)}) -> '{target_dir}'")

    # If source and destination are on the same drive and move=True, perform instant rename
    src_drive = os.path.splitdrive(clean_src)[0].upper()
    dest_drive = os.path.splitdrive(dest_path)[0].upper()
    if move and src_drive == dest_drive:
        try:
            shutil.move(clean_src, dest_path)
            if on_progress:
                on_progress(100.0, "Complete (Instant move)")
            if on_line:
                on_line(f"File moved instantly: {dest_path}")
            return True, f"File moved to {dest_path}"
        except Exception as e:
            return False, f"Move failed: {e}"

    # Chunked copy with progress
    buffer_size = 8 * 1024 * 1024  # 8 MB buffer for fast USB 3.0 / NVMe transfers
    copied_bytes = 0
    start_time = time.time()
    last_update_time = start_time

    try:
        with open(clean_src, "rb") as f_in, open(dest_path, "wb") as f_out:
            while True:
                if cancel_event and cancel_event.is_set():
                    f_out.close()
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    return False, "File transfer cancelled by user."

                chunk = f_in.read(buffer_size)
                if not chunk:
                    break

                f_out.write(chunk)
                copied_bytes += len(chunk)

                now = time.time()
                if now - last_update_time >= 0.25 or copied_bytes == total_bytes:
                    elapsed = now - start_time
                    speed = (copied_bytes / elapsed) if elapsed > 0 else 0
                    speed_str = f"{format_size(int(speed))}/s"
                    pct = (copied_bytes / total_bytes) * 100.0 if total_bytes > 0 else 100.0
                    status_text = f"{pct:.1f}% ({format_size(copied_bytes)} / {format_size(total_bytes)}) at {speed_str}"

                    if on_progress:
                        on_progress(pct, status_text)
                    last_update_time = now

        if move:
            try:
                os.remove(clean_src)
                if on_line:
                    on_line(f"Original source file removed: {clean_src}")
            except Exception as e:
                if on_line:
                    on_line(f"Warning: Could not remove original file after copy: {e}")

        if on_line:
            total_time = time.time() - start_time
            avg_speed = (total_bytes / total_time) if total_time > 0 else 0
            on_line(f"Transfer finished in {total_time:.1f}s (Average speed: {format_size(int(avg_speed))}/s)")

        return True, f"VHDX successfully transferred to {dest_path}"

    except Exception as e:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        return False, f"File transfer error: {e}"
