from __future__ import annotations

import os
import platform

import psutil

from .domain import HardwareProfile


def detect_hardware() -> HardwareProfile:
    """Select the fastest conservative CTranslate2 configuration available."""
    cpu = platform.processor() or platform.machine() or "Unknown CPU"
    cores = psutil.cpu_count(logical=True) or os.cpu_count() or 1
    memory_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    try:
        import ctranslate2  # type: ignore[import-not-found]

        cuda_types = set(ctranslate2.get_supported_compute_types("cuda"))
        if "float16" in cuda_types:
            return HardwareProfile(
                "cuda",
                "float16",
                cpu,
                cores,
                memory_gb,
                "NVIDIA CUDA",
                "CUDA with FP16 is available",
            )
        if "int8_float16" in cuda_types:
            return HardwareProfile(
                "cuda",
                "int8_float16",
                cpu,
                cores,
                memory_gb,
                "NVIDIA CUDA",
                "CUDA with mixed INT8/FP16 is available",
            )
    except (ImportError, RuntimeError, OSError):
        pass
    compute = "int8" if memory_gb < 12 else "int8_float32"
    return HardwareProfile(
        "cpu",
        compute,
        cpu,
        cores,
        memory_gb,
        None,
        "CPU mode selected; quantization minimizes latency and memory",
    )


def recommended_whisper_model(profile: HardwareProfile) -> str:
    if profile.device == "cuda" and profile.memory_gb >= 16:
        return "distil-large-v3"
    if profile.memory_gb >= 8:
        return "small.en"
    return "base.en"
