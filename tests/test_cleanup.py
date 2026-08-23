from localscribe.cleanup import RuleBasedCleaner
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
