from __future__ import annotations

from pathlib import Path

from .domain import Cleaner, CleanupMode, Transcriber, Transcript


class DictationPipeline:
    def __init__(self, transcriber: Transcriber, cleaner: Cleaner) -> None:
        self.transcriber = transcriber
        self.cleaner = cleaner

    def process(self, audio_path: Path, mode: CleanupMode, vocabulary: list[str]) -> Transcript:
        raw, language, duration = self.transcriber.transcribe(audio_path, vocabulary)
        cleaned = self.cleaner.clean(raw, mode, vocabulary)
        return Transcript(raw, cleaned, language, duration, mode)
