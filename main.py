"""A small, borderless desktop interface for local video conversion."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)
from PySide6.QtSvgWidgets import QSvgWidget

from app_info import APP_NAME, VERSION
from converter import MediaInfo, suggested_output
from workers import Worker


ROOT = Path(__file__).resolve().parent


STYLE = """
QWidget { background: #ffffff; color: #18181b; font-size: 14px; border: none; }
QLabel { background: transparent; }
QPushButton { background: #f1f1f3; color: #27272a; border: none; border-radius: 10px;
              font-size: 14px; font-weight: 500; padding: 0; }
QPushButton:hover { background: #e7e7eb; }
QPushButton:pressed { background: #ddddE2; }
QPushButton:disabled { background: #f6f6f7; color: #aaaab2; }
QPushButton#start { background: #18181b; color: #ffffff; }
QPushButton#start:hover { background: #35353b; }
QPushButton#start:pressed { background: #09090b; }
QPushButton#start:disabled { background: #e4e4e7; color: #a1a1aa; }
QPushButton#windowButton { background: transparent; border-radius: 6px; }
QPushButton#windowButton:hover { background: #f1f1f3; }
QProgressBar { background: #eeeeF0; border: none; border-radius: 3px; min-height: 6px; max-height: 6px; }
QProgressBar::chunk { background: #18181b; border-radius: 3px; }
"""


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{size} B"
        value /= 1024
    return str(size)


def human_duration(seconds: float | None) -> str:
    if seconds is None:
        return "Unknown duration"
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02}:{secs:02}" if hours else f"{minutes}:{secs:02}"


class WindowButton(QPushButton):
    def __init__(self, kind: str):
        super().__init__()
        self.kind = kind
        self.setObjectName("windowButton")
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Close" if kind == "close" else "Minimize")
        self.setAccessibleName(self.toolTip())

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#71717a"), 1.5))
        if self.kind == "close":
            painter.drawLine(12, 12, 20, 20)
            painter.drawLine(20, 12, 12, 20)
        else:
            painter.drawLine(11, 16, 21, 16)


class TitleBar(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.setFixedHeight(48)
        row = QHBoxLayout(self)
        row.setContentsMargins(18, 8, 14, 8)
        name = QLabel("VIDEO TO MP4")
        name.setStyleSheet("font-size: 10px; font-weight: 600; color: #a1a1aa; letter-spacing: 2px;")
        row.addWidget(name)
        row.addStretch()
        minimize, close = WindowButton("minimize"), WindowButton("close")
        minimize.clicked.connect(window.showMinimized)
        close.clicked.connect(window.close)
        row.addWidget(minimize)
        row.addWidget(close)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.window.windowHandle():
            self.window.windowHandle().startSystemMove()


class DropArea(QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("dropArea")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#dropArea { background: #f7f7f8; border: none; border-radius: 14px; }")
        self.setFixedHeight(112)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Drop a video here or press Enter to choose a file")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        self.title = QLabel("Drop a video here")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("font-size: 15px; font-weight: 500;")
        self.detail = QLabel("or select a file below")
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail.setStyleSheet("font-size: 12px; color: #8b8b94;")
        layout.addStretch()
        layout.addWidget(self.title)
        layout.addWidget(self.detail)
        layout.addStretch()

    def mouseReleaseEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)

    def highlight(self, enabled: bool):
        background = "#ececf0" if enabled else "#f7f7f8"
        self.setStyleSheet(f"QWidget#dropArea {{ background: {background}; border: none; border-radius: 14px; }}")


class MainWindow(QMainWindow):
    """Present one-file conversion and own the background worker lifecycle."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.setWindowIcon(QIcon(str(ROOT / "assets" / "logo.svg")))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(760, 706)
        self.setFixedSize(760, 706)
        self.setAcceptDrops(True)
        self.info: MediaInfo | None = None
        self.output: Path | None = None
        self.result: Path | None = None
        self.worker: Worker | None = None
        self.close_pending = False
        self.busy = False
        self.converting = False

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(TitleBar(self))

        content = QWidget()
        content.setMaximumWidth(540)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(22, 12, 22, 22)
        layout.setSpacing(0)
        logo = QSvgWidget(str(ROOT / "assets" / "logo.svg"))
        logo.setFixedSize(48, 48)
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(18)
        title = QLabel("Video to MP4")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 29px; font-weight: 600; letter-spacing: -1px;")
        layout.addWidget(title)
        layout.addSpacing(9)
        subtitle = QLabel("Your video, ready to play.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #8b8b94;")
        layout.addWidget(subtitle)
        layout.addSpacing(30)
        self.drop = DropArea()
        self.drop.clicked.connect(self.choose_video)
        layout.addWidget(self.drop)
        layout.addSpacing(18)

        self.select_button = self.make_button("Select video", self.choose_video)
        layout.addWidget(self.select_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)
        self.output_button = self.make_button("Save as", self.choose_output)
        layout.addWidget(self.output_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(8)
        self.output_label = QLabel("Choose a video to get started")
        self.output_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.output_label.setFixedHeight(35)
        self.output_label.setStyleSheet("font-size: 11px; color: #8b8b94;")
        layout.addWidget(self.output_label)
        layout.addSpacing(9)
        self.start_button = self.make_button("Start", self.start_or_cancel)
        self.start_button.setObjectName("start")
        layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(22)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(224)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(12)
        self.status = QLabel("Original size to +30%. Original resolution.")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setWordWrap(True)
        self.status.setFixedHeight(52)
        self.status.setStyleSheet("font-size: 12px; color: #8b8b94;")
        layout.addWidget(self.status)
        layout.addStretch()
        footer = QLabel("LOCAL FILES. NO UPLOADS.")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("font-size: 9px; letter-spacing: 1.5px; color: #b0b0b8;")
        layout.addWidget(footer)
        root.addWidget(content, 1, Qt.AlignmentFlag.AlignHCenter)
        self.update_controls()

    def make_button(self, text, callback) -> QPushButton:
        button = QPushButton(text)
        button.setFixedSize(224, 46)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.clicked.connect(callback)
        return button

    def set_status(self, text: str, kind: str = "normal"):
        color = {"normal": "#8b8b94", "error": "#bf3434", "success": "#238153"}[kind]
        self.status.setStyleSheet(f"font-size: 12px; color: {color};")
        self.status.setText(text)

    def update_controls(self):
        self.select_button.setEnabled(not self.busy)
        self.output_button.setEnabled(self.info is not None and not self.busy)
        self.drop.setEnabled(not self.busy)
        self.start_button.setEnabled(self.converting or (not self.busy and self.info is not None and self.output is not None))
        self.start_button.setText("Cancel" if self.converting else "Open video" if self.result else "Start")

    def reset_progress(self):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def choose_video(self):
        if self.busy:
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Select a video", str(self.info.path.parent) if self.info else str(Path.home()), "All files (*)")
        if filename:
            self.load_video(Path(filename))

    def load_video(self, path: Path):
        if self.busy:
            return
        self.info, self.output, self.result = None, None, None
        self.output_label.setText("Reading your video…")
        self.drop.title.setText(self.fontMetrics().elidedText(path.name, Qt.TextElideMode.ElideMiddle, 310))
        self.drop.title.setToolTip(str(path))
        self.drop.detail.setText("Checking file…")
        self.set_status("Reading your video…")
        self.busy = True
        self.progress_bar.setRange(0, 0)
        worker = Worker(source=path)
        worker.detected.connect(self.on_detected)
        self.launch_worker(worker)

    def launch_worker(self, worker: Worker):
        # Hold a strong reference until QThread.finished; never destroy a running thread.
        self.worker = worker
        worker.failed.connect(self.on_failed)
        worker.cancelled.connect(self.on_cancelled)
        worker.finished.connect(self.on_worker_finished)
        self.update_controls()
        worker.start()

    def on_detected(self, info: MediaInfo):
        self.info = info
        self.output = suggested_output(info.path)
        self.drop.detail.setText(f"{info.width} × {info.height}  ·  {human_duration(info.duration)}  ·  {human_size(info.size)}")
        self.show_output()
        self.reset_progress()
        if info.video_copy:
            self.set_status("Ready. Compatible video will be copied when it fits the size limit.")
        elif info.width % 2 or info.height % 2:
            self.set_status("Ready. One edge pixel will be added for MP4 compatibility.")
        elif info.hdr:
            self.set_status("Ready. HDR will be converted to SDR for broader playback support.")
        else:
            self.set_status("Ready. Original resolution. Output size limited to +30%.")

    def choose_output(self):
        if self.busy or not self.info:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save MP4 as", str(self.output), "MP4 video (*.mp4)",
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != ".mp4":
            path = path.with_name(path.name + ".mp4")
        if path.exists() or path.is_symlink():
            self.set_status("That file already exists. Choose a new filename.", "error")
            return
        self.output, self.result = path, None
        self.show_output()
        self.reset_progress()
        self.set_status("Ready to start.")
        self.update_controls()

    def show_output(self):
        if self.output:
            self.output_label.setText(self.fontMetrics().elidedText(str(self.output), Qt.TextElideMode.ElideMiddle, 310))
            self.output_label.setToolTip(str(self.output))

    def start_or_cancel(self):
        if self.converting and self.worker:
            self.worker.cancel_event.set()
            self.start_button.setEnabled(False)
            self.start_button.setText("Cancelling…")
            self.set_status("Cancelling. Your original video is safe.")
            return
        if self.result:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.result))):
                self.set_status("No video player could be opened. Your MP4 is saved at the location above.", "error")
            return
        if self.busy or not self.info or not self.output:
            return
        self.busy = self.converting = True
        self.reset_progress()
        self.set_status("Starting conversion…")
        worker = Worker(info=self.info, output=self.output)
        worker.progress.connect(self.on_progress)
        worker.completed.connect(self.on_completed)
        self.launch_worker(worker)

    def on_progress(self, percent, message):
        if percent is None:
            self.progress_bar.setRange(0, 0)
            self.set_status(message)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(round(percent))
            self.set_status(f"{message}  {round(percent)}%")

    def on_completed(self, output: Path):
        self.result = output
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.set_status(f"Success. Your MP4 is ready.  {human_size(output.stat().st_size)}", "success")

    def on_failed(self, message: str):
        self.reset_progress()
        if self.info is None:
            self.drop.detail.setText("Please select another video")
            self.output_label.setText("No output selected")
        self.set_status(message, "error")

    def on_cancelled(self):
        self.reset_progress()
        self.set_status("Cancelled. Your original video is unchanged.")

    def on_worker_finished(self):
        worker = self.worker
        self.worker = None
        self.busy = self.converting = False
        self.update_controls()
        if worker:
            worker.deleteLater()
        if self.close_pending:
            self.close()

    def dragEnterEvent(self, event):
        if not self.busy and event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                self.drop.highlight(True)
                event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.drop.highlight(False)

    def dropEvent(self, event):
        self.drop.highlight(False)
        if self.busy:
            return
        urls = event.mimeData().urls()
        if len(urls) != 1 or not urls[0].isLocalFile():
            self.set_status("Please drop one local video at a time.", "error")
            return
        path = Path(urls[0].toLocalFile())
        if not path.is_file():
            self.set_status("Please drop a video file, rather than a folder.", "error")
            return
        event.acceptProposedAction()
        self.load_video(path)

    def closeEvent(self, event):
        # Close only after FFmpeg stops and temporary files have been removed.
        if self.worker is not None and self.busy:
            self.close_pending = True
            self.worker.cancel_event.set()
            self.start_button.setEnabled(False)
            self.set_status("Stopping safely…")
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("Video to MP4")
    app.setStyle("Fusion")
    app.setFont(QFont("Sans Serif", 10))
    app.setStyleSheet(STYLE)
    app.setWindowIcon(QIcon(str(ROOT / "assets" / "logo.svg")))
    window = MainWindow()
    window.show()
    if len(sys.argv) > 1:
        window.load_video(Path(sys.argv[1]))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
