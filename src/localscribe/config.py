from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

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


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(user_config_dir("LocalScribe Flow")) / "config.json"

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
    path = Path(user_data_dir("LocalScribe Flow"))
    path.mkdir(parents=True, exist_ok=True)
    return path
