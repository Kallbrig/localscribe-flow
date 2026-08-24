"""Release gate: download, initialize, and run both local model engines on Windows."""

from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path

from localscribe.cleanup import AutoCleaner
from localscribe.domain import CleanupMode, HardwareProfile
from localscribe.models import ensure_cleanup_model, prepare_whisper_model
from localscribe.transcription import WhisperTranscriber


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="localscribe-model-test-") as temporary:
        root = Path(temporary)
        os.environ["LOCALSCRIBE_DATA_DIR"] = str(root / "data")
        last_progress = 0

        def progress(stage: str, current: int, total: int) -> None:
            nonlocal last_progress
            last_progress = current
            if total:
                print(f"{stage}: {current * 100 // total}%")

        model_path = prepare_whisper_model("tiny.en", progress)
        model_file = model_path / "model.bin"
        assert model_file.is_file() and model_file.stat().st_size > 70_000_000
        assert last_progress > 70_000_000

        audio_path = root / "silence.wav"
        with wave.open(str(audio_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16_000)
            audio.writeframes(b"\x00\x00" * 16_000)

        hardware = HardwareProfile("cpu", "int8", "CI CPU", 2, 4.0)
        transcriber = WhisperTranscriber(str(model_path), hardware, "en")
        text, language, duration = transcriber.transcribe(audio_path, [])
        assert text == ""
        assert language == "en"
        assert duration > 0

        cleanup_path = ensure_cleanup_model(hardware, progress)
        assert cleanup_path.is_file() and cleanup_path.stat().st_size > 450_000_000
        cleaner = AutoCleaner(str(cleanup_path), threads=2, use_gpu=False)
        assert cleaner.backend == "llama.cpp"
        cleaned = cleaner.clean("um hello from localscribe", CleanupMode.STANDARD, ["LocalScribe"])
        assert cleaned.strip()
        question = "Hi, how are you? How's it been going over there in Kentucky?"
        question_cleaned = cleaner.clean(question, CleanupMode.STANDARD, [])
        assert "I'm fine" not in question_cleaned
        assert "interesting" not in question_cleaned
        assert question_cleaned.count("?") == question.count("?")
        print("Real speech and cleanup model downloads, initialization, and inference passed.")


if __name__ == "__main__":
    main()
