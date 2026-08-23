# Architecture

LocalScribe Flow separates its domain pipeline from platform and engine adapters:

```text
Global hotkey -> AudioRecorder -> WhisperTranscriber -> AutoCleaner -> clipboard/paste
                                      |                    |
                               custom vocabulary     cleanup mode
```

`DictationPipeline` depends only on the `Transcriber` and `Cleaner` protocols. The Windows
desktop currently uses Qt, PortAudio through `sounddevice`, and `pynput`. The same pipeline can
be hosted by a Swift menu-bar adapter on macOS or a Kotlin foreground service on Android.

## Data flow

1. PCM mono audio is captured at 16 kHz into memory.
2. A temporary WAV is written to the local app-data directory.
3. CTranslate2 executes Whisper locally. Custom terms are included in its initial prompt.
4. `llama.cpp` edits the transcript with the selected mode and exact-term list.
5. The cleaned text is copied and pasted. The WAV is deleted unless recording retention is
   explicitly enabled.

There are no outbound inference calls. Network access occurs only when Hugging Face downloads
a missing model during setup.

## Extension roadmap

- **macOS:** reuse the Python domain/engine packages; replace hotkey, accessibility paste, and
  packaging adapters. Metal acceleration can be enabled through llama.cpp and CTranslate2.
- **Android:** move the protocols into a local service API; use whisper.cpp/ONNX and llama.cpp
  JNI with an IME or accessibility-service front end. Settings remain schema-compatible.
- **Engines:** additional speech and cleanup engines implement the two small protocols in
  `domain.py`, which makes them independently testable.

