from __future__ import annotations

import contextlib
import os
import sqlite3
import threading
import time

from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .audio import AudioRecorder
from .cleanup import AutoCleaner
from .config import ConfigStore, data_directory
from .domain import CleanupMode, HardwareProfile, Transcript
from .history import TranscriptHistory
from .models import ensure_cleanup_model, prepare_whisper_model
from .pipeline import DictationPipeline
from .platforms import DesktopIntegration
from .transcription import WhisperTranscriber
from .updater import DownloadedUpdate, download_update, find_update


class Events(QObject):
    toggle = Signal()
    complete = Signal(object)
    failed = Signal(str)
    status = Signal(str)
    models_ready = Signal(object, str)
    models_complete = Signal()
    model_progress = Signal(str, int, int)
    startup_failed = Signal(str)
    update_ready = Signal(object)
    update_status = Signal(str, bool)


def app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor("#111827"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#67e8f9"))
    painter.setBrush(QColor("#22d3ee"))
    painter.drawRoundedRect(24, 10, 16, 31, 8, 8)
    painter.drawArc(17, 19, 30, 31, 180 * 16, 180 * 16)
    painter.drawLine(32, 42, 32, 53)
    painter.drawLine(23, 53, 41, 53)
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self, store: ConfigStore, hardware: HardwareProfile) -> None:
        super().__init__()
        self.store, self.config, self.hardware = store, store.load(), hardware
        self.recorder = AudioRecorder()
        self.integration = DesktopIntegration()
        self.history = TranscriptHistory(data_directory() / "history.sqlite3")
        self.pipeline: DictationPipeline | None = None
        self.events = Events()
        self.events.toggle.connect(self.toggle_recording)
        self.events.complete.connect(self._on_complete)
        self.events.failed.connect(self._on_failed)
        self.events.status.connect(self._set_status)
        self.events.models_ready.connect(self._on_models_ready)
        self.events.models_complete.connect(self._on_models_complete)
        self.events.model_progress.connect(self._on_model_progress)
        self.events.startup_failed.connect(self._on_startup_failed)
        self.events.update_ready.connect(self._on_update_ready)
        self.events.update_status.connect(self._set_update_status)
        self._checking_updates = False
        self._build_ui()
        self._build_tray()
        self._register_hotkey()
        if os.environ.get("LOCALSCRIBE_DIAGNOSTIC") == "1":
            self.events.status.emit("Diagnostic mode · UI and native dependencies loaded")
        else:
            threading.Thread(target=self._load_models, daemon=True).start()
            QTimer.singleShot(5000, self._auto_check_for_updates)

    def _build_ui(self) -> None:
        self.setWindowTitle("LocalScribe Flow")
        self.setWindowIcon(app_icon())
        self.resize(720, 570)
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("LocalScribe Flow")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #22d3ee")
        layout.addWidget(title)
        layout.addWidget(
            QLabel("Private voice dictation. Your audio and text stay on this device.")
        )
        tabs = QTabWidget()
        home = QWidget()
        home_layout = QVBoxLayout(home)
        self.status = QLabel("Starting local engines…")
        self.status.setStyleSheet("padding: 10px; background: #1f2937; border-radius: 6px")
        home_layout.addWidget(self.status)
        self.model_progress = QProgressBar()
        self.model_progress.setMinimumHeight(28)
        self.model_progress.setTextVisible(True)
        self.model_progress.setRange(0, 0)
        self.model_progress.setFormat("Preparing local models…")
        home_layout.addWidget(self.model_progress)
        row = QHBoxLayout()
        self.record = QPushButton("Start recording")
        self.record.setMinimumHeight(55)
        self.record.setEnabled(False)
        self.record.setText("Preparing speech model…")
        self.record.clicked.connect(self.toggle_recording)
        row.addWidget(self.record)
        self.mode = QComboBox()
        self.mode.addItems([mode.value.title() for mode in CleanupMode])
        self.mode.setCurrentText(self.config.mode.value.title())
        self.mode.currentTextChanged.connect(self._save_settings)
        row.addWidget(self.mode)
        home_layout.addLayout(row)
        self.retry = QPushButton("Retry model setup")
        self.retry.clicked.connect(self._retry_model_setup)
        self.retry.hide()
        home_layout.addWidget(self.retry)
        self.output = QTextEdit()
        self.output.setPlaceholderText("Your latest transcription appears here…")
        home_layout.addWidget(self.output)
        self.copy = QPushButton("Copy result")
        self.copy.clicked.connect(
            lambda: QApplication.clipboard().setText(self.output.toPlainText())
        )
        home_layout.addWidget(self.copy)
        tabs.addTab(home, "Dictate")
        history = QWidget()
        history_layout = QVBoxLayout(history)
        history_controls = QHBoxLayout()
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Search raw and cleaned transcript text…")
        self.history_search.textChanged.connect(self._refresh_history)
        history_controls.addWidget(self.history_search)
        refresh_history = QPushButton("Refresh")
        refresh_history.clicked.connect(self._refresh_history)
        history_controls.addWidget(refresh_history)
        clear_history = QPushButton("Clear history")
        clear_history.clicked.connect(self._clear_history)
        history_controls.addWidget(clear_history)
        history_layout.addLayout(history_controls)
        self.history_results = QTextEdit()
        self.history_results.setReadOnly(True)
        self.history_results.setPlaceholderText("Saved transcripts will appear here.")
        history_layout.addWidget(self.history_results)
        tabs.addTab(history, "History")
        settings = QWidget()
        form = QFormLayout(settings)
        self.hotkey = QLineEdit(self.config.hotkey)
        self.hotkey.editingFinished.connect(self._hotkey_changed)
        form.addRow("Global hotkey", self.hotkey)
        self.model = QLineEdit(self.config.whisper_model)
        self.model.editingFinished.connect(self._save_settings)
        form.addRow("Whisper model", self.model)
        self.llm_path = QLineEdit(self.config.llm_model_path)
        self.llm_path.setPlaceholderText("Optional path to a small GGUF instruct model")
        self.llm_path.editingFinished.connect(self._save_settings)
        form.addRow("Cleanup GGUF", self.llm_path)
        self.words = QTextEdit("\n".join(self.config.custom_words))
        self.words.setPlaceholderText("One custom name or technical term per line")
        self.words.textChanged.connect(self._save_settings)
        form.addRow("Custom words", self.words)
        self.auto_updates = QCheckBox("Check for updates automatically")
        self.auto_updates.setChecked(self.config.auto_check_updates)
        self.auto_updates.toggled.connect(self._save_settings)
        form.addRow("Updates", self.auto_updates)
        self.save_history = QCheckBox("Save transcripts locally (audio is never saved here)")
        self.save_history.setChecked(self.config.save_history)
        self.save_history.toggled.connect(self._save_settings)
        form.addRow("History", self.save_history)
        self.notify_complete = QCheckBox("Show a Windows notification when transcription completes")
        self.notify_complete.setChecked(self.config.notify_on_complete)
        self.notify_complete.toggled.connect(self._save_settings)
        form.addRow("Notifications", self.notify_complete)
        self.check_updates = QPushButton("Check for updates now")
        self.check_updates.clicked.connect(lambda: self._start_update_check(manual=True))
        form.addRow("", self.check_updates)
        self.update_status = QLabel(f"Installed version: {__version__}")
        self.update_status.setWordWrap(True)
        form.addRow("", self.update_status)
        hardware_text = (
            f"{self.hardware.accelerator or 'CPU'} · {self.hardware.logical_cores} threads · "
            f"{self.hardware.memory_gb} GB RAM\n"
            f"{self.hardware.device}/{self.hardware.compute_type}: {self.hardware.reason}"
        )
        form.addRow("Detected hardware", QLabel(hardware_text))
        tabs.addTab(settings, "Settings")
        self._refresh_history()
        layout.addWidget(tabs)
        self.setCentralWidget(root)
        self.setStyleSheet(
            "QWidget { background: #111827; color: #e5e7eb; font-size: 14px; } "
            "QLineEdit, QTextEdit, QComboBox { background: #1f2937; padding: 7px; } "
            "QPushButton { background: #0891b2; padding: 8px; border-radius: 5px; } "
            "QPushButton:disabled { background: #374151; }"
        )

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(app_icon(), self)
        menu = self.tray.contextMenu() or QMenu()
        show = QAction("Open LocalScribe Flow", self)
        show.triggered.connect(self.show)
        toggle = QAction("Start / stop recording", self)
        toggle.triggered.connect(self.toggle_recording)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addActions([show, toggle, quit_action])
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.show() if reason == QSystemTrayIcon.Trigger else None
        )
        self.tray.show()

    def _register_hotkey(self) -> None:
        try:
            self.integration.register_hotkey(self.config.hotkey, self.events.toggle.emit)
        except (ValueError, OSError) as exc:
            self.events.failed.emit(f"Could not register hotkey: {exc}")

    def _load_models(self) -> None:
        def progress(stage: str, current: int, total: int) -> None:
            self.events.model_progress.emit(stage, current, total)

        try:
            self.events.status.emit(
                "Preparing the private speech model… First launch may take several minutes "
                "while it downloads once."
            )
            model_path = prepare_whisper_model(self.config.whisper_model, progress)
            self.events.model_progress.emit("Loading speech model into memory", 0, 0)
            try:
                transcriber = WhisperTranscriber(
                    str(model_path), self.hardware, self.config.language
                )
            except Exception:
                self.events.status.emit("Repairing an incomplete speech model download…")
                model_path = prepare_whisper_model(
                    self.config.whisper_model, progress, force_download=True
                )
                transcriber = WhisperTranscriber(
                    str(model_path), self.hardware, self.config.language
                )
        except Exception as exc:  # model libraries surface backend-specific exceptions
            self.events.startup_failed.emit(f"Speech model setup failed: {exc}")
            return

        fallback = AutoCleaner("", self.hardware.logical_cores - 1, False)
        self.events.models_ready.emit(
            DictationPipeline(transcriber, fallback),
            f"Ready to dictate · {self.hardware.device}/{self.hardware.compute_type} · "
            "enhanced cleanup is preparing in the background",
        )

        try:
            llm_path = self.config.llm_model_path or str(
                ensure_cleanup_model(self.hardware, progress)
            )
            cleaner = AutoCleaner(
                llm_path, self.hardware.logical_cores - 1, self.hardware.device == "cuda"
            )
            self.events.models_ready.emit(
                DictationPipeline(transcriber, cleaner),
                f"Ready · {self.hardware.device}/{self.hardware.compute_type} · "
                f"cleanup: {cleaner.backend} · "
                f"hotkey: {self.config.hotkey}",
            )
            self.events.models_complete.emit()
        except Exception as exc:  # cleanup is optional; dictation remains available
            self.events.status.emit(
                f"Ready · basic local cleanup active · enhanced cleanup setup failed: {exc}"
            )
            self.events.models_complete.emit()

    def toggle_recording(self) -> None:
        if self.recorder.recording:
            self.record.setEnabled(False)
            self.record.setText("Transcribing…")
            threading.Thread(target=self._finish_recording, daemon=True).start()
            return
        if not self.pipeline:
            self._set_status("Preparing the speech model; recording will unlock when it is ready.")
            return
        try:
            self.recorder.start()
            self.record.setText("Stop and transcribe")
            self.status.setText("Recording… press the hotkey again to finish")
        except Exception as exc:
            self._on_failed(f"Microphone error: {exc}")

    def _finish_recording(self) -> None:
        path = data_directory() / "recordings" / f"dictation-{int(time.time())}.wav"
        try:
            self.recorder.stop(path)
            assert self.pipeline is not None
            result = self.pipeline.process(path, self.config.mode, self.config.custom_words)
            if not self.config.keep_recordings:
                path.unlink(missing_ok=True)
            self.events.complete.emit(result)
        except Exception as exc:
            self.events.failed.emit(f"Transcription failed: {exc}")

    def _on_complete(self, result: object) -> None:
        assert isinstance(result, Transcript)
        self.output.setPlainText(result.cleaned)
        self.record.setEnabled(True)
        self.record.setText("Start recording")
        self.status.setText(
            f"Done · {result.duration_seconds:.1f}s · language: {result.language} · "
            f"{result.mode.value}"
        )
        QApplication.clipboard().setText(result.cleaned)
        if self.config.save_history:
            with contextlib.suppress(OSError, sqlite3.Error):
                self.history.add(result)
                self._refresh_history()
        if self.config.paste_after_transcription:
            with contextlib.suppress(Exception):
                self.integration.paste_text(result.cleaned)
        if self.config.notify_on_complete:
            self.tray.showMessage("LocalScribe Flow", "Transcription copied to clipboard")

    def _on_failed(self, message: str) -> None:
        self.record.setEnabled(True)
        self.record.setText("Start recording")
        self.status.setText(message)
        QMessageBox.warning(self, "LocalScribe Flow", message)

    def _set_status(self, message: str) -> None:
        self.status.setText(message)

    def _on_models_ready(self, pipeline: object, message: str) -> None:
        assert isinstance(pipeline, DictationPipeline)
        self.pipeline = pipeline
        if not self.recorder.recording:
            self.record.setEnabled(True)
            self.record.setText("Start recording")
        self.retry.hide()
        self.status.setText(message)

    def _on_startup_failed(self, message: str) -> None:
        self.pipeline = None
        self.record.setEnabled(False)
        self.record.setText("Speech model unavailable")
        self.retry.show()
        self.model_progress.hide()
        self.status.setText(message)

    def _retry_model_setup(self) -> None:
        self.retry.hide()
        self.record.setEnabled(False)
        self.record.setText("Preparing speech model…")
        self.model_progress.setRange(0, 0)
        self.model_progress.setFormat("Preparing local models…")
        self.model_progress.show()
        threading.Thread(target=self._load_models, daemon=True).start()

    def _on_model_progress(self, stage: str, current: int, total: int) -> None:
        self.model_progress.show()
        if total > 0:
            percentage = min(100, round(current * 100 / total))
            self.model_progress.setRange(0, 100)
            self.model_progress.setValue(percentage)
            downloaded_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.model_progress.setFormat(f"{stage} · {downloaded_mb:.1f}/{total_mb:.1f} MB · %p%")
        else:
            self.model_progress.setRange(0, 0)
            self.model_progress.setFormat(f"{stage}…")

    def _on_models_complete(self) -> None:
        self.model_progress.setRange(0, 100)
        self.model_progress.setValue(100)
        self.model_progress.setFormat("Local models ready · 100%")
        QTimer.singleShot(1200, self.model_progress.hide)

    def _auto_check_for_updates(self) -> None:
        if self.config.auto_check_updates:
            self._start_update_check(manual=False)

    def _start_update_check(self, manual: bool) -> None:
        if self._checking_updates:
            if manual:
                self.update_status.setText("An update check is already running.")
            return
        self._checking_updates = True
        self.check_updates.setEnabled(False)
        self.update_status.setText("Checking GitHub for updates…")
        threading.Thread(
            target=self._check_and_download_update, args=(manual,), daemon=True
        ).start()

    def _check_and_download_update(self, manual: bool) -> None:
        try:
            update = find_update(__version__)
            if update is None:
                message = (
                    "You have the latest version."
                    if manual
                    else f"Version {__version__} is current."
                )
                self.events.update_status.emit(message, True)
                return
            self.events.update_status.emit(f"Downloading version {update.version} securely…", False)
            downloaded = download_update(update, data_directory() / "updates")
            self.events.update_ready.emit(downloaded)
        except Exception as exc:
            prefix = "Update check failed" if manual else "Automatic update check failed"
            self.events.update_status.emit(f"{prefix}: {exc}", True)

    def _set_update_status(self, message: str, finished: bool) -> None:
        if finished:
            self._checking_updates = False
            self.check_updates.setEnabled(True)
        self.update_status.setText(message)

    def _on_update_ready(self, update: object) -> None:
        assert isinstance(update, DownloadedUpdate)
        self._checking_updates = False
        self.check_updates.setEnabled(True)
        self.update_status.setText(f"Version {update.version} is downloaded and verified.")
        answer = QMessageBox.question(
            self,
            "LocalScribe Flow update ready",
            f"Version {update.version} has been downloaded and verified. Install it now? "
            "LocalScribe Flow will close before the installer opens.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            launch_result = QProcess.startDetached(str(update.installer_path), [])
            launched = launch_result[0] if isinstance(launch_result, tuple) else launch_result
            if launched:
                QApplication.quit()
            else:
                self._on_failed("The update installer could not be opened.")

    def _refresh_history(self, *_args: object) -> None:
        entries = self.history.search(self.history_search.text())
        blocks: list[str] = []
        for entry in entries:
            timestamp = entry.created_at.replace("T", " ").replace("+00:00", " UTC")
            header = (
                f"{timestamp} · {entry.mode.value.title()} · {entry.language} · "
                f"{entry.duration_seconds:.1f}s"
            )
            block = f"{header}\n{entry.cleaned}"
            if entry.raw.strip() != entry.cleaned.strip():
                block += f"\nRaw: {entry.raw}"
            blocks.append(block)
        self.history_results.setPlainText("\n\n────────────────────\n\n".join(blocks))

    def _clear_history(self) -> None:
        answer = QMessageBox.question(
            self,
            "Clear transcript history",
            "Permanently delete all locally saved transcript history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.history.clear()
            self._refresh_history()

    def _save_settings(self) -> None:
        self.config.mode = CleanupMode(self.mode.currentText().lower())
        self.config.whisper_model = self.model.text().strip() or "small.en"
        self.config.llm_model_path = self.llm_path.text().strip()
        self.config.custom_words = [
            w.strip() for w in self.words.toPlainText().splitlines() if w.strip()
        ]
        self.config.auto_check_updates = self.auto_updates.isChecked()
        self.config.save_history = self.save_history.isChecked()
        self.config.notify_on_complete = self.notify_complete.isChecked()
        self.store.save(self.config)

    def _hotkey_changed(self) -> None:
        self.config.hotkey = self.hotkey.text().strip() or "<ctrl>+<shift>+<space>"
        self._save_settings()
        self._register_hotkey()

    def closeEvent(self, event: object) -> None:
        event.ignore()
        self.hide()
        self.tray.showMessage("LocalScribe Flow", "Still running in the system tray")
