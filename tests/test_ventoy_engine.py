"""
Unit tests for Ventoy detection and plugin verification.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from core.ventoy_engine import (
    check_vhdboot_plugin,
    detect_ventoy_drives,
    copy_vhdx_file
)


def test_check_vhdboot_plugin_present():
    with patch("os.path.isfile", return_value=True), \
         patch("os.path.getsize", return_value=2048576):
        
        has_plugin, path, size = check_vhdboot_plugin("E:\\")
        assert has_plugin is True
        assert path.endswith("ventoy_vhdboot.img")
        assert size == 2048576


def test_check_vhdboot_plugin_missing():
    with patch("os.path.isfile", return_value=False):
        has_plugin, path, size = check_vhdboot_plugin("E:\\")
        assert has_plugin is False
        assert size == 0


def test_detect_ventoy_drives_mock():
    mock_partition = MagicMock()
    mock_partition.mountpoint = "E:\\"
    mock_partition.device = "E:"
    mock_partition.fstype = "NTFS"
    mock_partition.opts = "rw,removable"

    with patch("psutil.disk_partitions", return_value=[mock_partition]), \
         patch("os.path.exists", return_value=True), \
         patch("core.ventoy_engine.get_volume_label_windows", return_value="Ventoy"), \
         patch("shutil.disk_usage", return_value=MagicMock(total=64*(1024**3), free=32*(1024**3))), \
         patch("core.ventoy_engine.check_vhdboot_plugin", return_value=(True, "E:\\ventoy\\ventoy_vhdboot.img", 2048576)):

        drives = detect_ventoy_drives()
        assert len(drives) == 1
        d = drives[0]
        assert d["drive_letter"] == "E:"
        assert d["is_ntfs"] is True
        assert d["label"] == "Ventoy"
        assert d["is_ventoy_candidate"] is True
        assert d["has_vhdboot_plugin"] is True
