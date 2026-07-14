# Gidion

Offline AI clinical triage assistant for healthcare professionals
(pharmacists, nurses, community health workers). Combines a
deterministic clinical rules engine with a small local language model
for note-writing and voice interaction. Runs entirely on-device no
server, no API key, no internet required after setup.

**Gidion is a professional-facing tool. Patients never interact with it
directly, and the professional remains the final decision-maker at all
times.** Every recommendation is labeled "suggestion only clinical
decision remains with you."

See the full SDLC document for scope, architecture, and roadmap.

## Status

Phase 0 (protocol foundation) and Phase 1 (rules engine) are implemented
and tested for the IMCI child (2 months–5 years) fever/cough/diarrhoea/
ear/throat/malnutrition/anaemia protocol. **The clinical sanity check
(Phase 0.3) has not yet been completed** — see
`docs/imci_child_protocol.md` for what's verified against source text
vs. still pending review. Treat this build as ready for testing, not
ready for real patients.

## Project layout

```
app/
  config.py              # paths, deployment settings, disclaimer text
  main.py                # entry point, first-run model check
  core/
    data/visit.py         # Visit / ClassificationResult / Assessment
    rules/engine.py        # generic Rule / RuleSet evaluator
    rules/imci_child.py    # IMCI child protocol encoded as rules
    llm/model_wrapper.py    # llama-cpp-python wrapper
    llm/prompts.py           # phrasing-only prompt templates
    llm/guardrails.py         # output scanning (drugs/diagnosis/reassurance)
    voice/stt.py               # whisper.cpp wrapper (offline)
    voice/tts.py                 # Piper wrapper (offline)
  storage/local_store.py  # opt-in SQLite override logging
  ui/server.py            # local Flask UI
docs/
  imci_child_protocol.md            # human-readable source of truth
  imci_child_protocol_engineering_notes.md
models/                    # place GGUF model + Piper voice here (not committed)
tests/
  test_cases.json
  test_rules_engine.py
```

## Setup

```bash
pip install -r requirements.txt
```

Download a quantized GGUF model (e.g. a 1B-class Phi-3-mini or Llama
3.2 build) and place it in `models/`, matching the filename in
`app/config.py` (`GIDION_LLM_MODEL` env var to override). Voice is
optional — set `GIDION_VOICE_ENABLED=1` and install a whisper.cpp model
+ Piper voice if you want speech input/output.

## Run

```bash
python -m app.main
```

Opens the local UI at `http://127.0.0.1:5000`.

## Test

```bash
pytest tests/ -v
```

## Build a distributable executable

```bash
./build.sh
```

## Key architectural principle

The rules engine makes every clinical decision. The language model only
rephrases decisions already made — it is never the source of clinical
judgment. Every clinical classification is traceable to a specific rule
in `core/rules/imci_child.py`, never a model inference.

## Non-goals (see SDLC §3.2, §11)

Gidion does not, and will not: talk to patients directly, diagnose
autonomously, prescribe medication, learn continually without human
review, or replace a licensed professional's judgment.