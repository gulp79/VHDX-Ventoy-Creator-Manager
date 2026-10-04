# Implementation Plan: Clean Standard OOBE Flow (Registry Tweaks Removal)

Remove the offline registry modification step (`SystemSetupInProgress=0`, `SetupType=0`) to eliminate BSOD `0xc00002e3` (`STATUS_SAM_INIT_FAILURE`), allowing Windows Security Accounts Manager (SAM) and OOBE to initialize cleanly during the first native boot.

---

## User Review Required

> [!IMPORTANT]
> The definitive Master VHDX pipeline preserves the standard Windows image state and GPT partitioning:
> 1. **Diskpart**: Create GPT layout (`EFI 300MB FAT32` + `MSR 16MB` + `OS NTFS`).
> 2. **DISM Apply-Image**: Apply Windows WIM/ESD index with live progress percentage.
> 3. **BCDboot Injection**: Inject bootloader into the EFI partition (`bcdboot <os_letter>:\Windows /s <efi_letter>: /f ALL`).
> 4. **Driver Injection**: Optional offline driver injection (`/Add-Driver /Recurse`).
> 5. **Diskpart Detach**: Clean unmount of VHDX.

---

## Proposed Changes

### 1. Core VHD Engine

#### [MODIFY] [core/vhd_engine.py](file:///d:/Develop/vhdx/core/vhd_engine.py)
- Remove `apply_offline_registry_fix` function to avoid tampering with the offline SAM/Setup state.

---

### 2. Master Pipeline Worker

#### [MODIFY] [ui/workers/master_worker.py](file:///d:/Develop/vhdx/ui/workers/master_worker.py)
- Remove the offline registry fix step from the execution pipeline.
- Preserve the 5-step clean workflow: Diskpart -> DISM -> BCDboot -> Drivers -> Detach.

---

### 3. Test Suite

#### [MODIFY] [tests/test_vhd_engine.py](file:///d:/Develop/vhdx/tests/test_vhd_engine.py)
- Remove obsolete registry fix unit tests.
- Maintain tests verifying the 3-partition GPT Diskpart layout and EFI-targeted BCDboot injection.

---

## Verification Plan

### Automated Tests
- Run `pytest -v tests/` to verify that all remaining unit tests pass without errors.
