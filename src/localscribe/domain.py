from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class CleanupMode(StrEnum):
    INFORMAL = "informal"
    CASUAL = "casual"
    STANDARD = "standard"
    BUSINESS = "business"


@dataclass(frozen=True)
class HardwareProfile:
    device: str
    compute_type: str
    cpu: str
    logical_cores: int
    memory_gb: float
    accelerator: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class Transcript:
    raw: str
    cleaned: str
    language: str
    duration_seconds: float
    mode: CleanupMode


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path, vocabulary: list[str]) -> tuple[str, str, float]: ...


class Cleaner(Protocol):
    def clean(self, text: str, mode: CleanupMode, vocabulary: list[str]) -> str: ...
