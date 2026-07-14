"""
Prompt templates for the local LLM.

The model's ONLY job is phrasing: turn a classification the rules
engine already produced into a natural clinical note, or turn "what
Visit field is still missing" into a natural spoken question. It never
decides urgency, never suggests a diagnosis or medication that isn't
already in the classification's action text, and never reassures.

Every prompt below explicitly restates that boundary, because a local
1B-class model needs it spelled out plainly and repeatedly to stay
in-scope — this is the main defense referenced in the SDLC's risk table
("Model overstates its role... scoped to phrasing only").
"""

from app.core.data.visit import Assessment

_SYSTEM_BOUNDARY = (
    "You are a phrasing assistant inside a clinical triage tool called "
    "Gidion. You do not diagnose, you do not suggest medications, and "
    "you do not reassure the caregiver about outcomes. A separate, "
    "deterministic rules engine has already decided the classification "
    "and the recommended action — your only job is to phrase what it "
    "already decided in plain, calm language. Never add a classification, "
    "medication, or diagnosis that isn't given to you below. If asked "
    "about something outside the given classification, say the "
    "professional should assess that separately. Write in flowing plain "
    "sentences only — never use brackets, tags, category labels, code "
    "names, or any punctuation like [this] anywhere in your answer."
)


def humanize(slug: str) -> str:
    """'some_dehydration' -> 'Some Dehydration'. Used so raw internal
    classification slugs never reach the model prompt or the UI
    verbatim — everything gets translated to plain words first."""
    return slug.replace("_", " ").strip().title()


def build_note_prompt(assessment: Assessment, child_age_months: int) -> str:
    """Builds the prompt for writing a structured clinical note from an
    already-computed Assessment. The model rephrases; it does not
    re-derive anything. Classifications are given as plain sentences,
    not bracket/tag notation — that notation was leaking verbatim into
    model output, which is a formatting defect, not a safety one, but
    still not something a caregiver should ever see or hear."""
    lines = [_SYSTEM_BOUNDARY, "", f"Child age: {child_age_months} months.", ""]

    if not assessment.results:
        lines.append("No classification was triggered for this visit.")
    else:
        lines.append("Findings the rules engine already determined:")
        for r in assessment.results:
            lines.append(f"- The child has been classified with {humanize(r.classification)}. "
                        f"Recommended action: {r.action}")

    if assessment.routine_reminders:
        lines.append("")
        lines.append("Routine care reminders:")
        for reminder in assessment.routine_reminders:
            lines.append(f"- {reminder}")

    lines.append("")
    lines.append(
        "Write this up as a short note (3-6 sentences) a health worker "
        "could read back to the caregiver. Use the findings and actions "
        "above, in plain flowing language, addressed to the caregiver. "
        "Do not invent additional detail, medications, or reassurance. "
        "Do not use brackets, tags, or code-style labels anywhere."
    )
    return "\n".join(lines)


def build_fallback_note(assessment: Assessment) -> str:
    """Deterministic, LLM-free note — used when the model isn't loaded,
    or when its output fails the guardrail scan. Always correct (it's
    just the rules engine's own text), always bracket-free, so the UI
    never has to choose between 'no answer' and 'a raw debug dump'."""
    if not assessment.results:
        return "No classification was triggered for this visit."

    sentences = []
    for r in assessment.results:
        sentences.append(f"{humanize(r.classification)}: {r.action}")

    note = " ".join(sentences)
    if assessment.routine_reminders:
        note += " " + " ".join(assessment.routine_reminders)
    return note


def build_next_question_prompt(missing_field_description: str) -> str:
    """Builds the prompt for phrasing the next data-collection question
    during a visit (e.g. voice mode asking the health worker what to
    check next)."""
    return (
        f"{_SYSTEM_BOUNDARY}\n\n"
        f"The rules engine needs this piece of information next: "
        f"{missing_field_description}\n\n"
        f"Phrase this as a single, short, natural spoken question a health "
        f"worker could ask or check for themselves. Do not add any other "
        f"questions or clinical commentary."
    )