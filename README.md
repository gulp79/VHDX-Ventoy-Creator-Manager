[![GitHub release](https://img.shields.io/github/v/release/gulp79/VHDX-Ventoy-Creator-Manager?include_prereleases)](https://github.com/gulp79/VHDX-Ventoy-Creator-Manager/releases/latest)  ![Total Downloads](https://img.shields.io/github/downloads/gulp79/VHDX-Ventoy-Creator-Manager/total)  ![Latest Downloads](https://img.shields.io/github/downloads/gulp79/VHDX-Ventoy-Creator-Manager/latest/total)
# VHDX Ventoy Creator & Manager

A modern desktop application built with Python and PySide6 (Qt6) to automate the creation, differential disk management, and Ventoy USB deployment of Windows VHDX virtual hard drives for **Native Boot**.  

## Overview

Booting Windows directly from a VHDX file (Native Boot) provides bare-metal performance—giving full access to system CPU, GPU, and RAM without the virtualization overhead of a hypervisor. Combined with **Ventoy** and its `ventoy_vhdboot` plugin, you can carry multiple fully configured Windows operating systems on a single USB drive.

**VHDX Ventoy Creator & Manager** eliminates the manual CLI workflow (`diskpart`, `dism`, `bcdboot`) by providing a GUI that builds properly formatted, bootable VHDX Master images and child differential disks in seconds.  

## Key Features

- **Automated Master VHDX Creation:** Generates a fully compliant UEFI/GPT disk structure inside a VHDX container.  
- **Live DISM Progress Streaming:** Real-time feedback during image extraction (`.wim` / `.esd`).  
- **EFI Bootloader Injection:** Automatically targets the dedicated internal FAT32 EFI partition with `bcdboot` for clean Ventoy boot handoffs.  
- **Differential Disk Branching (Parent/Child):** Instant creation of lightweight child disks for disposable testing environments.
- **Driver Injection Support:** Offline driver integration (`.inf`) via DISM prior to initial system boot.  
- **Clean Standard OOBE Flow:** Preserves original Windows security initialization (SAM) to prevent deployment crash loops.

## Why It's Useful & Use Cases

- **Disposable Test Labs:** Create a Master VHDX with your base tools installed. Generate a small Child VHDX for testing risky software, malware analysis, or temporary builds. When done, simply delete the child disk to reset to a pristine state.
- **Multi-Environment Flash Drives:** Maintain separate production, gaming, and IT troubleshooting environments on a single external Ventoy SSD/USB drive.
- **Hardware Benchmarking:** Perform bare-metal hardware testing without partitioning local system drives or touching primary OS installations.

## Master VHDX Automated Pipeline

The app executes a structured 5-step automation pipeline under the hood:  

```
+-----------------------------------------------------------------------------------+
| 1. DISKPART          Create GPT Layout (300MB FAT32 EFI + 16MB MSR + NTFS OS)    |
| 2. DISM APPLY-IMAGE  Apply WIM/ESD index to OS Partition                          |
| 3. BCDBOOT           Inject bootloader to EFI Partition (bcdboot V:\Win /s S: /f ALL) |
| 4. DRIVER INJECTION  Integrate offline INF drivers (Optional)                     |
| 5. DISKPART DETACH   Unmount and release virtual disk drives                      |
+-----------------------------------------------------------------------------------+
```

## Troubleshooting & OOBE Workaround

### <mark>Error: "Windows could not update the computer's boot configuration"</mark>

During the first Out-Of-Box Experience (OOBE/Specialize phase) under Ventoy, Windows Setup may occasionally attempt to update the host machine's physical NVRAM and throw a boot configuration error.  

#### Manual Fix (In-Place Workaround)

If Windows halts during initial boot with this error, you can bypass the check without recreating the VHDX:  

1. Press **`Shift + F10`** (or `Fn + Shift + F10`) on the error screen to open the Command Prompt.

2. Type **`regedit`** and press **Enter**.

3. Navigate to:

   Plaintext

   ```
   HKLM\SYSTEM\Setup\Status\ChildCompletion
   ```

4. Double-click the **`setup.exe`** DWORD value and change its data from `1` (or `2`) to **`3`**.

5. Click **OK**, close the Registry Editor and Command Prompt.

6. Click **OK** on the Windows error dialog. The system will reboot, skip the NVRAM update check, and load directly into the desktop setup.

## Building from Source

### Prerequisites

- Windows 10/11 (Administrator privileges required for `diskpart` and `dism`).  
- Python 3.10+
- Nuitka compiler and MinGW64 toolchain

### Installation

1. **Clone the repository:**

   Bash

   ```
   git clone https://github.com/your-username/vhdx-ventoy-manager.git
   cd vhdx-ventoy-manager
   ```

2. **Create and activate a virtual environment:**

   Bash

   ```
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies:**

   Bash

   ```
   pip install -r requirements.txt
   ```

4. **Run Unit Tests:**

   Bash

   ```
   pytest -v tests/
   ```

### Executable Compilation (Nuitka)

To compile the application into a standalone single-file Windows executable, run:

Bash

```
nuitka --standalone --onefile --windows-console-mode=disable --enable-plugin=pyside6 --mingw64 --windows-icon-from-ico=icon.ico main.py
```

## Requirements for Booting via Ventoy

1. A USB Drive or External SSD prepared with **Ventoy** (formatted as **NTFS**).
2. The **Ventoy VHD Boot Plugin**:
   - Download `ventoy_vhdboot.img` from the official Ventoy website.
   - Place it in the `/ventoy/` directory on your Ventoy USB drive (`/ventoy/ventoy_vhdboot.img`).

## License

Distributed under the MIT License. See `LICENSE` for more information.
