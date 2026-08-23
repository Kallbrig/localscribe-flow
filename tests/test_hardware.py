from unittest.mock import patch

from localscribe.hardware import detect_hardware, recommended_whisper_model


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
