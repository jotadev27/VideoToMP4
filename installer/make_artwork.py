"""Render the project logo into icons and installer images without stock art."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image  # noqa: E402
from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Sans Serif", 10))
    renderer = QSvgRenderer(str(ROOT / "assets" / "logo.svg"))
    icon = QImage(256, 256, QImage.Format.Format_ARGB32)
    icon.fill(Qt.GlobalColor.transparent)
    painter = QPainter(icon)
    renderer.render(painter, QRectF(0, 0, 256, 256))
    painter.end()
    icon.save(str(ROOT / "assets" / "logo.png"))
    Image.open(ROOT / "assets" / "logo.png").save(ROOT / "assets" / "logo.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    for name, width, height in (("welcome.bmp", 164, 314), ("header.bmp", 150, 57)):
        canvas = QImage(width, height, QImage.Format.Format_RGB32)
        canvas.fill(QColor("#f7f7f8") if name == "welcome.bmp" else QColor("white"))
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#18181b"))
        if name == "welcome.bmp":
            renderer.render(painter, QRectF(50, 45, 64, 64))
            painter.setFont(QFont("Sans Serif", 18, QFont.Weight.Bold))
            painter.drawText(QRectF(12, 127, 140, 75), Qt.AlignmentFlag.AlignCenter, "VIDEO\nTO MP4")
            painter.setFont(QFont("Sans Serif", 10))
            painter.setPen(QColor("#71717a"))
            painter.drawText(QRectF(10, 219, 144, 65), Qt.AlignmentFlag.AlignCenter, "v1.0\nLocal conversion\njotadev27")
        else:
            renderer.render(painter, QRectF(8, 12, 32, 32))
            painter.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
            painter.drawText(QRectF(48, 10, 100, 36), Qt.AlignmentFlag.AlignVCenter, "Video to MP4\nv1.0")
        painter.end()
        canvas.save(str(ROOT / "installer" / "windows" / name))


if __name__ == "__main__":
    main()
