"""Load the bundled open font for consistent Linux and Windows rendering."""

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase


def application_font() -> QFont:
    assets = Path(__file__).resolve().parent / "assets"
    regular = QFontDatabase.addApplicationFont(str(assets / "UiSans-Regular.ttf"))
    QFontDatabase.addApplicationFont(str(assets / "UiSans-Bold.ttf"))
    families = QFontDatabase.applicationFontFamilies(regular)
    return QFont(families[0] if families else "Sans Serif", 10)
