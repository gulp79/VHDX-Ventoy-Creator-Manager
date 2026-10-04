"""
Unit tests for VHDX engine and diskpart script generation.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.vhd_engine import (
    create_master_vhdx,
    create_child_vhdx,
    detach_vhdx,
    bcdboot_inject
)


def test_create_master_vhdx_script():
    executed_scripts = []

    def mock_run_diskpart(script_content, on_line=None, cancel_event=None):
        executed_scripts.append(script_content)
        return 0, "DiskPart successfully created the virtual disk."

    with patch("core.vhd_engine.run_diskpart_script", side_effect=mock_run_diskpart), \
         patch("os.path.exists", return_value=True), \
         patch("os.makedirs"):

        success, msg = create_master_vhdx(
            vhdx_path="C:\\VMs\\Win11.vhdx",
            size_mb=65536,
            vhdx_type="expandable",
            os_drive_letter="V",
            efi_drive_letter="S",
            volume_label="WindowsVHD"
        )

        assert success is True
        assert len(executed_scripts) == 1
        script = executed_scripts[0]
        assert 'create vdisk file="C:\\VMs\\Win11.vhdx" maximum=65536 type=expandable' in script
        assert 'convert gpt' in script
        assert 'create partition efi size=300' in script
        assert 'format quick fs=fat32 label="System"' in script
        assert 'assign letter=S' in script
        assert 'create partition msr size=16' in script
        assert 'create partition primary' in script
        assert 'format quick fs=ntfs label="WindowsVHD"' in script
        assert 'assign letter=V' in script


def test_create_child_vhdx_script():
    executed_scripts = []

    def mock_run_diskpart(script_content, on_line=None, cancel_event=None):
        executed_scripts.append(script_content)
        return 0, "DiskPart successfully created the virtual disk."

    with patch("core.vhd_engine.run_diskpart_script", side_effect=mock_run_diskpart), \
         patch("os.path.isfile", return_value=True), \
         patch("os.makedirs"):

        success, msg = create_child_vhdx(
            parent_path="C:\\VMs\\Parent.vhdx",
            child_path="C:\\VMs\\Child.vhdx"
        )

        assert success is True
        assert len(executed_scripts) == 1
        script = executed_scripts[0]
        assert 'create vdisk file="C:\\VMs\\Child.vhdx" parent="C:\\VMs\\Parent.vhdx"' in script


def test_detach_vhdx_script():
    executed_scripts = []

    def mock_run_diskpart(script_content, on_line=None, cancel_event=None):
        executed_scripts.append(script_content)
        return 0, "DiskPart successfully detached the virtual disk."

    with patch("core.vhd_engine.run_diskpart_script", side_effect=mock_run_diskpart), \
         patch("os.path.exists", return_value=True):

        success, msg = detach_vhdx("C:\\VMs\\Win11.vhdx")
        assert success is True
        assert len(executed_scripts) == 1
        assert 'detach vdisk' in executed_scripts[0]


def test_bcdboot_inject_mock():
    with patch("os.path.exists", return_value=True), \
         patch("core.vhd_engine.run_command", return_value=(0, "Boot files successfully created.")) as mock_run:

        success, msg = bcdboot_inject(os_drive_letter="V", efi_drive_letter="S", firmware_type="ALL")
        assert success is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd == ["bcdboot", "V:\\Windows", "/s", "S:", "/f", "ALL"]
