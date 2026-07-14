"""
Quick, no-UI way to see the rules engine actually answer.

Run this before touching Flask, the LLM, or voice — it only exercises
app/core, so it works the moment `pip install -r requirements.txt` has
finished, with no model files needed.
"""

from app.core.data.visit import Visit
from app.core.rules.imci_child import assess


def print_assessment(label: str, visit: Visit):
    result = assess(visit)
    print(f"\n=== {label} ===")
    print(f"Overall urgency: {result.overall_urgency}")
    if not result.results:
        print("  (no classification triggered)")
    for r in result.results:
        print(f"  [{r.category}] {r.classification} (section {r.section_ref})")
        print(f"    -> {r.action}")
    if result.routine_reminders:
        print("  Routine reminders:")
        for reminder in result.routine_reminders:
            print(f"    - {reminder}")


if __name__ == "__main__":
    print_assessment("Danger sign present", Visit(
        age_months=18, unable_to_drink=True,
    ))

    print_assessment("Cough with chest indrawing (severe pneumonia)", Visit(
        age_months=24, cough=True, chest_indrawing=True,
    ))

    print_assessment("Cough with fast breathing only (pneumonia)", Visit(
        age_months=24, cough=True, fast_breathing=True,
    ))

    print_assessment("Cough or cold, no complications", Visit(
        age_months=36, cough=True,
    ))

    print_assessment(
        "Multi-category: pneumonia + some dehydration + malaria together",
        Visit(
            age_months=30,
            cough=True, fast_breathing=True,
            diarrhoea=True, sunken_eyes=True, drinks_eagerly_thirsty=True,
            fever=True, malaria_risk_area="high",
        ),
    )

    print_assessment("Fever, malaria-risk area, no other source", Visit(
        age_months=42, fever=True, malaria_risk_area="high",
    ))

    print_assessment("Measles with clouded cornea (severe complicated)", Visit(
        age_months=30, measles_now_or_recent=True, clouded_cornea=True,
    ))

    print_assessment("Mastoiditis (tender swelling behind ear)", Visit(
        age_months=24, tender_swelling_behind_ear=True,
    ))

    print_assessment("Nothing reported", Visit(age_months=12))