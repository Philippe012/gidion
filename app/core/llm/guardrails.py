"""
Output guardrails for the local LLM (SDLC Phase 2.4).

Heuristic, keyword-based scanning — not a substitute for the
architectural guarantee that the rules engine (not the model) makes
every clinical decision. This exists as a second layer: if the model
drifts and adds something it shouldn't (a drug name, a new diagnosis,
false reassurance), catch it before it reaches the UI or voice output.

This is deliberately conservative: false positives (flagging something
harmless) are cheap to review; false negatives (a medication or
reassurance slipping through) are not.
"""

import re

# Drug/medication names appearing anywhere in the SDLC's source
# protocol data — these must never appear in Gidion's spoken output,
# regardless of which classification triggered them.
_BANNED_DRUG_TERMS = [
    "ampicillin", "gentamicin", "gentamycin", "cotrimoxazole", "amoxicillin",
    "amoxycillin", "erythromycin", "ciprofloxacin", "metronidazole",
    "chloroquine", "sulfadoxine", "pyrimethamine", "quinine", "paracetamol",
    "vitamin a capsule", "mebendazole", "salbutamol", "diazepam",
    "gentian violet", "tetracycline", "iron/folate", "folic acid",
    "zinc tablet", "ors packet",
]

# Phrases that constitute reassurance / risk estimation — banned
# categorically for cancer-adjacent / high-severity screen-and-route
# content (SDLC §3.3), and generally discouraged everywhere else since
# Gidion should state classifications, not editorialize about outcomes.
_BANNED_REASSURANCE_PATTERNS = [
    r"\bprobably (nothing|fine|benign|okay)\b",
    r"\bdon'?t worry\b",
    r"\bunlikely to be (serious|cancer|dangerous)\b",
    r"\bno need to (worry|see a doctor|refer)\b",
    r"\bmild (case|form) of cancer\b",
    r"\bit'?s (just|only) a\b",
]

# Diagnostic-overreach phrasing — the model asserting a diagnosis in its
# own voice rather than reporting the rules engine's classification.
_BANNED_DIAGNOSIS_PATTERNS = [
    r"\bi diagnose\b",
    r"\bthis (child|patient) has cancer\b",
    r"\bmy diagnosis is\b",
    r"\byou should prescribe\b",
]


def _find_matches(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [t for t in terms if t in lowered]


def _find_pattern_matches(text: str, patterns: list[str]) -> list[str]:
    lowered = text.lower()
    return [p for p in patterns if re.search(p, lowered)]


def scan_output(text: str) -> tuple[bool, list[str]]:
    """Returns (is_safe, violations). is_safe=False means the caller
    should NOT display/speak this text — regenerate, fall back to the
    raw classification/action strings verbatim, or surface an error."""
    violations = []

    drug_hits = _find_matches(text, _BANNED_DRUG_TERMS)
    if drug_hits:
        violations.append(f"Contains medication/drug terms: {', '.join(drug_hits)}")

    reassurance_hits = _find_pattern_matches(text, _BANNED_REASSURANCE_PATTERNS)
    if reassurance_hits:
        violations.append("Contains reassurance/risk-estimation language")

    diagnosis_hits = _find_pattern_matches(text, _BANNED_DIAGNOSIS_PATTERNS)
    if diagnosis_hits:
        violations.append("Contains model-asserted diagnosis language")

    return (len(violations) == 0, violations)


def strip_formatting_artifacts(text: str) -> str:
    """Defense-in-depth: even with the prompt telling the model never to
    use bracket/tag notation, small models sometimes copy formatting
    from their input into their output anyway. Strips anything shaped
    like [some_tag] before the text ever reaches a caregiver."""
    return re.sub(r"\[[a-zA-Z0-9_ ]+\]\s*", "", text).strip()


def safe_or_fallback(generated_text: str, fallback_text: str) -> str:
    """Convenience wrapper: use the model's phrasing if it passes
    guardrails, otherwise fall back to the deterministic action text
    (still correct, just less naturally phrased)."""
    cleaned = strip_formatting_artifacts(generated_text)
    is_safe, _violations = scan_output(cleaned)
    return cleaned if is_safe else fallback_text