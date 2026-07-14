# IMCI Child Protocol — Plain-Language Decision Table

**Source:** *Integrated Management of Childhood Illness* Chart Booklet —
WHO / Ministry of Public Health, Afghanistan / UNICEF, "Sick Child Age 2
Months up to 5 Years" (document ref. AFG-MN-62-01, Operational Guidance
2015).
**Validation status:** Verified against source text throughout. Section
4's branch structure (not its classifications or actions) is a
reconstruction — see §4.0. Pending: one clinical review before final
encoding.

---

## 0. Country-adaptation notice — read before deploying

This chart booklet is Afghanistan's national adaptation of the WHO IMCI
guidelines. The **classification logic and thresholds** (fast-breathing
cutoffs, dehydration sign combinations, fever temperature threshold, etc.)
are WHO-standard and should transfer to other IMCI-based settings largely
unchanged. Two things are specific to Afghanistan and must be
reconfigured for any other deployment:

- **Malaria risk area mapping** — Afghanistan's province-level
  high/low-risk list (§4.5). Any new deployment region needs its own
  malaria-risk source (national malaria control programme), not this list.
- **Drug/formulary names** — this booklet names Afghanistan's first- and
  second-line drugs. Per Gidion's non-prescribing scope (SDLC §3.2), these
  are **not** part of what Gidion voices as a recommendation in any
  deployment, Afghanistan or otherwise — see §0.1.

### 0.1 Non-prescribing boundary (applies to every section below)

Every classification in this document has two parts:

