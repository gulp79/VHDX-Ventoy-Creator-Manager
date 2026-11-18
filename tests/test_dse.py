"""
Unit tests for Driver Signature Enforcement (DSE) disablement and worker integration.
"""

import threading
from unittest.mock import patch, MagicMock, call
import pytest

from core.vhd_engine import disable_dse_in_bcd
from ui.workers.master_worker import MasterCreationWorker


# Sample bcdedit /enum all output mimicking realistic Windows EFI boot configuration
SAMPLE_BCD_OUTPUT = r"""
Windows Boot Manager
--------------------
identifier              {bootmgr}
device                  partition=\Device\HarddiskVolume1
path                    \EFI\Microsoft\Boot\bootmgfw.efi
description             Windows Boot Manager
locale                  en-US
inherit                 {globalsettings}
default                 {default}
resumeobject            {d2b3c4d5-1111-2222-3333-444455556666}
displayorder            {default}
toolsdisplayorder       {memdiag}
timeout                 30

Windows Boot Loader
-------------------
identifier              {default}
device                  partition=C:
path                    \Windows\system32\winload.efi
description             Windows 11 Pro
locale                  en-US
inherit                 {bootloadersettings}
recoverysequence        {e3f4a5b6-7777-8888-9999-000011112222}
recoveryenabled         Yes
isolatedcontext         Yes
allowedinmemorysettings 0x15000075
osdevice                partition=C:
systemroot              \Windows
resumeobject            {d2b3c4d5-1111-2222-3333-444455556666}
nx                      OptIn
bootmenupolicy          Standard

Windows Boot Loader
-------------------
identifier              {12345678-abcd-ef01-2345-6789abcdef01}
device                  partition=V:
path                    \Windows\system32\winload.efi
description             Custom Test Entry
locale                  en-US

Windows Memory Tester
---------------------
identifier              {memdiag}
device                  partition=\Device\HarddiskVolume1
path                    \boot\memtest.exe
description             Windows Memory Diagnostic
locale                  en-US
"""


def test_disable_dse_bcd_store_not_found():
    """Verify failure when BCD store does not exist."""
    with patch("os.path.exists", return_value=False):
        ok, msg = disable_dse_in_bcd("S")
        assert ok is False
        assert "BCD store not found" in msg


def test_disable_dse_enum_failure():
    """Verify failure handling when bcdedit enum exits with error."""
    with patch("os.path.exists", return_value=True), \
         patch("core.vhd_engine.run_command", return_value=(1, "The store could not be opened")):

        ok, msg = disable_dse_in_bcd("S:")
        assert ok is False
        assert "bcdedit /enum all failed" in msg


def test_disable_dse_success_flow():
    """Verify parsing and execution of bcdedit set commands for winload.efi entries and bootmgr."""
    executed_commands = []

    def mock_run_command(cmd, on_line=None, cancel_event=None):
        executed_commands.append(cmd)
        if "/enum" in cmd:
            return 0, SAMPLE_BCD_OUTPUT
        return 0, "The operation completed successfully."

    with patch("os.path.exists", return_value=True), \
         patch("core.vhd_engine.run_command", side_effect=mock_run_command):

        lines = []
        ok, msg = disable_dse_in_bcd("S:", on_line=lines.append)

        assert ok is True
        assert "Driver Signature Enforcement disabled successfully" in msg

        # Expected calls:
        # 1. enum all
        # 2. {default} nointegritychecks on
        # 3. {default} testsigning on
        # 4. {12345678-abcd-ef01-2345-6789abcdef01} nointegritychecks on
        # 5. {12345678-abcd-ef01-2345-6789abcdef01} testsigning on
        # 6. {bootmgr} nointegritychecks on
        expected_bcd_path = r"S:\EFI\Microsoft\Boot\BCD"

        assert executed_commands[0] == ["bcdedit", "/store", expected_bcd_path, "/enum", "all"]
        assert ["bcdedit", "/store", expected_bcd_path, "/set", "{default}", "nointegritychecks", "on"] in executed_commands
        assert ["bcdedit", "/store", expected_bcd_path, "/set", "{default}", "testsigning", "on"] in executed_commands
        assert ["bcdedit", "/store", expected_bcd_path, "/set", "{12345678-abcd-ef01-2345-6789abcdef01}", "nointegritychecks", "on"] in executed_commands
        assert ["bcdedit", "/store", expected_bcd_path, "/set", "{12345678-abcd-ef01-2345-6789abcdef01}", "testsigning", "on"] in executed_commands
        assert ["bcdedit", "/store", expected_bcd_path, "/set", "{bootmgr}", "nointegritychecks", "on"] in executed_commands


