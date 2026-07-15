"""
Checks the LLM/voice error-handling paths against whatever is ACTUALLY
set up on this machine right now, rather than assuming a fresh install
with nothing configured. Run any time — safe whether models are
present or not.
"""

from app import config
from app.core.llm.model_wrapper import LocalModel, ModelUnavailableError
from app.core.voice.stt import SpeechToText, VoiceUnavailableError as STTUnavailableError
from app.core.voice.tts import TextToSpeech, VoiceUnavailableError as TTSUnavailableError


def check_llm():
    if config.LLM_MODEL_PATH.exists():
        print(f"[SETUP] LLM model found at {config.LLM_MODEL_PATH}")
        try:
            LocalModel()._ensure_loaded()
            print("[OK]    LLM loads successfully.")
        except ModelUnavailableError as e:
            print(f"[FAIL]  Model file exists but failed to load: {e}")
    else:
        print(f"[SETUP] No LLM model at {config.LLM_MODEL_PATH} — testing the missing-model error path.")
        try:
            LocalModel().generate("test")
            print("[FAIL]  Expected ModelUnavailableError, none was raised.")
        except ModelUnavailableError as e:
            print(f"[OK]    Clean error as expected: {e}")


def check_stt():
    whisper_file_hint = config.MODELS_DIR / f"ggml-{config.WHISPER_MODEL_SIZE}.bin"
    if whisper_file_hint.exists():
        print(f"[SETUP] Whisper model found at {whisper_file_hint}")
        stt = SpeechToText()
        try:
            stt._ensure_loaded()
            print("[OK]    Whisper model loads successfully.")
        except STTUnavailableError as e:
            print(f"[FAIL]  Model file exists but failed to load: {e}")
            return
        # Model loads fine — now confirm a BAD audio path still fails
        # cleanly instead of leaking a raw exception.
        try:
            stt.transcribe("this_file_does_not_exist.wav")
            print("[FAIL]  Expected an error for a nonexistent audio file, none was raised.")
        except STTUnavailableError as e:
            print(f"[OK]    Bad audio path fails cleanly: {e}")
        except Exception as e:
            print(f"[FAIL]  Wrong exception type leaked through: {type(e).__name__}: {e}")
    else:
        print(f"[SETUP] No Whisper model at {whisper_file_hint} — testing the missing-model error path.")
        try:
            SpeechToText().transcribe("nonexistent.wav")
            print("[FAIL]  Expected STTUnavailableError, none was raised.")
        except STTUnavailableError as e:
            print(f"[OK]    Clean error as expected: {e}")


def check_tts():
    engine = config.TTS_ENGINE
    print(f"[SETUP] Active TTS_ENGINE = '{engine}'")
    if engine == "xtts_clone":
        ready = config.VOICE_CLONE_REFERENCE_PATH.exists()
        print(f"[SETUP] Voice reference {'found' if ready else 'MISSING'} at {config.VOICE_CLONE_REFERENCE_PATH}")
    else:
        ready = config.PIPER_VOICE_PATH.exists()
        print(f"[SETUP] Piper voice {'found' if ready else 'MISSING'} at {config.PIPER_VOICE_PATH}")

    tts = TextToSpeech()
    try:
        tts._ensure_loaded()
        print("[OK]    TTS backend loads successfully.")
    except TTSUnavailableError as e:
        if ready:
            print(f"[FAIL]  Files present but backend failed to load: {e}")
        else:
            print(f"[OK]    Clean error as expected (files missing): {e}")


if __name__ == "__main__":
    print("=== LLM ===")
    check_llm()
    print("\n=== Speech-to-text ===")
    check_stt()
    print("\n=== Text-to-speech ===")
    check_tts()