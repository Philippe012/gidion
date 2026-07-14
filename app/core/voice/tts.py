"""
Offline text-to-speech via Piper (SDLC Phase 3.2). Default voice only
for MVP — XTTS voice cloning is explicitly deferred (Phase 3.4,
optional, given its size/speed tradeoff).
"""

from email.mime import text
import os
import tempfile
from pathlib import Path
import wave

from app import config


class VoiceUnavailableError(RuntimeError):
    """Raised when Piper or its voice model aren't available."""


class TextToSpeech:
    def __init__(self):
        self._voice = None

    def _ensure_loaded(self):
        if self._voice is not None:
            return
        if not config.PIPER_VOICE_PATH.exists():
            raise VoiceUnavailableError(
                f"Piper voice model not found at {config.PIPER_VOICE_PATH}. "
                f"Download a Piper voice (see README) and place it there."
            )
        try:
            from piper import PiperVoice
        except ImportError as exc:
            raise VoiceUnavailableError(
                "piper-tts is not installed. Run: pip install piper-tts"
            ) from exc
        try:
            self._voice = PiperVoice.load(str(config.PIPER_VOICE_PATH))
        except Exception as exc:
            raise VoiceUnavailableError(
                f"Piper failed to load the voice model at "
                f"{config.PIPER_VOICE_PATH}: {exc}"
            ) from exc

    def synthesize_to_file(self, text: str, output_wav_path: str) -> str:
        self._ensure_loaded()
        out_path = Path(output_wav_path)
        with wave.open(str(out_path), "wb") as wav_file:
            self._voice.synthesize_wav(text, wav_file)
        return str(out_path)

    def synthesize_to_bytes(self, text: str) -> bytes:
        """Synthesizes `text` and returns raw WAV bytes, for streaming
        straight back over HTTP without leaving a permanent file
        behind."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            out_path = f.name
        try:
            self.synthesize_to_file(text, out_path)
            with open(out_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)