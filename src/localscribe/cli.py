from __future__ import annotations

import argparse
from pathlib import Path

from .cleanup import AutoCleaner
from .config import ConfigStore
from .domain import CleanupMode
from .hardware import detect_hardware
from .pipeline import DictationPipeline
from .transcription import WhisperTranscriber


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="localscribe", description="Local, private transcription")
    parser.add_argument("audio", type=Path, help="Audio file to transcribe")
    parser.add_argument("--mode", choices=[m.value for m in CleanupMode], default="standard")
    parser.add_argument("--raw", action="store_true", help="Skip cleanup")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = ConfigStore().load()
    hardware = detect_hardware()
    transcriber = WhisperTranscriber(config.whisper_model, hardware, config.language)
    cleaner = AutoCleaner(
        config.llm_model_path, hardware.logical_cores - 1, hardware.device == "cuda"
    )
    pipeline = DictationPipeline(transcriber, cleaner)
    result = pipeline.process(args.audio, CleanupMode(args.mode), config.custom_words)
    print(result.raw if args.raw else result.cleaned)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