def test_disable_dse_cancellation():
    """Verify cancellation behaves cooperatively at start or middle."""
    cancel_event = threading.Event()
    cancel_event.set()

    with patch("os.path.exists", return_value=True):
        ok, msg = disable_dse_in_bcd("S", cancel_event=cancel_event)
        assert ok is False
        assert "cancelled" in msg.lower()


def test_disable_dse_no_winload_soft_warning():
    """Verify soft warning and bootmgr modification when no winload.efi entries found."""
    executed_commands = []

    def mock_run_command(cmd, on_line=None, cancel_event=None):
        executed_commands.append(cmd)
        if "/enum" in cmd:
            return 0, "Windows Boot Manager\nidentifier {bootmgr}\n"
        return 0, "Success"

    with patch("os.path.exists", return_value=True), \
         patch("core.vhd_engine.run_command", side_effect=mock_run_command):

        log_lines = []
        ok, msg = disable_dse_in_bcd("S", on_line=log_lines.append)
        assert ok is True
        # Ensure bootmgr still set
        assert ["bcdedit", "/store", r"S:\EFI\Microsoft\Boot\BCD", "/set", "{bootmgr}", "nointegritychecks", "on"] in executed_commands
        assert any("No winload.efi entries found" in line for line in log_lines)


def test_master_worker_dse_parameter_and_non_blocking():
    """Verify worker invokes disable_dse_in_bcd and handles failure gracefully without stopping."""
    worker = MasterCreationWorker(
        source_path="C:\\win.iso",
        edition_index=1,
        target_vhdx_path="C:\\win.vhdx",
        size_gb=30,
        disable_dse=True
    )
    assert worker.disable_dse is True

    worker_no_dse = MasterCreationWorker(
        source_path="C:\\win.iso",
        edition_index=1,
        target_vhdx_path="C:\\win.vhdx",
        size_gb=30,
        disable_dse=False
    )
    assert worker_no_dse.disable_dse is False


def test_master_worker_pipeline_dse_execution():
    """Test full worker pipeline mock to ensure DSE step is called and non-blocking on failure."""
    worker = MasterCreationWorker(
        source_path="C:\\win.wim",
        edition_index=1,
        target_vhdx_path="C:\\win.vhdx",
        size_gb=30,
        disable_dse=True
    )

    events = []
    task_results = []
    worker.log_event.connect(lambda msg, lvl: events.append((lvl, msg)))
    worker.task_finished.connect(lambda ok, msg: task_results.append((ok, msg)))

    with patch("ui.workers.master_worker.create_master_vhdx", return_value=(True, "Created")), \
         patch("ui.workers.master_worker.bcdboot_inject", return_value=(True, "Injected")), \
         patch("ui.workers.master_worker.disable_dse_in_bcd", return_value=(False, "Simulated BCD warning")) as mock_dse, \
         patch("ui.workers.master_worker.detach_vhdx", return_value=(True, "Detached")), \
         patch("ui.workers.master_worker.apply_image", return_value=(True, "Applied")), \
         patch("ui.workers.master_worker.validate_space_headroom", return_value=(True, "")), \
         patch("ui.workers.master_worker.get_available_drive_letters", return_value=["V", "S"]), \
         patch("os.path.isfile", return_value=True), \
         patch("os.path.exists", return_value=False):

        worker.run()

        # Check that disable_dse_in_bcd was called with efi_letter "S"
        mock_dse.assert_called_once()
        assert mock_dse.call_args[1]["efi_drive_letter"] == "S"

        # Verify non-blocking: failure produced a WARNING event, but task finished with True
        assert any(lvl == "WARNING" and "Simulated BCD warning" in msg for lvl, msg in events)
        assert len(task_results) == 1
        assert task_results[0][0] is True