- **Action (Gidion's output)** — classification name, urgency, referral
  instruction, follow-up timing, and general counsel. This is what the
  rules engine encodes and what Gidion is allowed to say.
- **Clinical reference (not spoken by Gidion)** — the specific
  medication named in the booklet, kept here only so a clinician can
  cross-reference the source chart. **This text must never flow into
  `imci_child.py`'s action strings, the LLM's prompt output, or anything
  voiced/displayed to the user as a recommendation.** Gidion tells the
  professional *what* the classification and urgency are; the
  professional decides *what drug*, using their own training and
  formulary.

This mirrors the SDLC's explicit non-goal: *"Medication prescribing"* is
out of scope for the foreseeable roadmap, not just MVP (§3.2, §11).

### 0.2 Age scope

This document covers the **Sick Child, age 2 months up to 5 years**
chart only. The booklet also contains a separate **Sick Young Infant,
birth up to 2 months** chart (assess/classify/treat, different danger
signs, different feeding assessment, jaundice classification). That is a
**distinct protocol**, not a sub-case of this one — it needs its own
`docs/` file and its own `RuleSet` if Gidion ever supports young infants.
Treat it as future scope (consistent with SDLC Phase 8's "add further
protocols incrementally"), not something to fold into `imci_child.py`.

---

## Section 1 — General Danger Signs — **Verified**

*Always checked first, before any other symptom. If any general danger
sign is present, this classification takes priority — the health worker
still checks cough/fever/diarrhoea/throat and looks for severe
malnutrition, but the response is emergency care, not the ordinary
follow-the-arrows classification.*

**Ask:** Is the child unable to drink or breastfeed? Has the child been
vomiting everything? Has the child had convulsions (history)?
**Look:** Is the child lethargic or unconscious? Is the child convulsing
right now?

**If:** any one of the above is true.

**Classification:** Very Severe Disease (General Danger Sign Present)

**Action (Gidion's output):** Treat as an emergency. Refer urgently to
hospital. Do not delay for further assessment. Briefly check for cough,
fever, diarrhoea, sore throat, and signs of severe malnutrition while
preparing referral, since these affect what pre-referral care is needed.

**Clinical reference (not spoken by Gidion):** first-dose antibiotic
(ampicillin + gentamicin) if cough/sore throat; diazepam + airway
management if convulsing; hydration (Plan C) if diarrhoea, reassess,
refer if not responding; antimalarial + antipyretic if fever ≥38.5°C in
a malaria-endemic area; prevent low blood sugar; vitamin A + refer if
severe malnutrition.

---

## Section 2 — Cough or Difficult Breathing — **Verified**

*Only reached if Section 1 found no danger signs.*

**Ask:** Does the child have cough or difficult breathing? If yes — how
many days? **Look:** is breathing fast for age? Is there chest
indrawing? **Listen:** for stridor (in a calm child). **Look and
listen:** for wheeze.

**Fast-breathing thresholds (age-specific):**
- 2 up to 12 months: ≥ 50 breaths/minute
- 12 up to 59 months: ≥ 40 breaths/minute

### 2a — Severe Pneumonia
**If:** cough/difficult breathing **and** (stridor in a calm child **or**
chest indrawing).
**Action:** Urgent pre-referral care. Refer urgently to hospital. If
wheeze is also present, treat wheeze first (see §2e).
**Clinical reference:** first dose ampicillin + gentamicin; aerosolized
salbutamol if wheeze present.

### 2b — Pneumonia
**If:** cough/difficult breathing **and** fast breathing for age, **and
no** chest indrawing or stridor.
**Action:** Follow up in 2 days. Advise return immediately if breathing
becomes faster or more difficult. Counsel on a safe home remedy for
cough/throat. If wheeze also present, treat wheeze too (§2e).
**Clinical reference:** oral antibiotic (cotrimoxazole) for 5 days.

### 2c — No Pneumonia (Cough or Cold)
**If:** cough/difficult breathing, **no** signs of pneumonia or very
severe disease.
**Action:** Home care appropriate. If cough has lasted more than 14
days, refer for non-urgent assessment. Follow up in 5 days if not
improving. Advise return immediately if worse. Counsel on a safe home
remedy. If wheeze also present, treat wheeze too (§2e).

### 2e — Wheeze (modifier — applies within 2a/2b/2c above, not standalone)
**If:** wheeze present, alongside general danger sign or stridor/chest
indrawing → treat as an emergency: give a rapid-acting bronchodilator
first, alongside the pre-referral antibiotic, then refer immediately.
**If:** wheeze present with fast breathing but no danger sign/stridor →
treat as Pneumonia (2b) and add an oral bronchodilator course (age ≥ 6
months).
**If:** wheeze present alone, no other pneumonia signs → treat as No
Pneumonia: Cough or Cold (2c) and add an oral bronchodilator course
(age ≥ 6 months).
**Clinical reference:** nebulized or oral salbutamol, dosed by weight/age
per the booklet's table (not part of Gidion's output).

---

## Section 3 — Diarrhoea — **Verified**

*Only reached if Section 1 found no danger signs.*

**Ask:** Does the child have diarrhoea? For how many days? Is there
blood in the stool? **Assess dehydration — ask/look:** is the child
lethargic/unconscious, or restless/irritable? Are the eyes sunken? Does
the child drink poorly, or eagerly/thirsty? Skin pinch: does it go back
slowly, or very slowly?

### 3a — Severe Dehydration
**If:** diarrhoea **and** two or more of: lethargic/unconscious, sunken
eyes, drinks poorly/unable to drink, skin pinch goes back very slowly.
**Action:** Urgent rehydration. If another severe classification is also
present, refer urgently to hospital, advising frequent sips of oral
rehydration solution and breastmilk on the way. Give zinc after
rehydration.
**Clinical reference:** rehydration Plan C; antibiotic for cholera if
locally relevant and child ≥ 2 years.

### 3b — Some Dehydration
**If:** diarrhoea **and** two or more of: restless/irritable, sunken
eyes, drinks eagerly/thirsty, skin pinch goes back slowly.
**Action:** Rehydrate in clinic. If a severe classification is also
present, refer urgently with frequent sips of oral rehydration solution
on the way. Otherwise follow up in 2 days if not improving. Give zinc.
Advise return immediately if worse.
**Clinical reference:** rehydration Plan B.

### 3c — No Dehydration
**If:** diarrhoea, not enough signs to classify as some or severe
dehydration.
**Action:** Home fluid and feeding guidance. Advise return immediately if
worse. Give zinc.
**Clinical reference:** rehydration Plan A.

### 3d — Persistent Diarrhoea (modifier)
**If:** diarrhoea lasting 14 days or more.
**Action:** Counsel on feeding for persistent diarrhoea. If also some
dehydration, rehydrate, encourage feeding, and refer for assessment. If
no dehydration, follow up in 5 days if not improving.
**Clinical reference:** zinc, folic acid, vitamin A.

### 3e — Dysentery (modifier)
**If:** blood in the stool.
**Action:** Treat for dysentery. Treat any dehydration present. Advise
return immediately if worse. Follow up in 2 days if not improving.
**Clinical reference:** antibiotic recommended locally for Shigella
(5-day course).

---

## Section 4 — Fever — **Verified, with one layout caveat (see 4.0)**

*Only reached if Section 1 found no danger signs. Fever is defined as: by
history, feels hot to touch, or measured (axillary) temperature ≥
37.5°C.*

### 4.0 Transparency note on this section

The source PDF's fever/malaria/measles chart is a two-column diagram
(malaria classification + measles classification evaluated in parallel)
that came through text extraction as one flattened stream, with some
Yes/No branch arrows separated from their outcome boxes. Every
classification **name** and **action** below is quoted directly from the
source; the **branching structure** connecting them is my reconstruction
based on standard WHO IMCI fever-chart logic, which this booklet's
wording is consistent with. Because this is a reconstruction rather than
a verbatim transcription of the diagram, **flag this specific section for
extra attention in Phase 0.3** — ideally have the reviewer look at the
original PDF page 4 layout side-by-side with this table.

### 4a — Very Severe Febrile Disease
**If:** fever **and** stiff neck (or any general danger sign, already
covered by Section 1).
**Action:** Urgent pre-referral care. Refer urgently to hospital.
**Clinical reference:** quinine (malaria-endemic areas), first dose
ampicillin + gentamicin, paracetamol if ≥ 38.5°C, prevent low blood
sugar.

*The malaria and measles classifications below (4b–4e) are independent
of each other — a child can be classified with both Malaria and Measles
at the same visit, and neither is mutually exclusive with the cough,
diarrhoea, ear, throat, malnutrition, or anaemia classifications either.
This is why Gidion's rules engine evaluates each category separately
(per the multi-category fix already in `imci_child.py`).*

### 4b — Malaria (high malaria-risk area)
**If:** fever, no danger sign or stiff neck, in a designated high
malaria-risk area, **no** other apparent source of fever found (sore
throat, ear infection, ARI, diarrhoea, or other cause).
**Action:** Treat for malaria. Advise return immediately if worse. Follow
up in 2 days if fever persists. If fever has been present every day for
more than 7 days, refer for assessment.
**Clinical reference:** oral antimalarial (first-line: chloroquine +
sulfadoxine-pyrimethamine); paracetamol if ≥ 38.5°C.

### 4c — Malaria and Other Infection (high malaria-risk area)
**If:** fever, no danger sign or stiff neck, in a high malaria-risk area,
**and** another apparent source of fever is found.
**Action:** Treat for malaria and for the other identified infection
(each per its own classification/action in this document, e.g. ear
infection, sore throat). Advise return immediately if worse.
**Clinical reference:** oral antimalarial + appropriate antibiotic for
the other infection; paracetamol if ≥ 38.5°C.

### 4d — Fever: Other Infection / Malaria Unlikely (low malaria-risk area)
**If:** fever, no danger sign or stiff neck, in a low malaria-risk area
— whether or not another source of fever is found.
**Action:** Treat any identified other infection per its own
classification. Advise return immediately if worse. Follow up in 2 days
if fever persists. If fever has been present every day for more than 7
days, refer for assessment.
**Clinical reference:** paracetamol if ≥ 38.5°C; antibiotic only if
another infection is identified.

### 4e — Measles classification (independent, only if measles signs present)
**Ask:** did the child have measles now or within the last 3 months?
**Look:** generalized rash **and** (cough **or** runny nose **or** red
eyes) = measles now.

If measles now or in the last 3 months, look for eye/mouth
complications:

- **Clouded cornea OR deep mouth ulcers → Severe Complicated Measles.**
  **Action:** Urgent pre-referral care. Refer urgently to hospital.
  Advise the mother to continue feeding the child.
  **Clinical reference:** vitamin A (if none in last 3 months), first
  dose ampicillin + gentamicin, tetracycline eye ointment if corneal
  clouding.
- **Eye infection OR small mouth ulcers (not severe) → Measles With Eye
  or Mouth Complications.**
  **Action:** Follow up in 2 days. Advise the mother to continue feeding
  the child.
  **Clinical reference:** vitamin A (if none in last 3 months); local eye
  ointment / gentian violet for mouth ulcers as appropriate.
- **Neither of the above → Simple Measles (now or within last 3
  months).**
  **Action:** Counsel the mother to continue feeding the child. Follow
  up in 2 days if no improvement.
  **Clinical reference:** vitamin A if none given in last 3 months.

*Note: pneumonia, stridor, diarrhoea, ear infection, and malnutrition
that occur alongside measles are classified independently in their own
sections, per the source booklet's own footnote — Gidion's multi-category
design already handles this correctly.*

### 4.5 Malaria risk area — Afghanistan-specific, reconfigure per deployment

**High malaria risk:** Kunar, Nangahar, Laghman, Kunduz, Baghlan, Takhar,
Nimroz, Helmand, Kandahar, Zabul, Farah (per source map — treat as
approximate; confirm against current national malaria programme data
before relying on this for any real deployment).
**Low malaria risk:** remaining provinces listed in the source map
(Herat, Badakhshan, Ghor, Baghdis, Balkh, Faryab, Jawzjan, Samangan,
Bamyan, Wardak, Kabul, Kapisa, Parwan, Logar, Paktya, Paktika, Ghazni,
Oruzgan).

This is exactly the kind of value that should live in a config file
(`app/config.py` or a deployment-specific data file), never hardcoded
into `imci_child.py` — a different country or even a different province
list revision shouldn't require touching rule logic.

---

## Section 5 — Ear Problem — **Verified**

**Ask:** Is there ear pain? Is there discharge from the ear — for how
long? **Feel:** for a tender swelling behind the ear.

### 5a — Mastoiditis
**If:** tender swelling behind the ear.
**Action:** Give first dose of pain relief. Refer urgently to hospital.
**Clinical reference:** first dose antibiotic (ampicillin + gentamicin);
first dose paracetamol for pain.

### 5b — Acute Ear Infection
**If:** ear pain, **or** pus draining from the ear for less than 14 days.
**Action:** Follow up in 5 days. Advise on drying the ear (wicking) at
home.
**Clinical reference:** oral antibiotic (cotrimoxazole, 5 days);
paracetamol for pain.

### 5c — Chronic Ear Infection
**If:** pus draining from the ear for 14 days or more.
**Action:** Follow up in 5 days. Advise on drying the ear (wicking) at
home.

---

## Section 6 — Throat Problem — **Verified**

*Note: not explicitly named in the SDLC's original fever/cough MVP
scope, but present in this source chart. Kept here rather than
discarded — flag as optional for Phase 1's first encoding pass, or
include alongside the ear-problem section since both are quick, low-risk
additions once Sections 1–4 are solid.*

**Ask:** Is there throat pain? **Look:** for a red throat or white
patches (exudate) on the tonsils. **Feel:** for swollen neck lymph
nodes.

### 6a — Streptococcal Sore Throat
**If:** throat pain **and** two or more of: red throat, exudate on
tonsils/throat, large tender neck lymph nodes.
**Action:** Soothe the throat with a safe home remedy. Advise return
immediately if worse. Follow up in 5 days if no improvement.
**Clinical reference:** oral antibiotic (amoxicillin, 5 days);
paracetamol for pain.

### 6b — Viral Sore Throat
**If:** throat pain, with one or none of the above signs.
**Action:** Soothe the throat with a safe home remedy. Advise return
immediately if worse. Follow up in 5 days if no improvement.
**Clinical reference:** paracetamol for pain only — no antibiotic.

---

## Section 7 — Malnutrition & Anaemia — **Verified**

### 7a — Severe Malnutrition (or Severe Anaemia branch below)
**Look:** for visible severe wasting, oedema of both feet, and determine
weight-for-age.

**If:** visible severe wasting, **or** oedema of both feet, **or** very
low weight for age.
**Action:** Refer urgently to hospital. Treat to prevent low blood
sugar before referral.
**Clinical reference:** vitamin A before referral.

### 7b — Not Very Low Weight
**If:** not very low weight for age and no other malnutrition signs.
**Action:** Assess feeding and counsel the caregiver (if child < 2 years
or a feeding concern exists). Follow up in 5 days if a feeding problem
was found; follow up in 30 days if very low weight was found previously.
Deworm if age ≥ 1 year and no deworming dose in the last 6 months.

### 7c — Severe Anaemia
**Look:** for palmar pallor — is it some, or severe?
**If:** severe palmar pallor.
**Action:** Refer urgently to hospital. Treat to prevent low blood
sugar before referral.

### 7d — Anaemia
**If:** some palmar pallor (not severe).
**Action:** Assess feeding and counsel. Advise return immediately if
worse. Follow up in 14 days.
**Clinical reference:** iron; antimalarial if high malaria-risk area;
deworming if age ≥ 1 year and none in last 6 months.

### 7e — No Anaemia
**If:** no palmar pallor.
**Action:** Assess feeding and counsel if child < 2 years.

### 7f — Immunization, Vitamin A, Deworming status
Checked for every sick child regardless of presenting complaint — not a
classification with urgency, but a checklist Gidion should still surface:
- **Immunization schedule (age 2–23 months):** BCG + OPV-0 at birth;
  Penta-1 + OPV-1 at 6 weeks; Penta-2 + OPV-2 at 10 weeks; Penta-3 +
  OPV-3 at 14 weeks; Measles-1 + OPV-4 at 9 months; Measles-2 at 18
  months.
- **Vitamin A supplementation:** if age ≥ 6 months and none given in the
  last 6 months, offer a dose.
- **Deworming:** if age ≥ 1 year and none given in the last 6 months,
  offer a dose.

---

## Scope note

The Sick Young Infant chart (birth–2 months) is intentionally out of
this document's scope (§0.2) — it's a distinct protocol with different
danger signs and a different feeding assessment, not a variant of this
one. It belongs in its own `docs/` file if and when Gidion supports young
infants.

Engineering notes (Visit/RuleSet field additions, encoding order,
suggested test cases) have moved to
`docs/imci_child_protocol_engineering_notes.md` so this file stays pure
clinical reference.