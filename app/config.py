"""
Central configuration for Gidion.

Anything that changes per-deployment (malaria risk region, model choice,
storage location) lives here — never hardcoded inside core/rules or
core/llm. This is what makes the SDLC's "reuse the generic rules engine
for a new protocol/region" goal (Phase 8) actually practical.
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
# BASE_DIR must resolve correctly BOTH when running from source (python
# -m app.main) AND when frozen into a PyInstaller .exe. __file__ points
# into a temp extraction folder once frozen — sys.executable's own
# directory is the actual install location and is what we want instead.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent  # project root

MODELS_DIR = BASE_DIR / "models"
DOCS_DIR = BASE_DIR / "docs"

# User-writable data (override logs) must NOT live next to the bundled
# resources above — once installed under Program Files, a normal user
# has no write permission there. %LOCALAPPDATA% (Windows) or the home
# directory (elsewhere) is always writable by the current user.
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Gidion"
STORAGE_DB_PATH = USER_DATA_DIR / "storage_data" / "gidion_local.sqlite3"

# ---------------------------------------------------------------------
# Language model
# ---------------------------------------------------------------------
# Start with a 1B-class model per SDLC Phase 2.1 — test before assuming
# a 3B model is needed. Filename must match whatever is placed in
# MODELS_DIR (bundled or downloaded on first launch, per Phase 5.2).
LLM_MODEL_FILENAME = os.environ.get("GIDION_LLM_MODEL", "phi-3-mini-4k-instruct-q4.gguf")
LLM_MODEL_PATH = MODELS_DIR / LLM_MODEL_FILENAME
LLM_CONTEXT_SIZE = 4096
LLM_MAX_NEW_TOKENS = 220
LLM_TEMPERATURE = 0.2  # low — this model phrases decisions, it doesn't make them

# ---------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------
VOICE_ENABLED = os.environ.get("GIDION_VOICE_ENABLED", "0") == "1"
WHISPER_MODEL_SIZE = "base"  # whisper.cpp model size, offline
PIPER_VOICE_PATH = MODELS_DIR / "piper" / "en_US-default.onnx"

# TTS backend selection (SDLC Phase 3.4 — opt-in voice cloning add-on):
#   "piper"      - fast, small, fixed generic voice
#   "xtts_clone" - slower, larger, clones a voice from a short reference
#                  recording you provide yourself. Default, since this
#                  is now Gidion's normal voice for this deployment —
#                  override with GIDION_TTS_ENGINE=piper if you ever
#                  need the faster fallback (e.g. slow hardware).
TTS_ENGINE = os.environ.get("GIDION_TTS_ENGINE", "piper")
XTTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
XTTS_LANGUAGE = os.environ.get("GIDION_XTTS_LANGUAGE", "en")
VOICE_CLONE_DIR = MODELS_DIR / "voice_clone"
VOICE_CLONE_REFERENCE_PATH = VOICE_CLONE_DIR / "reference.wav"

# ---------------------------------------------------------------------
# Deployment / regional protocol settings
# ---------------------------------------------------------------------
# Per docs/imci_child_protocol.md §4.5 — this is Afghanistan's malaria
# risk map from the source booklet. ANY new deployment region must
# replace this with current national malaria-programme data before
# relying on it beyond synthetic testing.
MALARIA_HIGH_RISK_PROVINCES = {
    "kunar", "nangahar", "laghman", "kunduz", "baghlan", "takhar",
    "nimroz", "helmand", "kandahar", "zabul", "farah",
}
DEFAULT_MALARIA_RISK_AREA = "low"  # "high" or "low"

# ---------------------------------------------------------------------
# Storage / privacy posture (SDLC §6.4)
# ---------------------------------------------------------------------
OVERRIDE_LOGGING_ENABLED_DEFAULT = False  # opt-in, never on by default
TELEMETRY_ENABLED = False  # always False — no analytics, no telemetry

# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------
DISCLAIMER_TEXT = (
    "Suggestion only — clinical decision remains with you."
)
UI_HOST = "127.0.0.1"
UI_PORT = 5000
INTRO_TEXT = (
    "Hi, I am Gidion. I am an offline clinical triage assistant. I ask "
    "a few structured questions about a visit, apply a fixed set of "
    "clinical rules, and give you a classification and a recommended "
    "next step. I do not diagnose, I do not prescribe, and I never "
    "talk to a patient directly. The decision is always yours. "
    "Let us get started."
)


def province_to_malaria_risk(province: str | None) -> str:
    """Look up malaria risk area for a given province name.
    Falls back to DEFAULT_MALARIA_RISK_AREA if unknown/unset — never
    guesses "high" by default, since that changes the clinical branch
    taken."""
    if not province:
        return DEFAULT_MALARIA_RISK_AREA
    return "high" if province.strip().lower() in MALARIA_HIGH_RISK_PROVINCES else "low"