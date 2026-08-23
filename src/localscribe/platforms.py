from __future__ import annotations

import platform
from collections.abc import Callable
from typing import Any


class DesktopIntegration:
    """Desktop boundary; replace with native macOS/Android adapters later."""

    def __init__(self) -> None:
        self._listener: Any = None

    def register_hotkey(self, hotkey: str, callback: Callable[[], None]) -> None:
        from pynput import keyboard

        self.unregister_hotkey()
        self._listener = keyboard.GlobalHotKeys({hotkey: callback})
        self._listener.start()

    def unregister_hotkey(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def paste_text(self, text: str) -> None:
        import pyperclip
        from pynput.keyboard import Controller, Key

        pyperclip.copy(text)
        keyboard = Controller()
        modifier = Key.cmd if platform.system() == "Darwin" else Key.ctrl
        with keyboard.pressed(modifier):
            keyboard.press("v")
            keyboard.release("v")
