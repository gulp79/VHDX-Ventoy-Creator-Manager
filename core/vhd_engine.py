"""
VHDX virtual disk and ISO disk image operations via diskpart, bcdboot, and PowerShell.
"""

import os
import sys
import tempfile
import threading
from typing import Optional, Callable, Tuple, List
from core.system_executor import run_command
from utils.constants import DEFAULT_VOLUME_LABEL


def run_diskpart_script(
    script_content: str,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[int, str]:
    """
    Write script_content to a temporary file and execute diskpart /s <temp_file>.
    Cleans up the temporary script file afterwards.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".diskpart", delete=False, encoding="utf-8") as f:
        f.write(script_content.strip() + "\n")
        temp_path = f.name

    try:
        if on_line:
            on_line(f"[CMD] diskpart /s {temp_path}")
        cmd = ["diskpart", "/s", temp_path]
        return run_command(cmd, on_line=on_line, cancel_event=cancel_event)
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


def create_master_vhdx(
    vhdx_path: str,
    size_mb: int,
    vhdx_type: str = "expandable",
    os_drive_letter: str = "V",
    efi_drive_letter: str = "S",
    volume_label: str = DEFAULT_VOLUME_LABEL,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    """
    Create, partition (EFI + MSR + Primary NTFS), format, and mount a Master VHDX with GPT layout.
    
    Structure:
    1. EFI System Partition (300 MB, FAT32, label="System", assigned efi_drive_letter)
    2. MSR Partition (16 MB, Microsoft Reserved)
    3. Primary Partition (Remaining space, NTFS, label=volume_label, assigned os_drive_letter)
    
    Returns:
        Tuple (success: bool, message: str)
    """
    clean_path = os.path.abspath(vhdx_path)
    clean_os = os_drive_letter.strip(":").upper()
    clean_efi = efi_drive_letter.strip(":").upper()

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(clean_path), exist_ok=True)

    # Diskpart script lines
    script = (
        f'create vdisk file="{clean_path}" maximum={size_mb} type={vhdx_type}\n'
        f'select vdisk file="{clean_path}"\n'
        f'attach vdisk\n'
        f'convert gpt\n'
        f'create partition efi size=300\n'
        f'format quick fs=fat32 label="System"\n'
        f'assign letter={clean_efi}\n'
        f'create partition msr size=16\n'
        f'create partition primary\n'
        f'format quick fs=ntfs label="{volume_label}"\n'
        f'assign letter={clean_os}\n'
    )

    exit_code, output = run_diskpart_script(script, on_line=on_line, cancel_event=cancel_event)
    if exit_code != 0:
        return False, f"Diskpart failed (exit code {exit_code}): {output}"

    # Verify that the OS drive letter is now accessible
    target_drive = f"{clean_os}:\\"
    if not os.path.exists(target_drive):
        return False, f"Mounted OS drive {target_drive} is not accessible after diskpart execution."

    return True, f"VHDX created and mounted (OS: {clean_os}:\\, EFI: {clean_efi}:\\)"


def create_child_vhdx(
    parent_path: str,
    child_path: str,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    """
    Create a differential (child) VHDX pointing to an existing parent Master VHDX.
    """
    clean_parent = os.path.abspath(parent_path)
    clean_child = os.path.abspath(child_path)

    if not os.path.isfile(clean_parent):
        return False, f"Parent Master VHDX not found at '{clean_parent}'."

    os.makedirs(os.path.dirname(clean_child), exist_ok=True)

    script = (
        f'create vdisk file="{clean_child}" parent="{clean_parent}"\n'
    )

    exit_code, output = run_diskpart_script(script, on_line=on_line, cancel_event=cancel_event)
    if exit_code != 0:
        return False, f"Failed to create differential disk (code {exit_code}): {output}"

    return True, f"Differential VHDX created successfully at '{clean_child}'"


def attach_vhdx(
    vhdx_path: str,
    drive_letter: Optional[str] = None,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    """Attach an existing VHDX and optionally assign a drive letter."""
    clean_path = os.path.abspath(vhdx_path)
    if not os.path.isfile(clean_path):
        return False, f"VHDX file not found at '{clean_path}'."

    script = f'select vdisk file="{clean_path}"\nattach vdisk\n'
    if drive_letter:
        clean_letter = drive_letter.strip(":").upper()
        script += f'select partition 1\nassign letter={clean_letter}\n'

    exit_code, output = run_diskpart_script(script, on_line=on_line, cancel_event=cancel_event)
    if exit_code != 0:
        return False, f"Failed to attach VHDX (code {exit_code}): {output}"

    return True, f"VHDX attached successfully."


def detach_vhdx(
    vhdx_path: str,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    """Detach/unmount a VHDX virtual disk."""
    clean_path = os.path.abspath(vhdx_path)
    if not os.path.exists(clean_path):
        return False, f"VHDX file not found at '{clean_path}'."

    script = (
        f'select vdisk file="{clean_path}"\n'
        f'detach vdisk\n'
    )

    exit_code, output = run_diskpart_script(script, on_line=on_line, cancel_event=cancel_event)
    if exit_code != 0:
        return False, f"Failed to detach VHDX (code {exit_code}): {output}"

    return True, "VHDX detached successfully."


def bcdboot_inject(
    os_drive_letter: str,
    efi_drive_letter: str,
    firmware_type: str = "ALL",
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    r"""
    Inject Windows BCD boot files into the EFI System Partition of the mounted VHDX.
    Executes: bcdboot <os_letter>:\Windows /s <efi_letter>: /f <firmware_type>
    
    This is CRITICAL for Native VHD Booting under Ventoy / UEFI / BIOS.
    """
    clean_os = os_drive_letter.strip(":").upper()
    clean_efi = efi_drive_letter.strip(":").upper()
    win_dir = f"{clean_os}:\\Windows"
    target_efi = f"{clean_efi}:"

    if not os.path.exists(win_dir):
        return False, f"Windows directory not found at '{win_dir}'. Apply image must precede bcdboot."

    cmd = ["bcdboot", win_dir, "/s", target_efi, "/f", firmware_type]
    if on_line:
        on_line(f"[CMD] {' '.join(cmd)}")

    exit_code, output = run_command(cmd, on_line=on_line, cancel_event=cancel_event)
    if exit_code != 0:
        return False, f"bcdboot failed with exit code {exit_code}: {output}"

    return True, f"BCD boot files successfully injected into EFI partition ({target_efi})"


def mount_iso(
    iso_path: str,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[Optional[str], str]:
    """
    Mount a Windows ISO image using PowerShell Mount-DiskImage.
    Gracefully handles already-mounted ISOs and verifies volume availability.
    Returns: Tuple of (drive_letter_or_None, message)
    """
    clean_path = os.path.abspath(iso_path)
    if not os.path.isfile(clean_path):
        return None, f"ISO file not found: '{clean_path}'"

    # Escape single quotes in path for PowerShell
    escaped_path = clean_path.replace("'", "''")

    ps_script = (
        f"$p = '{escaped_path}'; "
        f"$img = Get-DiskImage -ImagePath $p -ErrorAction SilentlyContinue; "
        f"if (-not $img -or -not $img.Attached) {{ $img = Mount-DiskImage -ImagePath $p -PassThru -ErrorAction Stop }}; "
        f"$vol = Get-Volume -DiskImage $img -ErrorAction SilentlyContinue; "
        f"if (-not $vol) {{ Start-Sleep -Milliseconds 600; $vol = Get-Volume -DiskImage $img -ErrorAction SilentlyContinue }}; "
        f"if ($vol) {{ ($vol | Select-Object -ExpandProperty DriveLetter) -join '' }} else {{ '' }}"
    )
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
    if on_line:
        on_line(f"[CMD] Mounting ISO: {clean_path}")

    exit_code, output = run_command(cmd, on_line=on_line, cancel_event=cancel_event)

    # Extract drive letter from output lines
    for line in output.splitlines():
        letter = line.strip().upper()
        if len(letter) == 1 and letter.isalpha():
            return letter, f"ISO mounted on {letter}:\\"

    # Fallback: check all drives for newly mounted CDROM/virtual drives or matching ISO
    import psutil
    try:
        for p in psutil.disk_partitions(all=True):
            if "cdrom" in p.opts.lower() or "iso" in p.opts.lower():
                if p.device and len(p.device) >= 2 and p.device[1] == ':':
                    letter = p.device[0].upper()
                    # Verify drive actually has sources or is accessible
                    if os.path.exists(f"{letter}:\\"):
                        return letter, f"ISO mounted on {letter}:\\"
    except Exception:
        pass

    if exit_code != 0:
        return None, f"Failed to mount ISO: {output}"

    return None, f"Could not determine mounted drive letter for ISO: {output}"


def unmount_iso(
    iso_path: str,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    """Unmount an ISO image using PowerShell Dismount-DiskImage."""
    clean_path = os.path.abspath(iso_path)
    escaped_path = clean_path.replace("'", "''")
    ps_script = f"Dismount-DiskImage -ImagePath '{escaped_path}' -ErrorAction SilentlyContinue"
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
    if on_line:
        on_line(f"[CMD] Unmounting ISO: {clean_path}")

    exit_code, output = run_command(cmd, on_line=on_line, cancel_event=cancel_event)
    if exit_code != 0:
        return False, f"Failed to unmount ISO: {output}"

    return True, "ISO unmounted successfully."


def find_wim_or_esd_in_drive(drive_letter: str) -> Optional[str]:
    """
    Search for install.wim, install.esd, install.swm or any OS image file inside drive sources or root.
    Supports standard and custom Windows distributions (e.g. Bizarre11, Tiny11).
    """
    clean_letter = drive_letter.strip(":").upper()
    sources_dir = f"{clean_letter}:\\sources"

    candidates = ["install.wim", "install.esd", "install.swm"]
    for cand in candidates:
        full_path = os.path.join(sources_dir, cand)
        if os.path.isfile(full_path):
            return full_path

    # Broad search in root
    for cand in candidates:
        root_path = f"{clean_letter}:\\{cand}"
        if os.path.isfile(root_path):
            return root_path

    # Case-insensitive / custom name search in sources directory
    if os.path.isdir(sources_dir):
        try:
            for item in os.listdir(sources_dir):
                if item.lower().endswith((".wim", ".esd", ".swm")):
                    return os.path.join(sources_dir, item)
        except Exception:
            pass

    return None


def disable_dse_in_bcd(
    efi_drive_letter: str,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    r"""
    Disable Driver Signature Enforcement (DSE) in the VHDX BCD store.

    Operates on the BCD file inside the mounted EFI partition of the VHDX
    (e.g. S:\EFI\Microsoft\Boot\BCD) using 'bcdedit /store <path>'.
    This avoids touching the host system BCD.

    Sets for each Windows Boot Loader entry (winload.efi) found:
        - nointegritychecks on
        - testsigning on
    And for {bootmgr}:
        - nointegritychecks on

    Returns:
        Tuple (success: bool, message: str)
    """
    import re

    clean_efi = efi_drive_letter.strip(":").upper()
    bcd_path = f"{clean_efi}:\\EFI\\Microsoft\\Boot\\BCD"

    if not os.path.exists(bcd_path):
        return False, f"BCD store not found at '{bcd_path}'. Ensure bcdboot_inject was run first."

    if on_line:
        on_line(f"[DSE] Operating on BCD store: {bcd_path}")

    # Step 1: Enumerate all BCD entries
    cmd_enum = ["bcdedit", "/store", bcd_path, "/enum", "all"]
    if on_line:
        on_line(f"[CMD] {' '.join(cmd_enum)}")

    exit_code, output = run_command(cmd_enum, on_line=on_line, cancel_event=cancel_event)
    if exit_code != 0:
        return False, f"bcdedit /enum failed (code {exit_code}): {output}"

    if cancel_event and cancel_event.is_set():
        return False, "Operation cancelled."

    # Step 2: Parse output to find Windows Boot Loader GUIDs with winload.efi
    # bcdedit output blocks are separated by blank lines.
    # Each block starts with a type line, dashes, then key-value pairs.
    identifier_pattern = re.compile(r'identifier\s+(\{[^}]+\})', re.IGNORECASE)
    path_pattern = re.compile(r'^\s*path\s+.*winload\.efi', re.IGNORECASE | re.MULTILINE)

    # Normalize line endings and split into blocks
    normalized = output.replace('\r\n', '\n').replace('\r', '\n')
    blocks = re.split(r'\n\s*\n', normalized)

    loader_guids = []
    for block in blocks:
        if path_pattern.search(block):
            id_match = identifier_pattern.search(block)
            if id_match:
                guid = id_match.group(1).strip()
                if guid not in loader_guids:
                    loader_guids.append(guid)

    if not loader_guids:
        # Soft warning: no winload.efi entries found, fallback to {default}
        if on_line:
            on_line("[DSE] WARNING: No winload.efi entries found in BCD. Attempting fallback on {default}.")
        loader_guids = ["{default}"]

    if on_line:
        on_line(f"[DSE] Found {len(loader_guids)} Windows Boot Loader entry/entries: {', '.join(loader_guids)}")

    errors = []

    # Step 3: Apply DSE-disable flags to each Windows Boot Loader entry
    for guid in loader_guids:
        if cancel_event and cancel_event.is_set():
            return False, "Operation cancelled."

        for flag_name, flag_value in [("nointegritychecks", "on"), ("testsigning", "on")]:
            cmd = ["bcdedit", "/store", bcd_path, "/set", guid, flag_name, flag_value]
            if on_line:
                on_line(f"[CMD] {' '.join(cmd)}")
            rc, out = run_command(cmd, on_line=on_line, cancel_event=cancel_event)
            if rc != 0:
                err = f"bcdedit /set {guid} {flag_name} {flag_value} failed (code {rc}): {out}"
                errors.append(err)
                if on_line:
                    on_line(f"[DSE] WARNING: {err}")

    # Step 4: Apply nointegritychecks to {bootmgr}
    if cancel_event and cancel_event.is_set():
        return False, "Operation cancelled."

    cmd_bmgr = ["bcdedit", "/store", bcd_path, "/set", "{bootmgr}", "nointegritychecks", "on"]
    if on_line:
        on_line(f"[CMD] {' '.join(cmd_bmgr)}")
    rc_bmgr, out_bmgr = run_command(cmd_bmgr, on_line=on_line, cancel_event=cancel_event)
    if rc_bmgr != 0:
        err = f"bcdedit /set {{bootmgr}} nointegritychecks on failed (code {rc_bmgr}): {out_bmgr}"
        errors.append(err)
        if on_line:
            on_line(f"[DSE] WARNING: {err}")

    if errors:
        return True, f"DSE disable completed with {len(errors)} warning(s): {'; '.join(errors)}"

    applied = ", ".join(loader_guids + ["{bootmgr}"])
    return True, f"DSE disabled successfully (nointegritychecks + testsigning) on: {applied}"
