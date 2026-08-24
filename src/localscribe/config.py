from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

from . import APP_NAME, LEGACY_APP_NAME
from .domain import CleanupMode


@dataclass
class AppConfig:
    mode: CleanupMode = CleanupMode.STANDARD
    hotkey: str = "<ctrl>+<shift>+<space>"
    whisper_model: str = "small.en"
    language: str | None = None
    cleanup_backend: str = "auto"
    llm_model_path: str = ""
    custom_words: list[str] = field(default_factory=list)
    paste_after_transcription: bool = True
    keep_recordings: bool = False
    auto_check_updates: bool = True
    save_history: bool = True
    notify_on_complete: bool = False


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            _migrate_legacy_storage()
        self.path = path or Path(user_config_dir(APP_NAME)) / "config.json"

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            data["mode"] = CleanupMode(data.get("mode", CleanupMode.STANDARD))
            allowed = AppConfig.__dataclass_fields__.keys()
            return AppConfig(**{k: v for k, v in data.items() if k in allowed})
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(config)
        payload["mode"] = config.mode.value
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.path)


def data_directory() -> Path:
    override = os.environ.get("LOCALSCRIBE_DATA_DIR")
    if not override:
        _migrate_legacy_storage()
    path = Path(override) if override else Path(user_data_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _migrate_legacy_storage() -> None:
    locations = {
        (Path(user_config_dir(LEGACY_APP_NAME)), Path(user_config_dir(APP_NAME))),
        (Path(user_data_dir(LEGACY_APP_NAME)), Path(user_data_dir(APP_NAME))),
    }
    for legacy, current in locations:
        if legacy == current or current.exists() or not legacy.exists():
            continue
        current.parent.mkdir(parents=True, exist_ok=True)
        try:
            legacy.replace(current)
        except OSError:
            # Cross-volume or locked-directory fallback. Keep the legacy copy if cleanup fails.
            shutil.copytree(legacy, current, dirs_exist_ok=True)
