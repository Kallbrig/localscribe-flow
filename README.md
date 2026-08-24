# LocalScribe Flow

LocalScribe Flow is a private, local-first voice dictation app for Windows. Hold a global
hotkey, speak, release by pressing it again, and polished text is copied and pasted into the
active application. Audio transcription and language cleanup run on your computer.

> Beta (`v0.1.2`): Windows 10/11 x64 is the supported release target. The core and desktop
> integration boundaries are portable; macOS and Android adapters are planned.

## What it does

- Local speech-to-text with `faster-whisper` and Silero-style VAD filtering
- Automatic CUDA/CPU detection and efficient quantization selection
- A small local Qwen 2.5 GGUF model through `llama.cpp` for cleanup
- Informal, casual, standard, and business cleanup modes
- Custom names and technical terms supplied to Whisper and preserved during cleanup
- System tray operation, configurable global hotkey, auto-copy, and auto-paste
- Deterministic offline cleanup fallback if the local LLM cannot start
- A scriptable CLI for existing audio files
- No account, cloud API, telemetry, or server

## Install on Windows

Download the installer or portable ZIP from the latest GitHub release. The first launch
downloads two model files: Whisper `small.en` and Qwen 2.5 0.5B/1.5B Q4 (selected according
to RAM). After that, dictation works without a network connection. Model files live under
`%LOCALAPPDATA%\LocalScribe Flow` and never receive your recordings or text.

1. Launch **LocalScribe Flow** and allow microphone access if Windows asks.
2. Wait for the status to say **Ready**. First setup can take several minutes.
3. Focus any text field and press `Ctrl+Shift+Space`.
4. Speak, then press the same hotkey. The cleaned text is pasted into the focused field.
5. Choose a cleanup mode and add custom words under **Settings**.

The application copies text before pasting, so it remains available if the target application
rejects synthetic keyboard input.

## Cleanup modes

| Mode | Behavior |
|---|---|
| Informal | Keeps slang, fillers, and the speaker's personal voice; removes stumbles |
| Casual | Friendly, concise, conversational grammar |
| Standard | Correct grammar and punctuation without changing tone |
| Business | Polished, concise, professional phrasing |

Local LLM cleanup is constrained to editing: the prompt explicitly forbids adding facts.
Always review consequential medical, legal, financial, or business text before sending it.

## Hardware selection

At startup the app queries CTranslate2. NVIDIA CUDA with FP16 is preferred when supported;
the required CUDA 12 runtime libraries are load-tested before GPU mode is enabled. If they are
missing, the app safely falls back to CPU INT8 or INT8/FP32 based on available memory instead of
failing during transcription. Machines below 8 GB RAM
use a 0.5B cleanup model and `base.en` can be selected manually. The settings screen displays
the active backend and rationale.

## Developer setup

Python 3.11 or 3.12 and Git are required.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[app,dev]"
python -m pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
pytest
localscribe-flow
```

Transcribe a file from the command line:

```powershell
localscribe recording.wav --mode business
```

Build and verify the portable Windows release:

```powershell
./scripts/build.ps1
```

## Release lifecycle

Every push and pull request runs lint, type checks, and tests on Python 3.11/3.12. A tag named
`v*` runs the Windows packaging job, builds the portable ZIP and Inno Setup installer,
generates SHA-256 checksums and a CycloneDX software bill of materials, then publishes an
immutable GitHub Release. Dependabot submits monthly dependency and Actions updates.

To release:

1. Update `src/localscribe/__init__.py`, `pyproject.toml`, `packaging/installer.iss`, and
   `CHANGELOG.md` to the same version.
2. Run `./scripts/build.ps1` and test the portable build on a clean Windows VM.
3. Commit, tag `vX.Y.Z`, and push the tag. GitHub Actions performs the remaining steps.

See [architecture](docs/ARCHITECTURE.md), [privacy and security](SECURITY.md), and
[contributing](CONTRIBUTING.md) for more.

## License

MIT License. Downloaded models retain their respective upstream licenses.
