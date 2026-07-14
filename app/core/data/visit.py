from dataclasses import dataclass, field


@dataclass
class Visit:
    age_months: int

    # ---- Section 1 — General Danger Signs ----
    unable_to_drink: bool = False
    vomits_everything: bool = False
    convulsions_history: bool = False
    lethargic_or_unconscious: bool = False
    convulsing_now: bool = False

    # ---- Section 2 — Cough / Difficult Breathing ----
    cough: bool = False
    cough_days: int = 0
    fast_breathing: bool = False
    chest_indrawing: bool = False
    stridor: bool = False
    wheeze: bool = False

    # ---- Section 3 — Diarrhoea ----
    diarrhoea: bool = False
    diarrhoea_days: int = 0
    blood_in_stool: bool = False
    restless_or_irritable: bool = False
    sunken_eyes: bool = False
    drinks_eagerly_thirsty: bool = False
    unable_to_drink_or_drinking_poorly: bool = False
    skin_pinch_slow: bool = False
    skin_pinch_very_slow: bool = False

    # ---- Section 4 — Fever / Malaria / Measles ----
    fever: bool = False
    fever_days: int = 0
    stiff_neck: bool = False
    malaria_risk_area: str = "low"         
    other_fever_source_found: bool = False  # sore throat / ear infection / ARI / diarrhoea / other cause
    measles_now_or_recent: bool = False     # generalized rash + (cough or coryza or red eyes), now or in last 3 months
    clouded_cornea: bool = False
    deep_mouth_ulcers: bool = False
    eye_infection_or_small_mouth_ulcers: bool = False

    # ---- Section 5 — Ear Problem ----
    ear_pain: bool = False
    ear_pus_discharge: bool = False
    ear_pus_days: int = 0
    tender_swelling_behind_ear: bool = False

    # ---- Section 6 — Throat Problem ----
    throat_pain: bool = False
    red_throat_or_exudate: bool = False
    tender_neck_lymph_nodes: bool = False

    # ---- Section 7 — Malnutrition & Anaemia ----
    visible_severe_wasting: bool = False
    bilateral_oedema: bool = False
    very_low_weight_for_age: bool = False
    palmar_pallor: str = "none"  # "none" / "some" / "severe"

    # ---- Section 7f — Routine care (simplified stub; see note below) ----
    # A full immunization-by-date system is out of scope for this pass —
    # these flags are a simplification: "has the child received X within
    # the window the booklet specifies", not a real schedule tracker.
    vitamin_a_last_6_months: bool = True
    dewormed_last_6_months: bool = True


@dataclass
class ClassificationResult:
    """One classification for ONE symptom category (cough, fever, etc)."""
    category: str
    classification: str
    action: str          # drug-free — this is what Gidion is allowed to say
    section_ref: str
    action_level: int    # 0=home_care 1=follow_up 2=refer_soon 3=urgent_referral


@dataclass
class Assessment:
    """The combined result across ALL symptom categories for one visit."""
    danger_sign_present: bool = False
    results: list[ClassificationResult] = field(default_factory=list)
    routine_reminders: list[str] = field(default_factory=list)
    overall_urgency: str = "no_classification"
    overall_action_level: int = 0