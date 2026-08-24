import hashlib
from pathlib import Path

import pytest

from localscribe import models
from localscribe.domain import HardwareProfile
from localscribe.models import ModelFile, prepare_whisper_model, recommended_cleanup_size


def profile(memory: float) -> HardwareProfile:
    return HardwareProfile("cpu", "int8", "cpu", 4, memory)


def test_small_memory_gets_tiny_model() -> None:
    assert recommended_cleanup_size(profile(4)) == "tiny"


def test_normal_memory_gets_balanced_model() -> None:
    assert recommended_cleanup_size(profile(16)) == "balanced"


def test_whisper_download_uses_app_storage_and_can_force_repair(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, bool]] = []
    manifest = [ModelFile("model.bin", 3, hashlib.sha256(b"abc").hexdigest())]

    def fake_download(
        repository: str,
        model_file: ModelFile,
        model_dir: Path,
        completed: int,
        total: int,
        progress: object,
        force_download: bool,
        stage: str,
    ) -> None:
        calls.append((repository, force_download))

    monkeypatch.setattr(models, "data_directory", lambda: tmp_path)
    monkeypatch.setattr(models, "_whisper_manifest", lambda repository: manifest)
    monkeypatch.setattr(models, "_download_model_file", fake_download)

    path = prepare_whisper_model("small.en", force_download=True)

    assert path == tmp_path / "models" / "speech" / "Systran--faster-whisper-small.en"
    assert calls == [("Systran/faster-whisper-small.en", True)]


class InterruptedResponse:
    def __init__(self, chunks: list[bytes | Exception], status: int) -> None:
        self.chunks = chunks
        self.status = status

    def __enter__(self) -> "InterruptedResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        value = self.chunks.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def test_interrupted_download_resumes_and_completes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    content = b"abcdef"
    responses = [
        InterruptedResponse([b"abc", TimeoutError("stalled")], 200),
        InterruptedResponse([b"def", b""], 206),
    ]
    offsets: list[int] = []
    progress: list[tuple[int, int]] = []

    def open_download(repository: str, filename: str, start: int) -> InterruptedResponse:
        offsets.append(start)
        return responses.pop(0)

    monkeypatch.setattr(models, "_open_model_download", open_download)
    monkeypatch.setattr(models.time, "sleep", lambda seconds: None)
    model_file = ModelFile("model.bin", len(content), hashlib.sha256(content).hexdigest())

    models._download_model_file(
        "example/model",
        model_file,
        tmp_path,
        0,
        len(content),
        lambda stage, current, total: progress.append((current, total)),
        False,
    )

    assert offsets == [0, 3]
    assert (tmp_path / "model.bin").read_bytes() == content
    assert progress[-1] == (len(content), len(content))
