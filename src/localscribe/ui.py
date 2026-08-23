from __future__ import annotations

import contextlib
import os
import threading
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .audio import AudioRecorder
from .cleanup import AutoCleaner
from .config import ConfigStore, data_directory
from .domain import CleanupMode, HardwareProfile
from .models import ensure_cleanup_model
from .pipeline import DictationPipeline
from .platforms import DesktopIntegration
from .transcription import WhisperTranscriber


class Events(QObject):
    toggle = Signal()
    complete = Signal(object)
    failed = Signal(str)
    status = Signal(str)


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
        self.pipeline: DictationPipeline | None = None
        self.events = Events()
        self.events.toggle.connect(self.toggle_recording)
        self.events.complete.connect(self._on_complete)
        self.events.failed.connect(self._on_failed)
        self.events.status.connect(self._set_status)
        self._build_ui()
        self._build_tray()
        self._register_hotkey()
        if os.environ.get("LOCALSCRIBE_DIAGNOSTIC") == "1":
            self.events.status.emit("Diagnostic mode · UI and native dependencies loaded")
        else:
            threading.Thread(target=self._load_models, daemon=True).start()

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
        row = QHBoxLayout()
        self.record = QPushButton("Start recording")
        self.record.setMinimumHeight(55)
        self.record.clicked.connect(self.toggle_recording)
        row.addWidget(self.record)
        self.mode = QComboBox()
        self.mode.addItems([mode.value.title() for mode in CleanupMode])
        self.mode.setCurrentText(self.config.mode.value.title())
        self.mode.currentTextChanged.connect(self._save_settings)
        row.addWidget(self.mode)
        home_layout.addLayout(row)
        self.output = QTextEdit()
        self.output.setPlaceholderText("Your latest transcription appears here…")
        home_layout.addWidget(self.output)
        self.copy = QPushButton("Copy result")
        self.copy.clicked.connect(
            lambda: QApplication.clipboard().setText(self.output.toPlainText())
        )
        home_layout.addWidget(self.copy)
        tabs.addTab(home, "Dictate")
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
        hardware_text = (
            f"{self.hardware.accelerator or 'CPU'} · {self.hardware.logical_cores} threads · "
            f"{self.hardware.memory_gb} GB RAM\n"
            f"{self.hardware.device}/{self.hardware.compute_type}: {self.hardware.reason}"
        )
        form.addRow("Detected hardware", QLabel(hardware_text))
        tabs.addTab(settings, "Settings")
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
        try:
            self.events.status.emit(
                "Loading Whisper locally (first launch may download the model)…"
            )
            transcriber = WhisperTranscriber(
                self.config.whisper_model,
                self.hardware,
                self.config.language,
            )
            llm_path = self.config.llm_model_path
            if not llm_path:
                self.events.status.emit("Preparing the private cleanup model (one-time download)…")
                llm_path = str(ensure_cleanup_model(self.hardware))
            cleaner = AutoCleaner(
                llm_path,
                self.hardware.logical_cores - 1,
                self.hardware.device == "cuda",
            )
            self.pipeline = DictationPipeline(transcriber, cleaner)
            self.events.status.emit(
                f"Ready · {self.hardware.device}/{self.hardware.compute_type} · "
                f"cleanup: {cleaner.backend} · "
                f"hotkey: {self.config.hotkey}"
            )
        except Exception as exc:  # model libraries surface several backend-specific exceptions
            self.events.failed.emit(f"Engine startup failed: {exc}")

    def toggle_recording(self) -> None:
        if self.recorder.recording:
            self.record.setEnabled(False)
            self.record.setText("Transcribing…")
            threading.Thread(target=self._finish_recording, daemon=True).start()
            return
        if not self.pipeline:
            self._on_failed("The local models are still loading.")
            return
        try:
            self.recorder.start()
            self.record.setText("Stop and transcribe")
            self.status.setText("Recording… press the hotkey again to finish")
            self.tray.showMessage("LocalScribe Flow", "Recording started")
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
        from .domain import Transcript

        assert isinstance(result, Transcript)
        self.output.setPlainText(result.cleaned)
        self.record.setEnabled(True)
        self.record.setText("Start recording")
        self.status.setText(
            f"Done · {result.duration_seconds:.1f}s · language: {result.language} · "
            f"{result.mode.value}"
        )
        QApplication.clipboard().setText(result.cleaned)
        if self.config.paste_after_transcription:
            with contextlib.suppress(Exception):
                self.integration.paste_text(result.cleaned)
        self.tray.showMessage("LocalScribe Flow", "Transcription copied to clipboard")

    def _on_failed(self, message: str) -> None:
        self.record.setEnabled(True)
        self.record.setText("Start recording")
        self.status.setText(message)
        QMessageBox.warning(self, "LocalScribe Flow", message)

    def _set_status(self, message: str) -> None:
        self.status.setText(message)

    def _save_settings(self) -> None:
        self.config.mode = CleanupMode(self.mode.currentText().lower())
        self.config.whisper_model = self.model.text().strip() or "small.en"
        self.config.llm_model_path = self.llm_path.text().strip()
        self.config.custom_words = [
            w.strip() for w in self.words.toPlainText().splitlines() if w.strip()
        ]
        self.store.save(self.config)

    def _hotkey_changed(self) -> None:
        self.config.hotkey = self.hotkey.text().strip() or "<ctrl>+<shift>+<space>"
        self._save_settings()
        self._register_hotkey()

    def closeEvent(self, event: object) -> None:
        event.ignore()
        self.hide()
        self.tray.showMessage("LocalScribe Flow", "Still running in the system tray")
