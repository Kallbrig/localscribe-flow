from __future__ import annotations

import queue
import wave
from pathlib import Path
from typing import Any

import numpy as np


class AudioRecorder:
    def __init__(self, sample_rate: int = 16_000) -> None:
        self.sample_rate = sample_rate
        self._queue: queue.Queue[np.ndarray[Any, Any]] = queue.Queue()
        self._stream: Any = None

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        import sounddevice as sd

        if self.recording:
            return
        while not self._queue.empty():
            self._queue.get_nowait()

        def callback(indata: np.ndarray[Any, Any], _frames: int, _time: Any, status: Any) -> None:
            if status:
                return
            self._queue.put(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            callback=callback,
        )
        self._stream.start()

    def stop(self, destination: Path) -> Path:
        if not self.recording:
            raise RuntimeError("Recorder is not active")
        stream, self._stream = self._stream, None
        stream.stop()
        stream.close()
        chunks: list[np.ndarray[Any, Any]] = []
        while not self._queue.empty():
            chunks.append(self._queue.get_nowait())
        if not chunks:
            raise RuntimeError("No audio was captured")
        destination.parent.mkdir(parents=True, exist_ok=True)
        audio = np.concatenate(chunks).astype(np.int16)
        with wave.open(str(destination), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(audio.tobytes())
        return destination
