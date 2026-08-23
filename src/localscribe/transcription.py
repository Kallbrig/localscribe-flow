from __future__ import annotations

from pathlib import Path

from .domain import HardwareProfile


class WhisperTranscriber:
    def __init__(
        self, model_name: str, hardware: HardwareProfile, language: str | None = None
    ) -> None:
        from faster_whisper import WhisperModel  # type: ignore[import-not-found]

        self.language = language
        self._model = WhisperModel(
            model_name,
            device=hardware.device,
            compute_type=hardware.compute_type,
            cpu_threads=max(1, hardware.logical_cores - 1),
        )

    def transcribe(self, audio_path: Path, vocabulary: list[str]) -> tuple[str, str, float]:
        prompt = "Important vocabulary: " + ", ".join(vocabulary) if vocabulary else None
        segments, info = self._model.transcribe(
            str(audio_path),
            language=self.language,
            initial_prompt=prompt,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 400},
            condition_on_previous_text=True,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text, info.language, float(info.duration)
