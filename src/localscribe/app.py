from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config import ConfigStore
from .hardware import detect_hardware
from .ui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LocalScribe Flow")
    app.setOrganizationName("LocalScribe")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow(ConfigStore(), detect_hardware())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
