
from app.core.data.visit import Visit, Assessment, ClassificationResult
from app.core.rules.engine import Rule, RuleSet

_LEVEL_LABELS = {
    0: "home_care",
    1: "follow_up",
    2: "refer_soon",
    3: "urgent_referral",
}

def has_general_danger_sign(v: Visit) -> bool:
    return any([
        v.unable_to_drink,
        v.vomits_everything,
        v.convulsions_history,
        v.lethargic_or_unconscious,
        v.convulsing_now,
    ])


def is_fast_breathing_for_age(age_months: int, fast_breathing_flag: bool) -> bool:
    return fast_breathing_flag


cough_rules = RuleSet("cough_or_breathing", [
    Rule(
        condition=lambda v: v.cough and (v.stridor or v.chest_indrawing),
        classification="severe_pneumonia",
        action="Urgent pre-referral care. Refer urgently to hospital. "
               "If wheeze is also present, treat wheeze first.",
        section_ref="2a",
        action_level=3,
    ),
    Rule(
        condition=lambda v: v.cough and v.fast_breathing
                            and not (v.chest_indrawing or v.stridor),
        classification="pneumonia",
        action="Follow up in 2 days. Advise return immediately if breathing "
               "becomes faster or more difficult. Counsel on a safe home "
               "remedy. If wheeze is also present, treat wheeze too.",
        section_ref="2b",
        action_level=1,
    ),
    Rule(
        condition=lambda v: v.cough,
        classification="no_pneumonia_cough_or_cold",
        action="Home care appropriate. If cough has lasted more than 14 days, "
               "refer for non-urgent assessment. Follow up in 5 days if not "
               "improving. Advise return immediately if worse. Counsel on a "
               "safe home remedy. If wheeze is also present, treat wheeze too.",
        section_ref="2c",
        action_level=0,
    ),
])


def wheeze_note(v: Visit) -> ClassificationResult | None:
    if not v.wheeze:
        return None
    if v.chest_indrawing or v.stridor or has_general_danger_sign(v):
        action = ("Treat wheeze as part of emergency care — bronchodilator "
                  "and pre-referral treatment together, then refer immediately.")
        level = 3
    elif v.fast_breathing:
        action = "Treat wheeze alongside the pneumonia classification above."
        level = 1
    else:
        action = "Treat wheeze alongside the cough/cold classification above."
        level = 0
    return ClassificationResult(
        category="wheeze_modifier",
        classification="wheeze_present",
        action=action,
        section_ref="2e",
        action_level=level,
    )

diarrhoea_dehydration_rules = RuleSet("diarrhoea", [
    Rule(
        condition=lambda v: v.diarrhoea and sum([
            v.lethargic_or_unconscious,
            v.sunken_eyes,
            v.unable_to_drink_or_drinking_poorly,
            v.skin_pinch_very_slow,
        ]) >= 2,
        classification="severe_dehydration",
        action="Urgent rehydration. If another severe classification is "
               "also present, refer urgently to hospital, advising frequent "
               "sips of oral rehydration solution and breastmilk on the way.",
        section_ref="3a",
        action_level=3,
    ),
    Rule(
        condition=lambda v: v.diarrhoea and sum([
            v.restless_or_irritable,
            v.sunken_eyes,
            v.drinks_eagerly_thirsty,
            v.skin_pinch_slow,
        ]) >= 2,
        classification="some_dehydration",
        action="Rehydrate in clinic. If a severe classification is also "
               "present, refer urgently with frequent sips of oral "
               "rehydration solution on the way. Otherwise follow up in 2 "
               "days if not improving. Advise return immediately if worse.",
        section_ref="3b",
        action_level=1,
    ),
    Rule(
        condition=lambda v: v.diarrhoea,
        classification="no_dehydration",
        action="Home fluid and feeding guidance. Advise return immediately "
               "if worse.",
        section_ref="3c",
        action_level=0,
    ),
])


