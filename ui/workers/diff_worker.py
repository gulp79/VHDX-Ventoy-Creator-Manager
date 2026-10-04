"""
Differential (Child) VHDX Worker Thread (QThread).
"""

import threading
from PySide6.QtCore import QThread, Signal
from core.vhd_engine import create_child_vhdx


class DifferentialWorker(QThread):
    progress_changed = Signal(int)
    log_event = Signal(str, str)
    task_finished = Signal(bool, str)

    def __init__(self, parent_vhdx: str, child_vhdx: str, parent=None):
        super().__init__(parent)
        self.parent_vhdx = parent_vhdx
        self.child_vhdx = child_vhdx
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        try:
            self.log_event.emit("=== Creating Differential Child VHDX ===", "INFO")
            self.progress_changed.emit(20)
            self.log_event.emit(f"Parent Master: {self.parent_vhdx}", "INFO")
            self.log_event.emit(f"Child Target:  {self.child_vhdx}", "INFO")

            success, msg = create_child_vhdx(
                parent_path=self.parent_vhdx,
                child_path=self.child_vhdx,
                on_line=lambda l: self.log_event.emit(l, "RAW"),
                cancel_event=self.cancel_event
            )

            if success:
                self.progress_changed.emit(100)
                self.log_event.emit("Differential VHDX created successfully!", "SUCCESS")
                self.task_finished.emit(True, msg)
            else:
                self.progress_changed.emit(0)
                self.log_event.emit(msg, "ERROR")
                self.task_finished.emit(False, msg)

        except Exception as e:
            self.log_event.emit(f"Exception in differential worker: {e}", "ERROR")
            self.task_finished.emit(False, str(e))
