from types import SimpleNamespace
from unittest.mock import patch

from localscribe.hardware import (
    _cuda_runtime_available,
    detect_hardware,
    recommended_whisper_model,
)


def test_cpu_fallback() -> None:
    with patch("psutil.virtual_memory") as memory, patch.dict("sys.modules", {"ctranslate2": None}):
        memory.return_value.total = 8 * 1024**3
        profile = detect_hardware()
    assert profile.device == "cpu"
    assert profile.compute_type == "int8"
    assert recommended_whisper_model(profile) == "small.en"


def test_low_memory_recommendation() -> None:
    with patch("psutil.virtual_memory") as memory, patch.dict("sys.modules", {"ctranslate2": None}):
        memory.return_value.total = 4 * 1024**3
        profile = detect_hardware()
    assert profile.compute_type == "int8"
    assert recommended_whisper_model(profile) == "base.en"


def test_cuda_requires_loadable_runtime() -> None:
    ctranslate = SimpleNamespace(get_supported_compute_types=lambda _device: {"float16"})
    with (
        patch("psutil.virtual_memory") as memory,
        patch.dict("sys.modules", {"ctranslate2": ctranslate}),
        patch("localscribe.hardware._cuda_runtime_available", return_value=False),
    ):
        memory.return_value.total = 16 * 1024**3
        profile = detect_hardware()
    assert profile.device == "cpu"


def test_cuda_selected_when_runtime_is_ready() -> None:
    ctranslate = SimpleNamespace(get_supported_compute_types=lambda _device: {"float16"})
    with (
        patch("psutil.virtual_memory") as memory,
        patch.dict("sys.modules", {"ctranslate2": ctranslate}),
        patch("localscribe.hardware._cuda_runtime_available", return_value=True),
    ):
        memory.return_value.total = 16 * 1024**3
        profile = detect_hardware()
    assert profile.device == "cuda"
    assert profile.compute_type == "float16"
    assert recommended_whisper_model(profile) == "distil-large-v3"


def test_windows_cuda_runtime_probe() -> None:
    with patch("platform.system", return_value="Windows"), patch("ctypes.WinDLL") as loader:
        assert _cuda_runtime_available()
        loader.assert_called_once_with("cublas64_12.dll")


def test_cuda_runtime_probe_rejects_missing_library() -> None:
    with (
        patch("platform.system", return_value="Windows"),
        patch("ctypes.WinDLL", side_effect=OSError),
    ):
        assert not _cuda_runtime_available()


def test_cuda_runtime_probe_rejects_other_platforms() -> None:
    with patch("platform.system", return_value="Darwin"):
        assert not _cuda_runtime_available()
