from localscribe.domain import CleanupMode, Transcript
from localscribe.history import TranscriptHistory


def transcript(raw: str, cleaned: str) -> Transcript:
    return Transcript(raw, cleaned, "en", 2.5, CleanupMode.STANDARD)


def test_history_saves_and_searches_raw_and_cleaned_text(tmp_path) -> None:
    history = TranscriptHistory(tmp_path / "history.sqlite3")
    history.add(transcript("hello kentucky", "Hello Kentucky."))
    history.add(transcript("project update", "The launch is ready."))

    kentucky = history.search("KENTUCKY")
    launch = history.search("launch")

    assert len(kentucky) == 1
    assert kentucky[0].raw == "hello kentucky"
    assert kentucky[0].cleaned == "Hello Kentucky."
    assert kentucky[0].mode is CleanupMode.STANDARD
    assert len(launch) == 1
    assert launch[0].raw == "project update"


def test_history_search_treats_wildcards_as_text_and_can_clear(tmp_path) -> None:
    history = TranscriptHistory(tmp_path / "history.sqlite3")
    history.add(transcript("100% local", "100% local."))
    history.add(transcript("ordinary note", "Ordinary note."))

    assert len(history.search("%")) == 1

    history.clear()
    assert history.search() == []