def persistent_diarrhoea_note(v: Visit) -> ClassificationResult | None:
    if not (v.diarrhoea and v.diarrhoea_days >= 14):
        return None
    has_some_dehydration = sum([
        v.restless_or_irritable, v.sunken_eyes,
        v.drinks_eagerly_thirsty, v.skin_pinch_slow,
    ]) >= 2
    if has_some_dehydration:
        action = ("Counsel on feeding for persistent diarrhoea. Rehydrate, "
                  "encourage feeding, and refer for assessment.")
        level = 2
    else:
        action = ("Counsel on feeding for persistent diarrhoea. Follow up "
                  "in 5 days if not improving.")
        level = 1
    return ClassificationResult(
        category="diarrhoea_persistent",
        classification="persistent_diarrhoea",
        action=action,
        section_ref="3d",
        action_level=level,
    )


def dysentery_note(v: Visit) -> ClassificationResult | None:
    if not (v.diarrhoea and v.blood_in_stool):
        return None
    return ClassificationResult(
        category="diarrhoea_dysentery",
        classification="dysentery",
        action="Treat for dysentery. Treat any dehydration present. Advise "
               "return immediately if worse. Follow up in 2 days if not "
               "improving.",
        section_ref="3e",
        action_level=1,
    )


fever_rules = RuleSet("fever", [
    Rule(
        condition=lambda v: v.fever and v.stiff_neck,
        classification="very_severe_febrile_disease",
        action="Urgent pre-referral care. Refer urgently to hospital.",
        section_ref="4a",
        action_level=3,
    ),
    Rule(
        condition=lambda v: v.fever and v.malaria_risk_area == "high"
                            and v.other_fever_source_found,
        classification="malaria_and_other_infection",
        action="Treat for malaria and for the other identified infection "
               "(see that infection's own classification). Advise return "
               "immediately if worse.",
        section_ref="4c",
        action_level=2,
    ),
    Rule(
        condition=lambda v: v.fever and v.malaria_risk_area == "high"
                            and not v.other_fever_source_found,
        classification="malaria",
        action="Treat for malaria. Advise return immediately if worse. "
               "Follow up in 2 days if fever persists. If fever has been "
               "present every day for more than 7 days, refer for assessment.",
        section_ref="4b",
        action_level=1,
    ),
    Rule(
        condition=lambda v: v.fever and v.malaria_risk_area == "low",
        classification="fever_other_infection_malaria_unlikely",
        action="Treat any identified other infection per its own "
               "classification. Advise return immediately if worse. Follow "
               "up in 2 days if fever persists. If fever has been present "
               "every day for more than 7 days, refer for assessment.",
        section_ref="4d",
        action_level=0,
    ),
])

measles_rules = RuleSet("measles", [
    Rule(
        condition=lambda v: v.measles_now_or_recent
                            and (v.clouded_cornea or v.deep_mouth_ulcers),
        classification="severe_complicated_measles",
        action="Urgent pre-referral care. Refer urgently to hospital. "
               "Advise the mother to continue feeding the child.",
        section_ref="4e-severe",
        action_level=3,
    ),
    Rule(
        condition=lambda v: v.measles_now_or_recent
                            and v.eye_infection_or_small_mouth_ulcers,
        classification="measles_with_eye_or_mouth_complications",
        action="Follow up in 2 days. Advise the mother to continue "
               "feeding the child.",
        section_ref="4e-complications",
        action_level=1,
    ),
    Rule(
        condition=lambda v: v.measles_now_or_recent,
        classification="simple_measles",
        action="Counsel the mother to continue feeding the child. Follow "
               "up in 2 days if no improvement.",
        section_ref="4e-simple",
        action_level=0,
    ),
])


ear_rules = RuleSet("ear", [
    Rule(
        condition=lambda v: v.tender_swelling_behind_ear,
        classification="mastoiditis",
        action="Give first-dose pain relief. Refer urgently to hospital.",
        section_ref="5a",
        action_level=3,
    ),
    Rule(
        condition=lambda v: v.ear_pain or (v.ear_pus_discharge and v.ear_pus_days < 14),
        classification="acute_ear_infection",
        action="Follow up in 5 days. Advise on drying the ear (wicking) "
               "at home.",
        section_ref="5b",
        action_level=1,
    ),
    Rule(
        condition=lambda v: v.ear_pus_discharge and v.ear_pus_days >= 14,
        classification="chronic_ear_infection",
        action="Follow up in 5 days. Advise on drying the ear (wicking) "
               "at home.",
        section_ref="5c",
        action_level=1,
    ),
])



