"""
Ventoy Plugin Installer and VHDX Deployment Workers (QThread).
"""

import threading
from PySide6.QtCore import QThread, Signal
from core.ventoy_engine import install_vhdboot_plugin, copy_vhdx_file


class VentoyPluginWorker(QThread):
    progress_changed = Signal(int, str)
    log_event = Signal(str, str)
    task_finished = Signal(bool, str)

    def __init__(self, ventoy_root: str, parent=None):
        super().__init__(parent)
        self.ventoy_root = ventoy_root
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        try:
            self.log_event.emit("=== Installing ventoy_vhdboot.img Plugin ===", "INFO")
            self.progress_changed.emit(5, "Connecting to download source...")

            def on_prog(pct: float, text: str):
                self.progress_changed.emit(int(pct), text)

            success, msg = install_vhdboot_plugin(
                ventoy_root=self.ventoy_root,
                on_progress=on_prog,
                on_line=lambda l: self.log_event.emit(l, "INFO"),
                cancel_event=self.cancel_event
            )

            if success:
                self.progress_changed.emit(100, "Installation Complete")
                self.log_event.emit(msg, "SUCCESS")
                self.task_finished.emit(True, msg)
            else:
                self.progress_changed.emit(0, "Installation Failed")
                self.log_event.emit(msg, "ERROR")
                self.task_finished.emit(False, msg)

        except Exception as e:
            self.log_event.emit(f"Plugin installer error: {e}", "ERROR")
            self.task_finished.emit(False, str(e))


class VentoyDeployWorker(QThread):
    progress_changed = Signal(int, str)
    log_event = Signal(str, str)
    task_finished = Signal(bool, str)

    def __init__(self, source_vhdx: str, target_dir: str, move: bool = False, parent=None):
        super().__init__(parent)
        self.source_vhdx = source_vhdx
        self.target_dir = target_dir
        self.move = move
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        try:
            action_name = "Moving" if self.move else "Deploying (Copying)"
            self.log_event.emit(f"=== {action_name} VHDX to Ventoy Drive ===", "INFO")
            self.progress_changed.emit(0, "Starting transfer...")

            def on_prog(pct: float, text: str):
                self.progress_changed.emit(int(pct), text)

            success, msg = copy_vhdx_file(
                source_path=self.source_vhdx,
                target_dir=self.target_dir,
                move=self.move,
                on_progress=on_prog,
                on_line=lambda l: self.log_event.emit(l, "RAW"),
                cancel_event=self.cancel_event
            )

            if success:
                self.progress_changed.emit(100, "Transfer Complete")
                self.log_event.emit(msg, "SUCCESS")
                self.task_finished.emit(True, msg)
            else:
                self.progress_changed.emit(0, "Transfer Failed")
                self.log_event.emit(msg, "ERROR")
                self.task_finished.emit(False, msg)

        except Exception as e:
            self.log_event.emit(f"Transfer error: {e}", "ERROR")
            self.task_finished.emit(False, str(e))
