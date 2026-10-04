"""
Unit tests for disk_info utilities and safety calculations.
"""

import pytest
from unittest.mock import patch, MagicMock
from utils.disk_info import (
    format_size,
    get_disk_space_info,
    get_available_drive_letter,
    validate_space_headroom
)


def test_format_size():
    assert format_size(0) == "0.0 B" or format_size(0) == "0 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1024 * 1024) == "1.0 MB"
    assert format_size(1024 * 1024 * 1024) == "1.0 GB"
    assert format_size(64 * 1024 * 1024 * 1024) == "64.0 GB"


def test_get_available_drive_letter():
    with patch("utils.disk_info.get_used_drive_letters", return_value={"C", "D", "E", "V"}):
        letter = get_available_drive_letter(["V", "W", "X"])
        assert letter == "W"

    with patch("utils.disk_info.get_used_drive_letters", return_value={"C", "D", "V", "W", "X", "Y", "Z"}):
        letter = get_available_drive_letter(["V", "W", "X", "Y", "Z"])
        # Should fallback to reverse alphabet excluding A, B, and used letters
        assert letter not in {"A", "B", "C", "D", "V", "W", "X", "Y", "Z"}


def test_get_available_drive_letters_multiple():
    with patch("utils.disk_info.get_used_drive_letters", return_value={"C", "D"}):
        from utils.disk_info import get_available_drive_letters
        letters = get_available_drive_letters(count=2, preferred=["V", "S", "W"])
        assert len(letters) == 2
        assert letters[0] == "V"
        assert letters[1] == "S"


def test_validate_space_headroom_dynamic():
    # Free space 100 GB, VHDX max 64 GB -> safe
    with patch("utils.disk_info.get_disk_space_info", return_value={"free": 100 * (1024**3)}):
        safe, msg = validate_space_headroom("D:\\vhd", 64 * (1024**3), is_dynamic=True)
        assert safe is True
        assert msg == ""

    # Free space 30 GB, VHDX max 64 GB -> safe with warning for expandable VHDX
    with patch("utils.disk_info.get_disk_space_info", return_value={"free": 30 * (1024**3)}):
        safe, msg = validate_space_headroom("D:\\vhd", 64 * (1024**3), is_dynamic=True)
        assert safe is True
        assert "WARNING" in msg
        assert "VHD_BOOT_INITIALIZATION_FAILED" in msg

    # Free space 5 GB -> unsafe (below 20 GB min for dynamic)
    with patch("utils.disk_info.get_disk_space_info", return_value={"free": 5 * (1024**3)}):
        safe, msg = validate_space_headroom("D:\\vhd", 64 * (1024**3), is_dynamic=True)
        assert safe is False
        assert "Critically low disk space" in msg


def test_validate_space_headroom_fixed():
    # Fixed VHDX 64 GB requires 64 GB + 5 GB headroom = 69 GB
    with patch("utils.disk_info.get_disk_space_info", return_value={"free": 60 * (1024**3)}):
        safe, msg = validate_space_headroom("D:\\vhd", 64 * (1024**3), is_dynamic=False)
        assert safe is False
        assert "Insufficient disk space for Fixed VHDX" in msg

    with patch("utils.disk_info.get_disk_space_info", return_value={"free": 80 * (1024**3)}):
        safe, msg = validate_space_headroom("D:\\vhd", 64 * (1024**3), is_dynamic=False)
        assert safe is True
        assert msg == ""
