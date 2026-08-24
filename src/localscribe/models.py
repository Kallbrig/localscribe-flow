from __future__ import annotations

import hashlib
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

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

WHISPER_FILES = {"config.json", "model.bin", "tokenizer.json", "vocabulary.txt"}
DOWNLOAD_TIMEOUT_SECONDS = 30
DOWNLOAD_ATTEMPTS = 3


class ModelDownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelFile:
    name: str
    size: int
    sha256: str | None = None


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


def _whisper_manifest(repository: str) -> list[ModelFile]:
    from huggingface_hub import HfApi

    info = HfApi().model_info(repository, files_metadata=True, timeout=15)
    files: list[ModelFile] = []
    for sibling in info.siblings or []:
        if sibling.rfilename not in WHISPER_FILES or sibling.size is None:
            continue
        checksum = sibling.lfs.sha256 if sibling.lfs else None
        files.append(ModelFile(sibling.rfilename, sibling.size, checksum))
    missing = WHISPER_FILES.difference(item.name for item in files)
    if missing:
        raise ModelDownloadError(
            f"Model repository is missing required files: {', '.join(missing)}"
        )
    return sorted(files, key=lambda item: item.name == "model.bin")


def _repository_file(repository: str, filename: str) -> ModelFile:
    from huggingface_hub import HfApi

    info = HfApi().model_info(repository, files_metadata=True, timeout=15)
    for sibling in info.siblings or []:
        if sibling.rfilename == filename and sibling.size is not None:
            checksum = sibling.lfs.sha256 if sibling.lfs else None
            return ModelFile(filename, sibling.size, checksum)
    raise ModelDownloadError(f"Model repository is missing required file: {filename}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_model_download(repository: str, filename: str, start: int) -> Any:
    encoded_repository = quote(repository, safe="/")
    encoded_filename = quote(filename, safe="")
    url = f"https://huggingface.co/{encoded_repository}/resolve/main/{encoded_filename}"
    headers = {"User-Agent": "LocalScribe-Model-Downloader"}
    if start:
        headers["Range"] = f"bytes={start}-"
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS)  # noqa: S310


def _download_model_file(
    repository: str,
    model_file: ModelFile,
    model_dir: Path,
    completed: int,
    total: int,
    progress: ProgressCallback | None,
    force_download: bool,
    stage: str = "Downloading speech model",
) -> None:
    destination = model_dir / model_file.name
    partial = destination.with_suffix(destination.suffix + ".part")
    if force_download:
        destination.unlink(missing_ok=True)
        partial.unlink(missing_ok=True)
    if destination.is_file() and destination.stat().st_size == model_file.size:
        if progress:
            progress(stage, completed + model_file.size, total)
        return
    if partial.is_file() and partial.stat().st_size > model_file.size:
        partial.unlink()

    last_error: Exception | None = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            offset = partial.stat().st_size if partial.is_file() else 0
            if offset == model_file.size:
                partial.replace(destination)
                break
            with _open_model_download(repository, model_file.name, offset) as response:
                append = offset > 0 and getattr(response, "status", 200) == 206
                if offset and not append:
                    offset = 0
                with partial.open("ab" if append else "wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                        offset += len(chunk)
                        if progress:
                            progress(
                                f"{stage} ({model_file.name})",
                                completed + offset,
                                total,
                            )
            if partial.stat().st_size != model_file.size:
                raise ModelDownloadError(
                    f"{model_file.name} ended at {partial.stat().st_size} "
                    f"of {model_file.size} bytes"
                )
            partial.replace(destination)
            break
        except Exception as exc:
            last_error = exc
            if attempt == DOWNLOAD_ATTEMPTS:
                raise ModelDownloadError(
                    f"Download stalled or failed after {attempt} attempts "
                    f"for {model_file.name}: {exc}"
                ) from exc
            if progress:
                current = partial.stat().st_size if partial.is_file() else 0
                progress(
                    f"Connection interrupted; resuming {model_file.name} "
                    f"(attempt {attempt + 1}/{DOWNLOAD_ATTEMPTS})",
                    completed + current,
                    total,
                )
            time.sleep(attempt)
    if not destination.is_file():
        raise ModelDownloadError(f"Download did not produce {model_file.name}: {last_error}")
    if model_file.sha256 and _sha256(destination) != model_file.sha256:
        destination.unlink(missing_ok=True)
        raise ModelDownloadError(f"Integrity verification failed for {model_file.name}")


def prepare_whisper_model(
    model_name: str,
    progress: ProgressCallback | None = None,
    force_download: bool = False,
) -> Path:
    """Download Whisper into app-owned storage so corrupt caches can be repaired."""
    repository = WHISPER_REPOSITORIES.get(model_name, model_name)
    model_dir = data_directory() / "models" / "speech" / repository.replace("/", "--")
    model_dir.mkdir(parents=True, exist_ok=True)
    manifest = _whisper_manifest(repository)
    total = sum(item.size for item in manifest)
    completed = 0
    for model_file in manifest:
        _download_model_file(
            repository,
            model_file,
            model_dir,
            completed,
            total,
            progress,
            force_download,
            "Downloading speech model",
        )
        completed += model_file.size
    return model_dir


def ensure_cleanup_model(
    hardware: HardwareProfile,
    progress: ProgressCallback | None = None,
    force_download: bool = False,
) -> Path:
    """Download once into app data; inference is entirely local after that."""
    size = recommended_cleanup_size(hardware)
    repository, filename = MODEL_OPTIONS[size]
    model_dir = data_directory() / "models" / "cleanup"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_file = _repository_file(repository, filename)
    _download_model_file(
        repository,
        model_file,
        model_dir,
        0,
        model_file.size,
        progress,
        force_download,
        "Downloading enhanced cleanup model",
    )
    return model_dir / filename
