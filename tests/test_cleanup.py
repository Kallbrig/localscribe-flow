from typing import Any

from localscribe.cleanup import LlamaCppCleaner, RuleBasedCleaner, _is_faithful
from localscribe.domain import CleanupMode


def test_standard_removes_fillers_repetitions_and_punctuates() -> None:
    cleaner = RuleBasedCleaner()
    assert cleaner.clean("um hello hello world", CleanupMode.STANDARD, []) == "Hello world."


def test_informal_preserves_filler() -> None:
    value = RuleBasedCleaner().clean("um this is fine", CleanupMode.INFORMAL, [])
    assert value == "Um this is fine"


def test_custom_word_casing_is_restored() -> None:
    value = RuleBasedCleaner().clean("openai builds tools", CleanupMode.STANDARD, ["OpenAI"])
    assert value == "OpenAI builds tools."


def test_modes_are_all_supported() -> None:
    cleaner = RuleBasedCleaner()
    for mode in CleanupMode:
        assert cleaner.clean("a short note", mode, [])


class ReplyingModel:
    def create_chat_completion(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "I'm fine, how about you? It's been interesting over there in Kentucky."
                        )
                    }
                }
            ]
        }


def test_cleanup_rejects_a_conversational_reply() -> None:
    cleaner = object.__new__(LlamaCppCleaner)
    cleaner._llm = ReplyingModel()
    source = "hi how are you? Hows it been going over there in kentucky"

    result = cleaner.clean(source, CleanupMode.STANDARD, [])

    assert "I'm fine" not in result
    assert "interesting" not in result
    assert result == "Hi how are you? Hows it been going over there in kentucky."


def test_fidelity_guard_preserves_questions_and_rejects_invented_meaning() -> None:
    source = "Hi, how are you? How's it been going over there in Kentucky?"

    assert _is_faithful(source, "Hi, how are you? How's it been going over there in Kentucky?")
    assert not _is_faithful(
        source, "I'm fine, how about you? It's been interesting over there in Kentucky."
    )
