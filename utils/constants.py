"""
Application constants and configuration defaults.
"""

APP_NAME = "VHDX Ventoy Creator & Manager"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Automate Windows VHDX Native Boot creation and deployment for Ventoy"

# Disk Defaults (in GB)
DEFAULT_VHDX_SIZE_GB = 64
MIN_VHDX_SIZE_GB = 16
MAX_VHDX_SIZE_GB = 512

# Safety Buffer: Minimum free space required on destination drive (in GB)
MIN_FREE_SPACE_HEADROOM_GB = 5

# Supported source file formats
SOURCE_IMAGE_EXTENSIONS = [".iso", ".wim", ".esd"]

# Default VHD volume label
DEFAULT_VOLUME_LABEL = "WindowsVHD"

# Preferred virtual drive letter to avoid conflict
PREFERRED_DRIVE_LETTERS = ["V", "W", "X", "Y", "Z", "T", "U", "S", "R"]

# Ventoy vhdboot plugin settings
VENTOY_VHDBOOT_FILENAME = "ventoy_vhdboot.img"
VENTOY_VHDBOOT_SUBDIR = "ventoy"
VENTOY_VHDBOOT_DOWNLOAD_URL = (
    "https://github.com/ventoy/vhd-boot/releases/download/v1.0/ventoy_vhdboot.img"
)

# Alternative mirrors / fallback URLs if needed
VENTOY_VHDBOOT_FALLBACK_URL = (
    "https://raw.githubusercontent.com/ventoy/vhd-boot/master/ventoy_vhdboot.img"
)
