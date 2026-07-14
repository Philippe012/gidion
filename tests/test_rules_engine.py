import json
from pathlib import Path

import pytest

from app.core.data.visit import Visit
from app.core.rules.imci_child import assess

CASES_PATH = Path(__file__).parent / "test_cases.json"
with open(CASES_PATH) as f:
    CASES = json.load(f)


@pytest.mark.parametrize("case", CASES, ids=[c["label"] for c in CASES])
def test_case(case):
    visit = Visit(**case["visit"])
    result = assess(visit)
    assert result.overall_urgency == case["expect_urgency"], (
        f"{case['label']}: expected {case['expect_urgency']}, "
        f"got {result.overall_urgency} "
        f"(results: {[(r.category, r.classification) for r in result.results]})"
    )


def test_multi_category_does_not_drop_findings():
    """The specific safety property the multi-category design exists
    for: a visit with pneumonia AND some dehydration AND malaria must
    report all three, not just the most severe one."""
    visit = Visit(
        age_months=30,
        cough=True, fast_breathing=True,
        diarrhoea=True, sunken_eyes=True, drinks_eagerly_thirsty=True,
        fever=True, malaria_risk_area="high",
    )
    result = assess(visit)
    categories = {r.category for r in result.results}
    assert "cough_or_breathing" in categories
    assert "diarrhoea" in categories
    assert "fever" in categories


def test_no_drug_names_in_any_action_text():
    """Guards the non-prescribing boundary at the data layer: no action
    string produced by the rules engine should ever contain a drug
    name, regardless of which classification fires."""
    from app.core.llm.guardrails import _BANNED_DRUG_TERMS

    all_true_visit = Visit(
        age_months=30,
        unable_to_drink=True, cough=True, fast_breathing=True,
        chest_indrawing=True, stridor=True, wheeze=True,
        diarrhoea=True, diarrhoea_days=20, blood_in_stool=True,
        sunken_eyes=True, skin_pinch_very_slow=True,
        fever=True, stiff_neck=True, malaria_risk_area="high",
        other_fever_source_found=True, measles_now_or_recent=True,
        clouded_cornea=True, ear_pain=True, tender_swelling_behind_ear=True,
        throat_pain=True, red_throat_or_exudate=True,
        tender_neck_lymph_nodes=True, visible_severe_wasting=True,
        palmar_pallor="severe",
    )
    result = assess(all_true_visit)
    for r in result.results:
        lowered = r.action.lower()
        for drug in _BANNED_DRUG_TERMS:
            assert drug not in lowered, (
                f"Drug term '{drug}' found in action text for "
                f"{r.category}/{r.classification}"
            )