throat_rules = RuleSet("throat", [
    Rule(
        condition=lambda v: v.throat_pain and sum([
            v.red_throat_or_exudate, v.tender_neck_lymph_nodes,
        ]) >= 2,
        classification="streptococcal_sore_throat",
        action="Soothe the throat with a safe home remedy. Advise return "
               "immediately if worse. Follow up in 5 days if no improvement.",
        section_ref="6a",
        action_level=1,
    ),
    Rule(
        condition=lambda v: v.throat_pain,
        classification="viral_sore_throat",
        action="Soothe the throat with a safe home remedy. Advise return "
               "immediately if worse. Follow up in 5 days if no improvement.",
        section_ref="6b",
        action_level=0,
    ),
])


malnutrition_rules = RuleSet("malnutrition", [
    Rule(
        condition=lambda v: v.visible_severe_wasting or v.bilateral_oedema
                            or v.very_low_weight_for_age,
        classification="severe_malnutrition",
        action="Refer urgently to hospital. Treat to prevent low blood "
               "sugar before referral.",
        section_ref="7a",
        action_level=3,
    ),
])

anaemia_rules = RuleSet("anaemia", [
    Rule(
        condition=lambda v: v.palmar_pallor == "severe",
        classification="severe_anaemia",
        action="Refer urgently to hospital. Treat to prevent low blood "
               "sugar before referral.",
        section_ref="7c",
        action_level=3,
    ),
    Rule(
        condition=lambda v: v.palmar_pallor == "some",
        classification="anaemia",
        action="Assess feeding and counsel. Advise return immediately if "
               "worse. Follow up in 14 days.",
        section_ref="7d",
        action_level=1,
    ),
])


def check_routine_care(v: Visit) -> list[str]:
    reminders = []
    if v.age_months >= 6 and not v.vitamin_a_last_6_months:
        reminders.append("Vitamin A supplementation is due (age >= 6 months, "
                         "none recorded in the last 6 months).")
    if v.age_months >= 12 and not v.dewormed_last_6_months:
        reminders.append("Deworming dose is due (age >= 1 year, none "
                         "recorded in the last 6 months).")
    return reminders


def assess(visit: Visit) -> Assessment:
    assessment = Assessment()

    if has_general_danger_sign(visit):
        assessment.danger_sign_present = True
        assessment.results.append(ClassificationResult(
            category="danger_sign",
            classification="very_severe_disease",
            action="Treat as an emergency. Refer urgently to hospital. Do "
                   "not delay for further assessment. Briefly check for "
                   "cough, fever, diarrhoea, sore throat, and severe "
                   "malnutrition while preparing referral.",
            section_ref="1",
            action_level=3,
        ))

    if visit.cough:
        result = cough_rules.evaluate(visit)
        if result:
            assessment.results.append(result)
        wheeze = wheeze_note(visit)
        if wheeze:
            assessment.results.append(wheeze)

    if visit.diarrhoea:
        result = diarrhoea_dehydration_rules.evaluate(visit)
        if result:
            assessment.results.append(result)
        for note_fn in (persistent_diarrhoea_note, dysentery_note):
            note = note_fn(visit)
            if note:
                assessment.results.append(note)

    if visit.fever:
        result = fever_rules.evaluate(visit)
        if result:
            assessment.results.append(result)

    if visit.measles_now_or_recent:
        result = measles_rules.evaluate(visit)
        if result:
            assessment.results.append(result)

    if visit.ear_pain or visit.ear_pus_discharge or visit.tender_swelling_behind_ear:
        result = ear_rules.evaluate(visit)
        if result:
            assessment.results.append(result)

    if visit.throat_pain:
        result = throat_rules.evaluate(visit)
        if result:
            assessment.results.append(result)

    result = malnutrition_rules.evaluate(visit)
    if result:
        assessment.results.append(result)

    result = anaemia_rules.evaluate(visit)
    if result:
        assessment.results.append(result)

    assessment.routine_reminders = check_routine_care(visit)

    if assessment.results:
        top = max(assessment.results, key=lambda r: r.action_level)
        assessment.overall_action_level = top.action_level
        assessment.overall_urgency = _LEVEL_LABELS[top.action_level]

    return assessment