from pathlib import Path

from PySide6.QtWidgets import QApplication

from localscribe import ui
from localscribe.config import ConfigStore
from localscribe.domain import CleanupMode, HardwareProfile, Transcript
from localscribe.pipeline import DictationPipeline
from localscribe.ui import MainWindow


class StubTranscriber:
    def transcribe(self, audio_path: Path, vocabulary: list[str]) -> tuple[str, str, float]:
        return "test", "en", 1.0


class StubCleaner:
    def clean(self, text: str, mode: CleanupMode, vocabulary: list[str]) -> str:
        return text


class StubRecorder:
    def __init__(self) -> None:
        self.recording = False

    def start(self) -> None:
        self.recording = True


class CapturingTray:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def showMessage(self, title: str, message: str) -> None:
        self.messages.append((title, message))


def make_window(monkeypatch: object, tmp_path: Path) -> MainWindow:
    monkeypatch.setenv("LOCALSCRIBE_DIAGNOSTIC", "1")  # type: ignore[attr-defined]
    monkeypatch.setenv("LOCALSCRIBE_DATA_DIR", str(tmp_path / "data"))  # type: ignore[attr-defined]
    monkeypatch.setattr(MainWindow, "_build_tray", lambda self: None)  # type: ignore[attr-defined]
    monkeypatch.setattr(MainWindow, "_register_hotkey", lambda self: None)  # type: ignore[attr-defined]
    app = QApplication.instance() or QApplication([])
    hardware = HardwareProfile("cpu", "int8", 4, 8.0, None, "test")
    window = MainWindow(ConfigStore(tmp_path / "config.json"), hardware)
    window._test_app = app
    return window


def test_recording_is_locked_while_speech_model_loads(monkeypatch: object, tmp_path: Path) -> None:
    window = make_window(monkeypatch, tmp_path)

    assert window.windowTitle() == "LocalScribe"
    assert not window.record.isEnabled()
    assert window.record.text() == "Preparing speech model…"
    assert not window.model_progress.isHidden()


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


def test_starting_recording_never_shows_a_windows_notification(
    monkeypatch: object, tmp_path: Path
) -> None:
    window = make_window(monkeypatch, tmp_path)
    window.pipeline = DictationPipeline(StubTranscriber(), StubCleaner())
    window.recorder = StubRecorder()  # type: ignore[assignment]
    tray = CapturingTray()
    window.tray = tray  # type: ignore[assignment]

    window.toggle_recording()

    assert tray.messages == []


def test_completion_notification_is_silent_by_default(monkeypatch: object, tmp_path: Path) -> None:
    window = make_window(monkeypatch, tmp_path)
    tray = CapturingTray()
    window.tray = tray  # type: ignore[assignment]

    window._on_complete(Transcript("hello", "Hello.", "en", 1.0, CleanupMode.STANDARD))

    assert tray.messages == []


def test_completion_notification_can_be_enabled(monkeypatch: object, tmp_path: Path) -> None:
    window = make_window(monkeypatch, tmp_path)
    window.config.notify_on_complete = True  # type: ignore[attr-defined]
    tray = CapturingTray()
    window.tray = tray  # type: ignore[assignment]

    window._on_complete(Transcript("hello", "Hello.", "en", 1.0, CleanupMode.STANDARD))

    assert tray.messages == [("LocalScribe", "Transcription copied to clipboard")]


def test_completion_notification_setting_is_persisted(monkeypatch: object, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    window = make_window(monkeypatch, tmp_path)

    window.notify_complete.setChecked(True)  # type: ignore[attr-defined]

    assert ConfigStore(config_path).load().notify_on_complete is True  # type: ignore[attr-defined]


def test_model_download_progress_is_visible(monkeypatch: object, tmp_path: Path) -> None:
    window = make_window(monkeypatch, tmp_path)
    window._on_model_progress("Downloading speech model", 25, 100)

    assert window.model_progress.value() == 25
    assert window.model_progress.maximum() == 100
    assert "Downloading speech model" in window.model_progress.format()


def test_corrupt_speech_model_is_force_downloaded_and_retried(
    monkeypatch: object, tmp_path: Path
) -> None:
    window = make_window(monkeypatch, tmp_path)
    forced: list[bool] = []
    transcriber_attempts = 0

    def prepare(*args: object, force_download: bool = False, **kwargs: object) -> Path:
        forced.append(force_download)
        return tmp_path / "speech-model"

    def transcriber(*args: object, **kwargs: object) -> StubTranscriber:
        nonlocal transcriber_attempts
        transcriber_attempts += 1
        if transcriber_attempts == 1:
            raise RuntimeError("Unable to open file 'model.bin'")
        return StubTranscriber()

    monkeypatch.setattr(ui, "prepare_whisper_model", prepare)  # type: ignore[attr-defined]
    monkeypatch.setattr(ui, "WhisperTranscriber", transcriber)  # type: ignore[attr-defined]
    monkeypatch.setattr(ui, "ensure_cleanup_model", lambda *args: tmp_path / "cleanup.gguf")  # type: ignore[attr-defined]

    window._load_models()

    assert forced == [False, True]
    assert transcriber_attempts == 2
    assert window.pipeline is not None


def test_history_tab_renders_and_searches_saved_transcripts(
    monkeypatch: object, tmp_path: Path
) -> None:
    window = make_window(monkeypatch, tmp_path)
    window.history.add(
        Transcript(
            "raw kentucky note",
            "Clean Kentucky note.",
            "en",
            1.5,
            CleanupMode.STANDARD,
        )
    )

    window.history_search.setText("Kentucky")
    window._refresh_history()

    rendered = window.history_results.toPlainText()
    assert "Clean Kentucky note." in rendered
    assert "Raw: raw kentucky note" in rendered
