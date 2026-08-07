from app.core.data.visit import Assessment

_SYSTEM_BOUNDARY = (
    "You are Gidion, a phrasing assistant inside a clinical triage tool. "
    "A rules engine has already decided the classification and action. "
    "Your only job is to rephrase that decision in plain, calm language. "
    "Do not diagnose, do not suggest medications, do not reassure about outcomes. "
    "Never use brackets, tags, or labels like [this]. "
    "Be concise: do not include greetings, apologies, empathy, or any extra commentary."
)


def humanize(slug: str) -> str:
    return slug.replace("_", " ").strip().title()


def build_note_prompt(assessment: Assessment, child_age_months: int) -> str:
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
    return (
        f"{_SYSTEM_BOUNDARY}\n\n"
        f"The rules engine needs this piece of information next: "
        f"{missing_field_description}\n\n"
        
        f"... Phrase this as a single, short, natural spoken question a health "
        f"worker could ask. OUTPUT MUST BE ONLY THAT QUESTION — no greeting, no "
        f"apology, no explanation, no extra sentences, no labels or punctuation "
        f"beyond what the question requires."
    )