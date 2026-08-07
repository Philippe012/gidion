import re

_BANNED_DRUG_TERMS = [
    "ampicillin", "gentamicin", "gentamycin", "cotrimoxazole", "amoxicillin",
    "amoxycillin", "erythromycin", "ciprofloxacin", "metronidazole",
    "chloroquine", "sulfadoxine", "pyrimethamine", "quinine", "paracetamol",
    "vitamin a capsule", "mebendazole", "salbutamol", "diazepam",
    "gentian violet", "tetracycline", "iron/folate", "folic acid",
    "zinc tablet", "ors packet",
]

# Greetings, apologies, introductions, and assistant-like chatter
_BANNED_EXTRANEOUS_PATTERNS = [
    r"\bhello\b",
    r"\bhi\b",
    r"\bhey\b",
    r"\bgood (morning|afternoon|evening)\b",
    r"\bi'm sorry\b",
    r"\bi am sorry\b",
    r"\bsorry to hear\b",
    r"\bhow can i help\b",
    r"\bhow can i assist\b",
    r"\bi'm gidion\b",
    r"\bi am gidion\b",
]

_BANNED_REASSURANCE_PATTERNS = [
    r"\bprobably (nothing|fine|benign|okay)\b",
    r"\bdon'?t worry\b",
    r"\bunlikely to be (serious|cancer|dangerous)\b",
    r"\bno need to (worry|see a doctor|refer)\b",
    r"\bmild (case|form) of cancer\b",
    r"\bit'?s (just|only) a\b",
]

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
    violations = []

    drug_hits = _find_matches(text, _BANNED_DRUG_TERMS)
    if drug_hits:
        violations.append(
            f"Contains medication/drug terms: {', '.join(drug_hits)}"
        )

    extraneous_hits = _find_pattern_matches(
        text,
        _BANNED_EXTRANEOUS_PATTERNS,
    )
    if extraneous_hits:
        violations.append(
            "Contains extraneous greeting/apology"
        )

    reassurance_hits = _find_pattern_matches(
        text,
        _BANNED_REASSURANCE_PATTERNS,
    )
    if reassurance_hits:
        violations.append(
            "Contains reassurance/risk-estimation language"
        )

    diagnosis_hits = _find_pattern_matches(
        text,
        _BANNED_DIAGNOSIS_PATTERNS,
    )
    if diagnosis_hits:
        violations.append(
            "Contains model-asserted diagnosis language"
        )

    return (len(violations) == 0, violations)


def strip_formatting_artifacts(text: str) -> str:
    return re.sub(r"\[[a-zA-Z0-9_ ]+\]\s*", "", text).strip()


def safe_or_fallback(generated_text: str, fallback_text: str) -> str:
    cleaned = strip_formatting_artifacts(generated_text)
    is_safe, _violations = scan_output(cleaned)
    return cleaned if is_safe else fallback_text