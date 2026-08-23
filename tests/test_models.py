from localscribe.domain import HardwareProfile
from localscribe.models import recommended_cleanup_size


def profile(memory: float) -> HardwareProfile:
    return HardwareProfile("cpu", "int8", "cpu", 4, memory)


def test_small_memory_gets_tiny_model() -> None:
    assert recommended_cleanup_size(profile(4)) == "tiny"


def test_normal_memory_gets_balanced_model() -> None:
    assert recommended_cleanup_size(profile(16)) == "balanced"
