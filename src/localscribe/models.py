from __future__ import annotations

from pathlib import Path

from .config import data_directory
from .domain import HardwareProfile

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


def ensure_cleanup_model(hardware: HardwareProfile) -> Path:
    """Download once into app data; inference is entirely local after that."""
    from huggingface_hub import hf_hub_download  # type: ignore[import-not-found]

    size = recommended_cleanup_size(hardware)
    repository, filename = MODEL_OPTIONS[size]
    model_dir = data_directory() / "models" / "cleanup"
    model_dir.mkdir(parents=True, exist_ok=True)
    destination = model_dir / filename
    if destination.is_file():
        return destination
    downloaded = hf_hub_download(repo_id=repository, filename=filename, local_dir=model_dir)
    return Path(downloaded)
