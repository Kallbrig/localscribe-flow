# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and semantic versioning.

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
