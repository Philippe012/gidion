"""
Diagnoses a 0-byte Piper output by checking each stage separately:
does phonemization produce anything, does synthesize() yield any audio
chunks, and only then does synthesize_wav get blamed.
"""

from app.core.voice.tts import TextToSpeech
from app import config

tts = TextToSpeech()
tts._ensure_loaded()
voice = tts._voice

text = "This is a test of the Gidion voice output."

print(f"Voice model path: {config.PIPER_VOICE_PATH}")
print(f"Voice model exists: {config.PIPER_VOICE_PATH.exists()}")
print()

print("Step 1: phonemizing text...")
try:
    phonemes = voice.phonemize(text)
    print(f"  Result: {phonemes}")
    print(f"  Empty?: {not phonemes or all(not p for p in phonemes)}")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")

print()
print("Step 2: generating audio chunks...")
try:
    chunk_count = 0
    total_bytes = 0
    for chunk in voice.synthesize(text):
        chunk_count += 1
        total_bytes += len(chunk.audio_int16_bytes)
    print(f"  Chunks produced: {chunk_count}")
    print(f"  Total audio bytes: {total_bytes}")
    if chunk_count == 0:
        print("  ^ THIS is the problem — no audio was generated at all.")
        print("    Likely cause: espeak-ng data missing/misconfigured, so")
        print("    phonemization silently returned nothing.")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")

print()
print("Step 3: checking for espeak-ng data...")
try:
    import espeakng_loader
    print(f"  espeakng_loader found. Data path: {espeakng_loader.get_data_path()}")
except ImportError:
    print("  espeakng_loader is not installed. This is likely the cause —")
    print("  run: pip install espeakng-loader")