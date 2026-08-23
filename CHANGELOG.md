# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and semantic versioning.

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
