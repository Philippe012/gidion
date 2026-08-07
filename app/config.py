import os
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

MODELS_DIR = BASE_DIR / "models"
DOCS_DIR = BASE_DIR / "docs"

USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Gidion"
STORAGE_DB_PATH = USER_DATA_DIR / "storage_data" / "gidion_local.sqlite3"

# === NEW: Session database for dynamic conversations ===
SESSION_DB_PATH = USER_DATA_DIR / "storage_data" / "gidion_sessions.sqlite3"
DEFAULT_PROTOCOL = "imci_child"
SESSION_TIMEOUT_MINUTES = 30


LLM_MODEL_FILENAME = os.environ.get("GIDION_LLM_MODEL", "phi-3-mini-4k-instruct-q4.gguf")
LLM_MODEL_PATH = MODELS_DIR / LLM_MODEL_FILENAME
LLM_CONTEXT_SIZE = 4096
LLM_MAX_NEW_TOKENS = 220
LLM_TEMPERATURE = 0.2

VOICE_ENABLED = os.environ.get("GIDION_VOICE_ENABLED", "0") == "1"
WHISPER_MODEL_SIZE = "base"
PIPER_VOICE_PATH = MODELS_DIR / "piper" / "en_US-default.onnx"

TTS_ENGINE = os.environ.get("GIDION_TTS_ENGINE", "xtts_clone")
XTTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
XTTS_LANGUAGE = os.environ.get("GIDION_XTTS_LANGUAGE", "en")
VOICE_CLONE_DIR = MODELS_DIR / "voice_clone"
VOICE_CLONE_REFERENCE_PATH = VOICE_CLONE_DIR / "reference.wav"

MALARIA_HIGH_RISK_PROVINCES = {
    "kunar", "nangahar", "laghman", "kunduz", "baghlan", "takhar",
    "nimroz", "helmand", "kandahar", "zabul", "farah",
}
DEFAULT_MALARIA_RISK_AREA = "low"

OVERRIDE_LOGGING_ENABLED_DEFAULT = False
TELEMETRY_ENABLED = False

DISCLAIMER_TEXT = (
    "Suggestion only — clinical decision remains with you."
)
UI_HOST = "127.0.0.1"
UI_PORT = 5000
INTRO_TEXT = (
    "Hi, I am Gidion. I am an offline clinical triage assistant. I help "
    "health workers assess children through natural conversation. I apply "
    "clinical rules for safety, but I do not diagnose or prescribe. "
    "The decision is always yours."
)


def province_to_malaria_risk(province: str | None) -> str:
    if not province:
        return DEFAULT_MALARIA_RISK_AREA
    return "high" if province.strip().lower() in MALARIA_HIGH_RISK_PROVINCES else "low"