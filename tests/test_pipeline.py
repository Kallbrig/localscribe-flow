from pathlib import Path

from localscribe.domain import CleanupMode
from localscribe.pipeline import DictationPipeline


class FakeTranscriber:
    def transcribe(self, audio_path: Path, vocabulary: list[str]) -> tuple[str, str, float]:
        assert audio_path.name == "sample.wav"
        return "raw words", "en", 1.25


class FakeCleaner:
    def clean(self, text: str, mode: CleanupMode, vocabulary: list[str]) -> str:
        return f"{mode.value}: {text}"


def test_pipeline_composes_local_engines(tmp_path) -> None:
    result = DictationPipeline(FakeTranscriber(), FakeCleaner()).process(
        tmp_path / "sample.wav", CleanupMode.BUSINESS, ["term"]
    )
    assert result.cleaned == "business: raw words"
    assert result.duration_seconds == 1.25
