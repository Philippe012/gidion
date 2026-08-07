
import os
import subprocess
import tempfile

from app import config


class VoiceUnavailableError(RuntimeError):
    """Raised when whisper.cpp bindings, the model, or ffmpeg aren't
    available. Always has a clear, actionable message — never lets the
    caller see a raw traceback."""


def _convert_to_wav(audio_bytes: bytes, source_suffix: str) -> str:
    """Browsers record audio as webm/opus (or similar) via MediaRecorder;
    whisper.cpp needs 16kHz mono WAV. ffmpeg does that conversion.
    Returns the path to a temp WAV file — caller is responsible for
    deleting it."""
    with tempfile.NamedTemporaryFile(suffix=source_suffix, delete=False) as f:
        f.write(audio_bytes)
        in_path = f.name

    out_path = in_path + ".wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", in_path, "-ar", "16000", "-ac", "1", out_path],
            check=True, capture_output=True,
        )
    except FileNotFoundError as exc:
        raise VoiceUnavailableError(
            "ffmpeg is not installed or not on PATH. Voice input needs it "
            "to convert recorded audio to the format whisper.cpp expects. "
            "Install it from https://ffmpeg.org/download.html (or "
            "'winget install ffmpeg' on Windows) and make sure it's on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise VoiceUnavailableError(
            f"ffmpeg failed to convert the recorded audio: "
            f"{exc.stderr.decode(errors='ignore')[:300]}"
        ) from exc
    finally:
        os.unlink(in_path)
    return out_path


class SpeechToText:
    def __init__(self):
        self._model = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            from pywhispercpp.model import Model
        except ImportError as exc:
            raise VoiceUnavailableError(
                "pywhispercpp is not installed. Run: pip install pywhispercpp"
            ) from exc

        expected_file_hint = (
            f"ggml-{config.WHISPER_MODEL_SIZE}.bin (or similar) in "
            f"{config.MODELS_DIR}"
        )
        try:
            # models_dir keeps this local-first rather than letting
            # pywhispercpp reach for the network if it can't find one.
            self._model = Model(config.WHISPER_MODEL_SIZE, models_dir=str(config.MODELS_DIR))
        except Exception as exc:
            raise VoiceUnavailableError(
                f"Could not load whisper model '{config.WHISPER_MODEL_SIZE}'. "
                f"Expected a local model file such as {expected_file_hint}. "
                f"Download one from the whisper.cpp model repo and place it "
                f"there. Original error: {exc}"
            ) from exc

    def transcribe(self, audio_path: str) -> str:
        """Transcribes a local WAV file and returns plain text. Never
        sends audio anywhere — whisper.cpp runs entirely on-device."""
        self._ensure_loaded()
        try:
            segments = self._model.transcribe(audio_path)
        except Exception as exc:
            # Model loaded fine, but something about THIS audio failed
            # (missing file, corrupted data, etc.) — still a voice
            # problem the caller should handle the same clean way,
            # not a raw traceback.
            raise VoiceUnavailableError(
                f"Could not transcribe audio at '{audio_path}': {exc}"
            ) from exc
        return " ".join(segment.text.strip() for segment in segments).strip()

    def transcribe_bytes(self, audio_bytes: bytes, source_suffix: str = ".webm") -> str:
        """Transcribes raw audio bytes as uploaded by the browser (e.g.
        webm/opus from MediaRecorder). Converts to WAV via ffmpeg first,
        cleans up temp files even on failure."""
        wav_path = _convert_to_wav(audio_bytes, source_suffix)
        try:
            return self.transcribe(wav_path)
        finally:
            if os.path.exists(wav_path):
                os.unlink(wav_path)