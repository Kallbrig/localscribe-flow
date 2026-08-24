from pathlib import Path

import huggingface_hub
import pytest

from localscribe import models
from localscribe.domain import HardwareProfile
from localscribe.models import prepare_whisper_model, recommended_cleanup_size


def profile(memory: float) -> HardwareProfile:
    return HardwareProfile("cpu", "int8", "cpu", 4, memory)


def test_small_memory_gets_tiny_model() -> None:
    assert recommended_cleanup_size(profile(4)) == "tiny"


def test_normal_memory_gets_balanced_model() -> None:
    assert recommended_cleanup_size(profile(16)) == "balanced"


def test_whisper_download_uses_app_storage_and_can_force_repair(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def fake_snapshot_download(**kwargs: object) -> str:
        captured.update(kwargs)
        return str(kwargs["local_dir"])

    monkeypatch.setattr(models, "data_directory", lambda: tmp_path)
    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_snapshot_download)

    path = prepare_whisper_model("small.en", force_download=True)

    assert path == tmp_path / "models" / "speech" / "Systran--faster-whisper-small.en"
    assert captured["repo_id"] == "Systran/faster-whisper-small.en"
    assert captured["force_download"] is True
