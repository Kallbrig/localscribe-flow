from pathlib import Path

from PySide6.QtWidgets import QApplication

from localscribe.config import ConfigStore
from localscribe.domain import CleanupMode, HardwareProfile
from localscribe.pipeline import DictationPipeline
from localscribe.ui import MainWindow


class StubTranscriber:
    def transcribe(self, audio_path: Path, vocabulary: list[str]) -> tuple[str, str, float]:
        return "test", "en", 1.0


class StubCleaner:
    def clean(self, text: str, mode: CleanupMode, vocabulary: list[str]) -> str:
        return text


def make_window(monkeypatch: object, tmp_path: Path) -> MainWindow:
    monkeypatch.setenv("LOCALSCRIBE_DIAGNOSTIC", "1")  # type: ignore[attr-defined]
    monkeypatch.setattr(MainWindow, "_build_tray", lambda self: None)  # type: ignore[attr-defined]
    monkeypatch.setattr(MainWindow, "_register_hotkey", lambda self: None)  # type: ignore[attr-defined]
    app = QApplication.instance() or QApplication([])
    hardware = HardwareProfile("cpu", "int8", 4, 8.0, None, "test")
    window = MainWindow(ConfigStore(tmp_path / "config.json"), hardware)
    window._test_app = app
    return window


def test_recording_is_locked_while_speech_model_loads(monkeypatch: object, tmp_path: Path) -> None:
    window = make_window(monkeypatch, tmp_path)

    assert not window.record.isEnabled()
    assert window.record.text() == "Preparing speech model…"


def test_startup_failure_is_retryable_without_modal(monkeypatch: object, tmp_path: Path) -> None:
    window = make_window(monkeypatch, tmp_path)
    window._on_startup_failed("download unavailable")

    assert not window.record.isEnabled()
    assert window.retry.isVisibleTo(window)
    assert window.status.text() == "download unavailable"


def test_recording_unlocks_when_pipeline_is_ready(monkeypatch: object, tmp_path: Path) -> None:
    window = make_window(monkeypatch, tmp_path)
    pipeline = DictationPipeline(StubTranscriber(), StubCleaner())
    window._on_models_ready(pipeline, "Ready")

    assert window.record.isEnabled()
    assert window.record.text() == "Start recording"
    assert window.status.text() == "Ready"
