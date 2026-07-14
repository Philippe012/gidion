"""
Central configuration for Gidion.

Anything that changes per-deployment (malaria risk region, model choice,
storage location) lives here — never hardcoded inside core/rules or
core/llm. This is what makes the SDLC's "reuse the generic rules engine
for a new protocol/region" goal (Phase 8) actually practical.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent 
MODELS_DIR = BASE_DIR / "models"
DOCS_DIR = BASE_DIR / "docs"
STORAGE_DB_PATH = BASE_DIR / "storage_data" / "gidion_local.sqlite3"

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
WHISPER_MODEL_SIZE = "base" 
PIPER_VOICE_PATH = MODELS_DIR / "piper" / "en_US-default.onnx"

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


def province_to_malaria_risk(province: str | None) -> str:
    """Look up malaria risk area for a given province name.
    Falls back to DEFAULT_MALARIA_RISK_AREA if unknown/unset — never
    guesses "high" by default, since that changes the clinical branch
    taken."""
    if not province:
        return DEFAULT_MALARIA_RISK_AREA
    return "high" if province.strip().lower() in MALARIA_HIGH_RISK_PROVINCES else "low"