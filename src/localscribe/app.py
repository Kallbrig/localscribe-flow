from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
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
    diagnostic_file = os.environ.get("LOCALSCRIBE_DIAGNOSTIC_FILE")
    if diagnostic_file:

        def diagnostic_success() -> None:
            startup_controls_are_safe = (
                not window.record.isEnabled()
                and window.record.text() == "Preparing speech model…"
            )
            result = "ok\n" if startup_controls_are_safe else "invalid startup state\n"
            Path(diagnostic_file).write_text(result, encoding="utf-8")
            app.quit()

        QTimer.singleShot(250, diagnostic_success)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
