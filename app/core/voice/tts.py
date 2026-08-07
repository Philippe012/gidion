
import os
import tempfile
import wave
from pathlib import Path

from app import config


class VoiceUnavailableError(RuntimeError):
    """Raised when the selected TTS backend, its model, or the voice
    reference recording aren't available."""


class TextToSpeech:
    def __init__(self):
        self._piper_voice = None
        self._xtts_model = None

    def _ensure_loaded(self):
        if config.TTS_ENGINE == "xtts_clone":
            self._ensure_xtts_loaded()
        else:
            self._ensure_piper_loaded()

    # ------------------------------------------------------------
    # Piper backend
    # ------------------------------------------------------------
    def _ensure_piper_loaded(self):
        if self._piper_voice is not None:
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
            self._piper_voice = PiperVoice.load(str(config.PIPER_VOICE_PATH))
        except Exception as exc:
            raise VoiceUnavailableError(
                f"Piper failed to load the voice model at "
                f"{config.PIPER_VOICE_PATH}: {exc}"
            ) from exc

    def _synthesize_piper_to_file(self, text: str, output_wav_path: str) -> str:
        # Must use Python's wave module, not a plain open(path, 'wb') —
        # Piper's synthesize_wav() needs a real wave.Wave_write object
        # to set the sample rate/width/channel header correctly.
        out_path = Path(output_wav_path)
        with wave.open(str(out_path), "wb") as wav_file:
            self._piper_voice.synthesize_wav(text, wav_file)
        return str(out_path)

    # ------------------------------------------------------------
    # XTTS voice-cloning backend
    # ------------------------------------------------------------
    def _ensure_xtts_loaded(self):
        if self._xtts_model is not None:
            return
        if not config.VOICE_CLONE_REFERENCE_PATH.exists():
            raise VoiceUnavailableError(
                f"No voice reference recording found at "
                f"{config.VOICE_CLONE_REFERENCE_PATH}. Record ~20-30 "
                f"seconds of clear speech (see README) and place it there "
                f"as reference.wav before using xtts_clone."
            )
        try:
            from TTS.api import TTS as CoquiTTS
        except ImportError as exc:
            if "torch" in str(exc).lower():
                raise VoiceUnavailableError(
                    "coqui-tts is installed, but PyTorch (its actual "
                    "backend) is not. Run: pip install torch torchaudio "
                    "--index-url https://download.pytorch.org/whl/cpu "
                    "(use the CPU index unless you specifically have a "
                    "CUDA-compatible GPU set up)."
                ) from exc
            raise VoiceUnavailableError(
                "coqui-tts is not installed. Run: pip install coqui-tts "
                "(this is a large, optional dependency — see README)."
            ) from exc
        try:
            self._xtts_model = CoquiTTS(config.XTTS_MODEL_NAME)
        except Exception as exc:
            raise VoiceUnavailableError(
                f"Failed to load the XTTS model '{config.XTTS_MODEL_NAME}': "
                f"{exc}"
            ) from exc

    def _synthesize_xtts_to_file(self, text: str, output_wav_path: str) -> str:
        self._xtts_model.tts_to_file(
            text=text,
            speaker_wav=str(config.VOICE_CLONE_REFERENCE_PATH),
            language=config.XTTS_LANGUAGE,
            file_path=str(output_wav_path),
        )
        return str(output_wav_path)

    # ------------------------------------------------------------
    # Public API — unchanged regardless of backend
    # ------------------------------------------------------------
    def synthesize_to_file(self, text: str, output_wav_path: str) -> str:
        """Synthesizes `text` to a local .wav file and returns its path.
        Runs entirely on-device, using whichever backend
        config.TTS_ENGINE selects."""
        self._ensure_loaded()
        if config.TTS_ENGINE == "xtts_clone":
            return self._synthesize_xtts_to_file(text, output_wav_path)
        return self._synthesize_piper_to_file(text, output_wav_path)

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