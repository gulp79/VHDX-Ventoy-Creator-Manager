"""
Unit tests for DISM engine and output parsers.
"""

import pytest
from unittest.mock import patch
from core.dism_engine import (
    parse_wim_info_output,
    extract_dism_progress,
    apply_image,
    add_drivers
)


SAMPLE_DISM_OUTPUT_EN = """
Deployment Image Servicing and Management tool
Version: 10.0.22621.1

Details for image : C:\\sources\\install.wim

Index : 1
Name : Windows 11 Home
Description : Windows 11 Home Edition
Size : 16,342,123,456 bytes

Index : 2
Name : Windows 11 Pro
Description : Windows 11 Pro Edition
Size : 16,567,890,123 bytes
"""

SAMPLE_DISM_OUTPUT_IT = """
Strumento Gestione e manutenzione immagini distribuzione
Versione: 10.0.22621.1

Dettagli per l'immagine: D:\\sources\\install.wim

Indice : 1
Nome : Windows 11 Home
Descrizione : Windows 11 Home
Dimensioni : 16.342.123.456 byte

Indice : 2
Nome : Windows 11 Pro
Descrizione : Windows 11 Pro
Dimensioni : 16.567.890.123 byte
"""


def test_parse_wim_info_english():
    editions = parse_wim_info_output(SAMPLE_DISM_OUTPUT_EN)
    assert len(editions) == 2
    assert editions[0]["index"] == 1
    assert editions[0]["name"] == "Windows 11 Home"
    assert editions[0]["size_bytes"] == 16342123456
    assert editions[1]["index"] == 2
    assert editions[1]["name"] == "Windows 11 Pro"
    assert "[1] Windows 11 Home" in editions[0]["display_str"]


def test_parse_wim_info_italian():
    editions = parse_wim_info_output(SAMPLE_DISM_OUTPUT_IT)
    assert len(editions) == 2
    assert editions[0]["index"] == 1
    assert editions[0]["name"] == "Windows 11 Home"
    assert editions[0]["size_bytes"] == 16342123456
    assert editions[1]["index"] == 2
    assert editions[1]["name"] == "Windows 11 Pro"


def test_extract_dism_progress():
    assert extract_dism_progress("[========================== 45.0% ==========================]") == 45.0
    assert extract_dism_progress("[= 5.2% =]") == 5.2
    assert extract_dism_progress("100.0%") == 100.0
    assert extract_dism_progress("Applying progress: 83.4%") == 83.4
    assert extract_dism_progress("No percentage here") is None


def test_apply_image_mock():
    with patch("os.path.isfile", return_value=True), \
         patch("core.dism_engine.run_command", return_value=(0, "Success")) as mock_run:
        
        progress_calls = []
        success, msg = apply_image(
            image_file="C:\\install.wim",
            index=1,
            apply_dir="V:\\",
            on_progress=lambda p: progress_calls.append(p)
        )
        assert success is True
        assert 100.0 in progress_calls
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "dism"
        assert "/Apply-Image" in cmd
        assert "/Index:1" in cmd


def test_add_drivers_mock():
    with patch("os.path.isdir", return_value=True), \
         patch("core.dism_engine.run_command", return_value=(0, "Success")) as mock_run:
        
        success, msg = add_drivers(
            image_dir="V:\\",
            driver_folder="C:\\Drivers"
        )
        assert success is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "/Add-Driver" in cmd
        assert "/Recurse" in cmd


def test_extract_wim_xml_metadata_mock(tmp_path):
    from core.dism_engine import extract_wim_xml_metadata, get_wim_info
    
    xml_content = (
        '<?xml version="1.0" encoding="UTF-16"?>'
        '<WIM><IMAGE INDEX="1">'
        '<NAME>Bizarre11</NAME>'
        '<DESCRIPTION>Bizarre11 custom edition</DESCRIPTION>'
        '<TOTALBYTES>6398769527</TOTALBYTES>'
        '</IMAGE></WIM>'
    )
    test_file = tmp_path / "install.esd"
    # Write some dummy header bytes then the UTF-16LE XML metadata
    dummy_bytes = b"MSWIM\x00\x00\x00" + b"\x00" * 1024
    test_file.write_bytes(dummy_bytes + xml_content.encode("utf-16le"))

    editions = extract_wim_xml_metadata(str(test_file))
    assert editions is not None
    assert len(editions) == 1
    assert editions[0]["index"] == 1
    assert editions[0]["name"] == "Bizarre11"
    assert editions[0]["size_bytes"] == 6398769527
    assert "[1] Bizarre11" in editions[0]["display_str"]

    # Also verify get_wim_info uses it directly
    ed_info, _ = get_wim_info(str(test_file))
    assert len(ed_info) == 1
    assert ed_info[0]["name"] == "Bizarre11"
