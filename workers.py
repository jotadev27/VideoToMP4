"""Qt signal adapter for the independent conversion engine."""

import sys
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from converter import Cancelled, ConversionError, MediaInfo, convert_media, probe_media


class Worker(QThread):
    """Keep filesystem and FFmpeg work off the GUI thread."""

    detected = Signal(object)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    progress = Signal(object, str)

    def __init__(self, source: Path | None = None, info: MediaInfo | None = None, output: Path | None = None):
        super().__init__()
        self.source, self.info, self.output = source, info, output
        self.cancel_event = threading.Event()

    def run(self) -> None:
        try:
            if self.source is not None:
                self.detected.emit(probe_media(self.source, self.cancel_event))
            else:
                self.completed.emit(convert_media(self.info, self.output, self.cancel_event, self.progress.emit))
        except Cancelled:
            self.cancelled.emit()
        except ConversionError as error:
            self.failed.emit(str(error))
        except OSError as error:
            self.failed.emit("The file could not be read or saved. Check the location and available disk space.")
            print(f"File error: {type(error).__name__}", file=sys.stderr)
        except Exception as error:
            self.failed.emit("Something went wrong. Please try again or choose a different file.")
            print(f"Unexpected error: {type(error).__name__}", file=sys.stderr)


