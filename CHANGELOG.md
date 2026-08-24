# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and semantic versioning.

## [0.1.8] - 2026-08-23

### Changed

- Start recording silently without emitting a Windows notification.
- Make transcription-complete Windows notifications optional and disabled by default.

## [0.1.7] - 2026-08-23

### Added

- Add a local SQLite transcript archive containing timestamps, raw/cleaned text, mode, language,
  and duration without retaining audio.
- Add a History tab with live full-text search, refresh, raw-text comparison, and confirmed clear.
- Add a privacy setting, enabled by default, to disable saving future transcript history.

## [0.1.6] - 2026-08-23

### Fixed

- Treat dictated questions as quoted text to edit, never prompts to answer.
- Add explicit non-conversational examples and perspective/intent preservation constraints to the
  cleanup system prompt.
- Reject LLM output that introduces substantial new vocabulary, drops questions, or expands the
  transcript suspiciously; fall back to deterministic cleanup instead.
- Add the reported Kentucky sentence to unit tests and real llama.cpp release inference.

## [0.1.5] - 2026-08-23

### Fixed

- Make installed untyped audio/model libraries behave consistently in the Python 3.11/3.12 mypy
  matrix.
- Run lint, formatting, and strict typing inside the release build itself so a tag cannot publish
  when the separate CI quality matrix would fail.

## [0.1.4] - 2026-08-23

### Fixed

- Replace the hanging parallel Hugging Face snapshot path with sequential, resumable downloads.
- Enforce connection and read timeouts, retry interrupted transfers three times, preserve partial
  bytes for resume, verify payload sizes, and verify LFS SHA-256 digests.
- Report aggregate byte/megabyte progress across every required model file in a readable full-height
  progress bar.
- Gate CI and releases on downloading real Whisper and GGUF models, loading them with CTranslate2
  and llama.cpp, and running actual inference through both engines on Windows.

## [0.1.3] - 2026-08-23

### Fixed

- Show determinate download progress and indeterminate model-loading progress during setup.
- Store Whisper models in app-owned storage and automatically force a clean download when model
  loading detects an incomplete or corrupt cache.
- Keep Retry useful after a failed first-run model download.

## [0.1.2] - 2026-08-23

### Fixed

- Lock recording until the speech model is ready instead of showing a misleading modal during
  first-run setup.
- Enable dictation with basic local cleanup as soon as Whisper loads while enhanced cleanup
  continues preparing in the background.
- Show persistent model setup failures with an in-app retry action.
- Verify the safe initial model-loading controls in the packaged startup check.
- Add configurable automatic update checks, verified background downloads, and an install prompt.

## [0.1.1] - 2026-08-23

### Fixed

- Launch the frozen application through a package-aware entry point so relative imports resolve.
- Require a positive marker and clean exit from the packaged executable smoke test, preventing
  an error dialog from being mistaken for a successful startup.

## [0.1.0] - 2026-08-23

### Added

- Windows desktop app with global push-to-talk, tray mode, clipboard, and automatic paste.
- Hardware-aware local faster-whisper transcription.
- Automatic small local Qwen/llama.cpp cleanup with four style modes and rules fallback.
- Custom vocabulary, persistent settings, and audio-file CLI.
- Tests, lint/type checks, Windows packaging, installer, SBOM, checksums, and release automation.
