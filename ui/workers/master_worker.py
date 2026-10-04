"""
Master VHDX Creation Worker Thread (QThread).
Executes the full 5-step pipeline:
1. Space validation & Diskpart VHDX creation/partition/format/mount
2. DISM Apply-Image with live progress percentage
3. BCDboot injection (CRITICAL for native VHD boot)
4. Optional Driver injection via DISM
5. Clean detachment of VHDX and ISO unmount
"""

import os
import threading
from PySide6.QtCore import QThread, Signal
from core.vhd_engine import (
    create_master_vhdx,
    detach_vhdx,
    bcdboot_inject,
    mount_iso,
    unmount_iso,
    find_wim_or_esd_in_drive
)
from core.dism_engine import apply_image, add_drivers
from utils.disk_info import get_available_drive_letters, validate_space_headroom, format_size


class MasterCreationWorker(QThread):
    progress_changed = Signal(int)           # 0 - 100
    status_changed = Signal(str)             # High-level step description
    log_event = Signal(str, str)             # (message, level)
    task_finished = Signal(bool, str)        # (success, message)

    def __init__(
        self,
        source_path: str,
        edition_index: int,
        target_vhdx_path: str,
        size_gb: int,
        vhdx_type: str = "expandable",
        driver_dir: str = "",
        volume_label: str = "WindowsVHD",
        parent=None
    ):
        super().__init__(parent)
        self.source_path = source_path
        self.edition_index = edition_index
        self.target_vhdx_path = target_vhdx_path
        self.size_gb = size_gb
        self.size_mb = size_gb * 1024
        self.vhdx_type = vhdx_type
        self.driver_dir = driver_dir
        self.volume_label = volume_label
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()
        self.log_event.emit("Cancellation requested...", "WARNING")

    def run(self):
        mounted_iso_path = None
        assigned_letter = None
        vhdx_created = False

        try:
            self.log_event.emit("=== Starting Master VHDX Creation Pipeline ===", "INFO")
            self.progress_changed.emit(2)
            self.status_changed.emit("Validating storage requirements...")

            # 1. Validation & Safety Checks
            dest_dir = os.path.dirname(os.path.abspath(self.target_vhdx_path))
            size_bytes = self.size_gb * 1024 * 1024 * 1024
            is_dynamic = (self.vhdx_type.lower() == "expandable")

            is_safe, warn_msg = validate_space_headroom(dest_dir, size_bytes, is_dynamic=is_dynamic)
            if not is_safe:
                self.log_event.emit(warn_msg, "ERROR")
                self.task_finished.emit(False, warn_msg)
                return

            if warn_msg:
                self.log_event.emit(warn_msg, "WARNING")

            # Determine available drive letters for mounting VHDX (OS partition + EFI partition)
            drive_letters = get_available_drive_letters(count=2)
            os_letter, efi_letter = drive_letters[0], drive_letters[1]
            self.log_event.emit(f"Allocated virtual drive letters: OS -> {os_letter}:\\, EFI -> {efi_letter}:\\", "INFO")

            # 2. Source Image Resolution (ISO vs WIM/ESD)
            image_file = self.source_path
            ext = os.path.splitext(self.source_path)[1].lower()

            if ext == ".iso":
                self.status_changed.emit("Mounting Windows ISO...")
                self.log_event.emit(f"Mounting ISO: {self.source_path}", "INFO")
                iso_drive, msg = mount_iso(
                    self.source_path,
                    on_line=lambda l: self.log_event.emit(l, "RAW"),
                    cancel_event=self.cancel_event
                )
                if not iso_drive:
                    self.task_finished.emit(False, f"ISO mount failed: {msg}")
                    return

                mounted_iso_path = self.source_path
                self.log_event.emit(f"ISO successfully mounted on {iso_drive}:\\", "SUCCESS")

                found_wim = find_wim_or_esd_in_drive(iso_drive)
                if not found_wim:
                    self.task_finished.emit(False, f"Could not find install.wim/install.esd in mounted ISO ({iso_drive}:\\)")
                    return
                image_file = found_wim
                self.log_event.emit(f"Found image file in ISO: {image_file}", "INFO")

            if not os.path.isfile(image_file):
                self.task_finished.emit(False, f"Image file not found: {image_file}")
                return

            if self.cancel_event.is_set():
                self.task_finished.emit(False, "Operation cancelled by user.")
                return

            # 3. Diskpart: Create, Partition (EFI+MSR+OS), Format, and Mount VHDX
            self.progress_changed.emit(10)
            self.status_changed.emit(f"Creating & partitioning {self.size_gb} GB VHDX ({self.vhdx_type})...")
            self.log_event.emit(f"Creating VHDX at '{self.target_vhdx_path}' ({self.size_gb} GB, {self.vhdx_type})...", "INFO")

            success, msg = create_master_vhdx(
                vhdx_path=self.target_vhdx_path,
                size_mb=self.size_mb,
                vhdx_type=self.vhdx_type,
                os_drive_letter=os_letter,
                efi_drive_letter=efi_letter,
                volume_label=self.volume_label,
                on_line=lambda l: self.log_event.emit(l, "RAW"),
                cancel_event=self.cancel_event
            )
            if not success:
                self.log_event.emit(msg, "ERROR")
                self.task_finished.emit(False, msg)
                return

            vhdx_created = True
            self.log_event.emit(f"VHDX created and mounted (OS: {os_letter}:\\, EFI: {efi_letter}:\\)", "SUCCESS")
            self.progress_changed.emit(20)

            if self.cancel_event.is_set():
                self.task_finished.emit(False, "Operation cancelled by user.")
                return

            # 4. DISM: Apply Windows Image with progress parsing
            self.status_changed.emit(f"Applying Windows Image (Index {self.edition_index})...")
            self.log_event.emit(f"Applying Image: {image_file} (Index {self.edition_index}) to {os_letter}:\\", "INFO")

            def on_dism_progress(pct: float):
                # Map DISM 0-100% to overall progress 20% -> 80%
                overall = int(20 + (pct * 0.6))
                self.progress_changed.emit(overall)
                self.status_changed.emit(f"Applying Windows Image: {pct:.1f}%")

            success, msg = apply_image(
                image_file=image_file,
                index=self.edition_index,
                apply_dir=f"{os_letter}:\\",
                on_progress=on_dism_progress,
                on_line=lambda l: self.log_event.emit(l, "RAW"),
                cancel_event=self.cancel_event
            )
            if not success:
                self.log_event.emit(msg, "ERROR")
                self.task_finished.emit(False, msg)
                return

            self.log_event.emit("Windows Image applied successfully!", "SUCCESS")
            self.progress_changed.emit(80)

            if self.cancel_event.is_set():
                self.task_finished.emit(False, "Operation cancelled by user.")
                return

            # 5. CRITICAL: Inject BCD Bootloader Files into EFI System Partition
            self.status_changed.emit("Injecting BCD bootloader files to EFI partition (bcdboot)...")
            self.log_event.emit(f"Injecting BCD boot configuration (bcdboot {os_letter}:\\Windows /s {efi_letter}: /f ALL)", "INFO")

            success, msg = bcdboot_inject(
                os_drive_letter=os_letter,
                efi_drive_letter=efi_letter,
                firmware_type="ALL",
                on_line=lambda l: self.log_event.emit(l, "RAW"),
                cancel_event=self.cancel_event
            )
            if not success:
                self.log_event.emit(msg, "ERROR")
                self.task_finished.emit(False, msg)
                return

            self.log_event.emit("BCD bootloader files injected successfully into EFI partition", "SUCCESS")
            self.progress_changed.emit(88)

            # 6. Optional: Inject Additional Device Drivers
            if self.driver_dir and os.path.isdir(self.driver_dir):
                self.status_changed.emit("Injecting offline device drivers...")
                self.log_event.emit(f"Injecting drivers from '{self.driver_dir}'...", "INFO")
                drv_success, drv_msg = add_drivers(
                    image_dir=f"{os_letter}:\\",
                    driver_folder=self.driver_dir,
                    on_line=lambda l: self.log_event.emit(l, "RAW"),
                    cancel_event=self.cancel_event
                )
                if drv_success:
                    self.log_event.emit("Drivers injected successfully.", "SUCCESS")
                else:
                    self.log_event.emit(f"Driver injection warning: {drv_msg}", "WARNING")

            self.progress_changed.emit(94)

            # 7. Detach VHDX
            self.status_changed.emit("Detaching VHDX...")
            self.log_event.emit(f"Detaching VHDX ({os_letter}:\\, {efi_letter}:\\)...", "INFO")
            detach_success, detach_msg = detach_vhdx(
                self.target_vhdx_path,
                on_line=lambda l: self.log_event.emit(l, "RAW")
            )
            if detach_success:
                self.log_event.emit("VHDX detached cleanly.", "SUCCESS")
            else:
                self.log_event.emit(f"Detach notice: {detach_msg}", "WARNING")

            self.progress_changed.emit(100)
            self.status_changed.emit("Master VHDX Creation Completed Successfully!")
            self.log_event.emit("=== Pipeline Completed Successfully ===", "SUCCESS")
            self.task_finished.emit(True, f"Master VHDX created successfully at:\n{self.target_vhdx_path}")

        except Exception as e:
            self.log_event.emit(f"Unexpected pipeline exception: {str(e)}", "ERROR")
            self.task_finished.emit(False, str(e))

        finally:
            # Cleanup ISO mount if needed
            if mounted_iso_path:
                try:
                    self.log_event.emit("Cleaning up ISO mount...", "INFO")
                    unmount_iso(mounted_iso_path, on_line=lambda l: self.log_event.emit(l, "RAW"))
                except Exception:
                    pass
