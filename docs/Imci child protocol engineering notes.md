# Engineering Notes — IMCI Child Protocol

Companion to `docs/imci_child_protocol.md`. This file is implementation
guidance for Phase 1 coding, not clinical content — if it and the
protocol doc ever disagree about what a classification *is*, the
protocol doc wins.

## Rule evaluation order

Section 1 (danger signs) first, unconditionally. Every remaining
category — cough, diarrhoea, fever, measles, ear, throat, malnutrition,
anaemia — is evaluated **independently**, per the existing
multi-category `Assessment` design in `imci_child.py`. `measles` is its
own `RuleSet`, evaluated alongside (not instead of) `fever_rules`, since
a visit can classify as both Malaria and Measles at once.

## `visit.py` field additions

```python
# Section 4 additions
malaria_risk_area: str = "low"       # "high" or "low" — was a plain bool before
other_fever_source_found: bool = False
measles_now_or_recent: bool = False  # rash + (cough or coryza or red_eyes)
clouded_cornea: bool = False
deep_mouth_ulcers: bool = False
eye_infection_or_small_mouth_ulcers: bool = False

# Section 5 — Ear
ear_pain: bool = False
ear_pus_discharge: bool = False
ear_pus_days: int = 0
tender_swelling_behind_ear: bool = False

# Section 6 — Throat
throat_pain: bool = False
red_throat_or_exudate: bool = False
tender_neck_lymph_nodes: bool = False

# Section 7 — Malnutrition / Anaemia
visible_severe_wasting: bool = False
bilateral_oedema: bool = False
very_low_weight_for_age: bool = False
palmar_pallor: str = "none"          # "none" / "some" / "severe"
```

## Before encoding

1. Clinical sanity check (Phase 0.3) — prioritize §4 (fever/measles),
   since its branch structure is a reconstruction rather than a verbatim
   transcription; everything else is more directly quoted.
2. Confirm the malaria-risk province list (§4.5 of the protocol doc)
   against current national data before relying on it beyond synthetic
   testing.

## Test cases to add to `tests/test_cases.json`

Mirror the existing style. New cases needed: diarrhoea modifiers
(persistent diarrhoea, dysentery), malaria + other-infection together,
measles alone, measles + malaria together, ear (all three tiers), throat
(both tiers), malnutrition, anaemia (all three tiers).