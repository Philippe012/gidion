"""
Proves ModelUnavailableError / VoiceUnavailableError behave correctly
BEFORE you've downloaded any model — run this any time to confirm the
failure path is clean, not a crash.
"""

from app.core.llm.model_wrapper import LocalModel, ModelUnavailableError
from app.core.voice.stt import SpeechToText, VoiceUnavailableError as STTUnavailableError
from app.core.voice.tts import TextToSpeech, VoiceUnavailableError as TTSUnavailableError


def check(label, fn, expected_exception):
    try:
        fn()
        print(f"[FAIL] {label}: expected {expected_exception.__name__}, but no error was raised")
    except expected_exception as e:
        print(f"[OK]   {label}: raised {expected_exception.__name__} as expected")
        print(f"       message: {e}")
    except Exception as e:
        print(f"[FAIL] {label}: raised the WRONG exception type: {type(e).__name__}: {e}")


if __name__ == "__main__":
    check(
        "LLM generate() with no model file present",
        lambda: LocalModel().generate("test prompt"),
        ModelUnavailableError,
    )
    print()
    check(
        "Speech-to-text with no whisper model configured",
        lambda: SpeechToText().transcribe("nonexistent.wav"),
        STTUnavailableError,
    )
    print()
    check(
        "Text-to-speech with no Piper voice file present",
        lambda: TextToSpeech().synthesize_to_file("hello", "out.wav"),
        TTSUnavailableError,
    )