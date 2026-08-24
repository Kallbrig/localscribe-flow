from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import data_directory
from .domain import HardwareProfile

ProgressCallback = Callable[[str, int, int], None]

WHISPER_REPOSITORIES = {
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "tiny": "Systran/faster-whisper-tiny",
    "base.en": "Systran/faster-whisper-base.en",
    "base": "Systran/faster-whisper-base",
    "small.en": "Systran/faster-whisper-small.en",
    "small": "Systran/faster-whisper-small",
    "medium.en": "Systran/faster-whisper-medium.en",
    "medium": "Systran/faster-whisper-medium",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
}

WHISPER_FILES = [
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
]

MODEL_OPTIONS = {
    "tiny": (
        "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "qwen2.5-0.5b-instruct-q4_k_m.gguf",
    ),
    "balanced": (
        "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        "qwen2.5-1.5b-instruct-q4_k_m.gguf",
    ),
}


def recommended_cleanup_size(hardware: HardwareProfile) -> str:
    return "balanced" if hardware.memory_gb >= 8 else "tiny"


def _progress_class(stage: str, callback: ProgressCallback | None) -> type[Any] | None:
    if callback is None:
        return None
    from tqdm.auto import tqdm  # type: ignore[import-untyped]

    progress_callback = callback

    class ModelProgress(tqdm):  # type: ignore[misc]
        def update(self, amount: float | None = 1) -> bool | None:
            changed: bool | None = super().update(amount)
            progress_callback(stage, int(self.n), int(self.total or 0))
            return changed

        def close(self) -> None:
            if self.total:
                progress_callback(stage, int(self.total), int(self.total))
            super().close()

    return ModelProgress


def prepare_whisper_model(
    model_name: str,
    progress: ProgressCallback | None = None,
    force_download: bool = False,
) -> Path:
    """Download Whisper into app-owned storage so corrupt caches can be repaired."""
    from huggingface_hub import snapshot_download

    repository = WHISPER_REPOSITORIES.get(model_name, model_name)
    model_dir = data_directory() / "models" / "speech" / repository.replace("/", "--")
    model_dir.mkdir(parents=True, exist_ok=True)
    downloaded = snapshot_download(
        repo_id=repository,
        local_dir=model_dir,
        allow_patterns=WHISPER_FILES,
        force_download=force_download,
        tqdm_class=_progress_class("Downloading speech model", progress),
    )
    return Path(downloaded)


def ensure_cleanup_model(
    hardware: HardwareProfile,
    progress: ProgressCallback | None = None,
    force_download: bool = False,
) -> Path:
    """Download once into app data; inference is entirely local after that."""
    from huggingface_hub import hf_hub_download

    size = recommended_cleanup_size(hardware)
    repository, filename = MODEL_OPTIONS[size]
    model_dir = data_directory() / "models" / "cleanup"
    model_dir.mkdir(parents=True, exist_ok=True)
    destination = model_dir / filename
    if destination.is_file():
        return destination
    downloaded = hf_hub_download(
        repo_id=repository,
        filename=filename,
        local_dir=model_dir,
        force_download=force_download,
        tqdm_class=_progress_class("Downloading enhanced cleanup model", progress),
    )
    return Path(downloaded)
