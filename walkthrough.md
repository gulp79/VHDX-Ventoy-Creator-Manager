# Walkthrough: VHDX Ventoy Creator & Manager (Standard OOBE Flow)

Desktop application in Python (PySide6 / Qt6) for Windows to automate the creation, differential management, and Ventoy USB deployment of VHDX virtual hard disks for native booting.

---

## 🛠️ Pipeline Definitiva Master VHDX (Clean OOBE)

I tweak offline del registro sono stati rimossi per evitare il BSOD `0xc00002e3` (`STATUS_SAM_INIT_FAILURE`) e consentire al Security Accounts Manager (SAM) di Windows e alla procedura di prima inizializzazione (OOBE) di completarsi in modo standard.

### 5 Fasi della Pipeline:

1. **Diskpart**:
   - Creazione VHDX GPT con layout a 3 partizioni:
     1. **Partizione EFI**: 300 MB, FAT32 (`label="System"`), assegnata alla lettera EFI (es. `S:` o `W:`).
     2. **Partizione MSR**: 16 MB (`create partition msr size=16`).
     3. **Partizione OS**: Restante spazio, NTFS (`label="WindowsVHD"`), assegnata alla lettera OS (es. `V:`).
2. **DISM Apply-Image**:
   - Estrazione dell'immagine Windows scelta sul volume OS: `dism /Apply-Image /ImageFile:... /Index:1 /ApplyDir:V:\` con streaming della percentuale di completamento.
3. **BCDBOOT Injection**:
   - Iniezione del bootloader sulla partizione EFI FAT32: `bcdboot V:\Windows /s S: /f ALL`.
4. **DISM Drivers** *(Opzionale)*:
   - Iniezione di driver INF offline se selezionati.
5. **Diskpart Detach**:
   - Smontaggio pulito del disco virtuale (`detach vdisk`).

---

## Verification & Test Results

Tutti i 17 test unitari sono passati con successo:

```
tests/test_disk_info.py::test_format_size PASSED                         [  5%]
tests/test_disk_info.py::test_get_available_drive_letter PASSED          [ 11%]
tests/test_disk_info.py::test_get_available_drive_letters_multiple PASSED [ 17%]
tests/test_disk_info.py::test_validate_space_headroom_dynamic PASSED     [ 23%]
tests/test_disk_info.py::test_validate_space_headroom_fixed PASSED       [ 29%]
tests/test_dism_engine.py::test_parse_wim_info_english PASSED            [ 35%]
tests/test_dism_engine.py::test_parse_wim_info_italian PASSED            [ 41%]
tests/test_dism_engine.py::test_extract_dism_progress PASSED             [ 47%]
tests/test_dism_engine.py::test_apply_image_mock PASSED                  [ 52%]
tests/test_dism_engine.py::test_add_drivers_mock PASSED                  [ 58%]
tests/test_ventoy_engine.py::test_check_vhdboot_plugin_present PASSED    [ 64%]
tests/test_ventoy_engine.py::test_check_vhdboot_plugin_missing PASSED    [ 70%]
tests/test_ventoy_engine.py::test_detect_ventoy_drives_mock PASSED       [ 76%]
tests/test_vhd_engine.py::test_create_master_vhdx_script PASSED          [ 82%]
tests/test_vhd_engine.py::test_create_child_vhdx_script PASSED           [ 88%]
tests/test_vhd_engine.py::test_detach_vhdx_script PASSED                 [ 94%]
tests/test_vhd_engine.py::test_bcdboot_inject_mock PASSED                [100%]

============================= 17 passed in 0.58s ==============================
```
