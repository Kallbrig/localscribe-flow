from __future__ import annotations

import ctypes
import os
import platform

import psutil

from .domain import HardwareProfile


def _cuda_runtime_available() -> bool:
    """CTranslate2 can be CUDA-enabled even when required runtime DLLs are absent."""
    if platform.system() == "Windows":
        try:
            ctypes.WinDLL("cublas64_12.dll")
        except OSError:
            return False
        return True
    if platform.system() == "Linux":
        try:
            ctypes.CDLL("libcublas.so.12")
        except OSError:
            return False
        return True
    return False


def detect_hardware() -> HardwareProfile:
    """Select the fastest conservative CTranslate2 configuration available."""
    cpu = platform.processor() or platform.machine() or "Unknown CPU"
    cores = psutil.cpu_count(logical=True) or os.cpu_count() or 1
    memory_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    reason = "CPU mode selected; quantization minimizes latency and memory"
    try:
        import ctranslate2

        cuda_types = set(ctranslate2.get_supported_compute_types("cuda"))
        cuda_ready = _cuda_runtime_available()
        if cuda_ready and "float16" in cuda_types:
            return HardwareProfile(
                "cuda",
                "float16",
                cpu,
                cores,
                memory_gb,
                "NVIDIA CUDA",
                "CUDA with FP16 is available",
            )
        if cuda_ready and "int8_float16" in cuda_types:
            return HardwareProfile(
                "cuda",
                "int8_float16",
                cpu,
                cores,
                memory_gb,
                "NVIDIA CUDA",
                "CUDA with mixed INT8/FP16 is available",
            )
        if cuda_types and not cuda_ready:
            reason = "CUDA engine detected but its runtime libraries are unavailable; using CPU"
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
        reason,
    )


def recommended_whisper_model(profile: HardwareProfile) -> str:
    if profile.device == "cuda" and profile.memory_gb >= 16:
        return "distil-large-v3"
    if profile.memory_gb >= 8:
        return "small.en"
    return "base.en"
