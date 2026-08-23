from __future__ import annotations

import re
from pathlib import Path

from .domain import CleanupMode

FILLERS = re.compile(r"\b(?:um+|uh+|erm+|ah+|you know|like)\b[,.]?\s*", re.IGNORECASE)
REPEATED = re.compile(r"\b([\w'-]+)(?:\s+\1\b)+", re.IGNORECASE)
SPACES = re.compile(r"[ \t]+")
PROMPTS = {
    CleanupMode.INFORMAL: "Keep the speaker's voice and slang. Remove stumbles only.",
    CleanupMode.CASUAL: "Make it friendly and concise with natural conversational grammar.",
    CleanupMode.STANDARD: "Correct grammar and punctuation while preserving meaning and tone.",
    CleanupMode.BUSINESS: "Rewrite as polished, concise professional communication.",
}


def _restore_words(text: str, vocabulary: list[str]) -> str:
    for word in sorted(vocabulary, key=len, reverse=True):
        if word.strip():
            text = re.sub(rf"\b{re.escape(word)}\b", word, text, flags=re.IGNORECASE)
    return text


class RuleBasedCleaner:
    """Deterministic offline fallback used when no GGUF model is configured."""

    def clean(self, text: str, mode: CleanupMode, vocabulary: list[str]) -> str:
        value = SPACES.sub(" ", text).strip()
        value = REPEATED.sub(r"\1", value)
        if mode is not CleanupMode.INFORMAL:
            value = FILLERS.sub("", value)
        value = re.sub(r"\s+([,.;!?])", r"\1", value)
        value = re.sub(r"([.!?])(?=\S)", r"\1 ", value)
        if value:
            value = value[0].upper() + value[1:]
            if mode in {CleanupMode.STANDARD, CleanupMode.BUSINESS} and value[-1] not in ".!?":
                value += "."
        return _restore_words(value, vocabulary)


class LlamaCppCleaner:
    def __init__(self, model_path: Path, threads: int, gpu_layers: int = 0) -> None:
        from llama_cpp import Llama  # type: ignore[import-not-found]

        self._llm = Llama(
            model_path=str(model_path),
            n_ctx=2048,
            n_threads=max(1, threads),
            n_gpu_layers=gpu_layers,
            verbose=False,
        )

    def clean(self, text: str, mode: CleanupMode, vocabulary: list[str]) -> str:
        vocab = ", ".join(vocabulary) or "none"
        result = self._llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a private dictation editor. Return only edited text. "
                        "Never add facts. "
                        f"{PROMPTS[mode]} Preserve these exact terms when present: {vocab}."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=512,
            temperature=0.1,
        )
        output = str(result["choices"][0]["message"]["content"]).strip()
        return _restore_words(output or text, vocabulary)


class AutoCleaner:
    def __init__(self, model_path: str, threads: int, use_gpu: bool) -> None:
        self.backend = "rules"
        self._cleaner: RuleBasedCleaner | LlamaCppCleaner = RuleBasedCleaner()
        path = Path(model_path).expanduser() if model_path else None
        if path and path.is_file():
            try:
                self._cleaner = LlamaCppCleaner(path, threads, -1 if use_gpu else 0)
                self.backend = "llama.cpp"
            except (ImportError, RuntimeError, ValueError, OSError):
                pass

    def clean(self, text: str, mode: CleanupMode, vocabulary: list[str]) -> str:
        return self._cleaner.clean(text, mode, vocabulary)
