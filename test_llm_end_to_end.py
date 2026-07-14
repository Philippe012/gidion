
from app.core.data.visit import Visit
from app.core.rules.imci_child import assess
from app.core.llm.model_wrapper import LocalModel, ModelUnavailableError
from app.core.llm.prompts import build_note_prompt
from app.core.llm.guardrails import scan_output


def run_case(label: str, visit: Visit, model: LocalModel):
    print(f"\n=== {label} ===")
    assessment = assess(visit)
    print(f"Rules engine classification: {[(r.category, r.classification) for r in assessment.results]}")
    print(f"Overall urgency: {assessment.overall_urgency}")

    prompt = build_note_prompt(assessment, visit.age_months)
    # Phi-3's expected chat format, per its model card
    formatted_prompt = f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n"

    raw_output = model.generate(formatted_prompt)
    print(f"\nRaw model output:\n{raw_output}")

    is_safe, violations = scan_output(raw_output)
    print(f"\nGuardrail check: {'PASSED' if is_safe else 'FAILED'}")
    if violations:
        for v in violations:
            print(f"  - {v}")


if __name__ == "__main__":
    try:
        model = LocalModel()
        model._ensure_loaded()  # forces the load now, so any error surfaces immediately
    except ModelUnavailableError as e:
        print(f"Model not available: {e}")
        raise SystemExit(1)

    print("Model loaded successfully.\n")

    run_case("Pneumonia (simple case)", Visit(
        age_months=24, cough=True, fast_breathing=True,
    ), model)

    run_case("Multi-category: pneumonia + some dehydration + malaria", Visit(
        age_months=30,
        cough=True, fast_breathing=True,
        diarrhoea=True, sunken_eyes=True, drinks_eagerly_thirsty=True,
        fever=True, malaria_risk_area="high",
    ), model)

    run_case("Danger sign present", Visit(
        age_months=18, unable_to_drink=True,
    ), model)