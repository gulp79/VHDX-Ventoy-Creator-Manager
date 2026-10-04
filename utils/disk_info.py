"""
Disk and filesystem inspection utilities for Windows.
"""

import os
import shutil
import string
import psutil
from typing import Optional, Tuple, Dict, Any, List
from utils.constants import PREFERRED_DRIVE_LETTERS, MIN_FREE_SPACE_HEADROOM_GB


def format_size(bytes_val: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB, TB)."""
    if bytes_val < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_val < 1024.0 or unit == 'PB':
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} B"


def get_disk_space_info(path: str) -> Dict[str, Any]:
    """
    Get total, used, and free disk space for the drive containing `path`.
    Returns dict with keys: total, used, free, percent_used, total_str, free_str, used_str.
    """
    try:
        abs_path = os.path.abspath(path)
        # Find root of the path
        drive = os.path.splitdrive(abs_path)[0]
        check_path = drive + "\\" if drive else abs_path

        usage = shutil.disk_usage(check_path)
        percent = (usage.used / usage.total) * 100 if usage.total > 0 else 0
        return {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent_used": percent,
            "total_str": format_size(usage.total),
            "used_str": format_size(usage.used),
            "free_str": format_size(usage.free),
            "drive": drive
        }
    except Exception as e:
        return {
            "total": 0,
            "used": 0,
            "free": 0,
            "percent_used": 0,
            "total_str": "Unknown",
            "used_str": "Unknown",
            "free_str": "Unknown",
            "drive": "",
            "error": str(e)
        }


def get_used_drive_letters() -> set:
    """Return set of currently assigned uppercase drive letters (e.g. {'C', 'D'})."""
    used = set()
    try:
        partitions = psutil.disk_partitions(all=True)
        for p in partitions:
            if p.device and len(p.device) >= 2 and p.device[1] == ':':
                used.add(p.device[0].upper())
    except Exception:
        # Fallback to os.path.exists checks
        for letter in string.ascii_uppercase:
            if os.path.exists(f"{letter}:\\"):
                used.add(letter)
    return used


def get_available_drive_letters(count: int = 1, preferred: Optional[list] = None) -> List[str]:
    """
    Find and return `count` unused drive letters.
    Tries preferred letters first, then falls back to any available letter from Z to D.
    """
    used = get_used_drive_letters()
    search_list = (preferred or PREFERRED_DRIVE_LETTERS).copy()

    # Append fallback letters
    for letter in reversed(string.ascii_uppercase):
        if letter not in ('A', 'B') and letter not in search_list:
            search_list.append(letter)

    allocated = []
    for letter in search_list:
        upper = letter.upper().strip(":\\")
        if upper not in used and upper not in allocated:
            allocated.append(upper)
            if len(allocated) == count:
                return allocated

    if len(allocated) < count:
        raise RuntimeError(f"Could not find {count} available drive letters on the system.")

    return allocated


def get_available_drive_letter(preferred: Optional[list] = None) -> str:
    """
    Find and return a single unused drive letter.
    """
    return get_available_drive_letters(count=1, preferred=preferred)[0]


def get_filesystem_type(path_or_drive: str) -> str:
    """
    Get the filesystem type (e.g. 'NTFS', 'exFAT', 'FAT32') of the drive.
    """
    try:
        abs_path = os.path.abspath(path_or_drive)
        drive_letter = os.path.splitdrive(abs_path)[0].upper()
        if not drive_letter:
            drive_letter = path_or_drive[:2].upper()

        for partition in psutil.disk_partitions(all=True):
            p_drive = partition.device[:2].upper()
            if p_drive == drive_letter:
                return partition.fstype.upper()
    except Exception:
        pass
    return "UNKNOWN"


def validate_space_headroom(target_dir: str, vhdx_max_size_bytes: int, is_dynamic: bool = True) -> Tuple[bool, str]:
    """
    Check if the host drive has adequate free space for creating and running the VHDX.
    Prevents BSOD VHD_BOOT_INITIALIZATION_FAILED on native boot.
    Returns (is_valid, warning_or_error_message).
    """
    info = get_disk_space_info(target_dir)
    free_bytes = info.get("free", 0)

    if free_bytes == 0:
        return False, "Unable to determine free disk space on the target drive."

    min_headroom_bytes = MIN_FREE_SPACE_HEADROOM_GB * 1024 * 1024 * 1024

    if not is_dynamic:
        # Fixed VHDX: Must have at least max size + headroom
        required = vhdx_max_size_bytes + min_headroom_bytes
        if free_bytes < required:
            return False, (
                f"Insufficient disk space for Fixed VHDX! Free: {format_size(free_bytes)}, "
                f"Required: {format_size(required)} (includes {MIN_FREE_SPACE_HEADROOM_GB} GB safety margin)."
            )
    else:
        # Dynamic VHDX: Must have at least 15GB for initial installation + headroom
        initial_min = 20 * 1024 * 1024 * 1024
        if free_bytes < initial_min:
            return False, (
                f"Critically low disk space! Only {format_size(free_bytes)} free. "
                f"At least {format_size(initial_min)} is needed to apply the Windows image."
            )
        # Check if free space is less than max dynamic size (can cause BSOD on boot if disk fills)
        if free_bytes < vhdx_max_size_bytes:
            return True, (
                f"WARNING: Host drive has {format_size(free_bytes)} free, which is less than "
                f"the VHDX maximum size of {format_size(vhdx_max_size_bytes)}. "
                f"Ensure the host drive does not fill up to prevent BSOD VHD_BOOT_INITIALIZATION_FAILED."
            )

    return True, ""
