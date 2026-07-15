  
"""
Local web UI (SDLC Phase 4).

Runs on 127.0.0.1 only — a local desktop app, never exposed to the
network. config.DISCLAIMER_TEXT is rendered persistently in the header;
it is not optional and not something a future feature flag should be
able to turn off.

Design choice worth stating explicitly: this is a GUIDED conversation,
not a free-text chatbot. The frontend asks a fixed sequence of
structured questions and the backend builds a Visit from the answers.
Nothing the user types is ever sent to the LLM as an open-ended
question — the LLM only ever phrases an Assessment the rules engine has
already produced. A free-text "ask anything" box would hand clinical
judgment to the model, which is exactly what the SDLC's architecture
forbids (rules engine decides, LLM only rephrases).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))



"""
Local web UI (SDLC Phase 4).

Runs on 127.0.0.1 only — a local desktop app, never exposed to the
network. config.DISCLAIMER_TEXT is rendered persistently in the header;
it is not optional and not something a future feature flag should be
able to turn off.

Design choice worth stating explicitly: this is a GUIDED conversation,
not a free-text chatbot. The frontend asks a fixed sequence of
structured questions and the backend builds a Visit from the answers.
Nothing the user types is ever sent to the LLM as an open-ended
question — the LLM only ever phrases an Assessment the rules engine has
already produced. A free-text "ask anything" box would hand clinical
judgment to the model, which is exactly what the SDLC's architecture
forbids (rules engine decides, LLM only rephrases).
"""

import io
import os
import threading

from flask import Flask, jsonify, render_template_string, request, send_file

from app import config
from app.core.data.visit import Visit
from app.core.rules.imci_child import assess
from app.core.llm.model_wrapper import LocalModel, ModelUnavailableError
from app.core.llm.prompts import build_note_prompt, build_fallback_note
from app.core.llm.guardrails import safe_or_fallback
from app.core.voice.stt import SpeechToText, VoiceUnavailableError as STTUnavailableError
from app.core.voice.tts import TextToSpeech, VoiceUnavailableError as TTSUnavailableError

app = Flask(__name__)

_model_lock = threading.Lock()
_model = None
_model_load_failed = False


def _get_model():
    global _model, _model_load_failed
    if _model is not None:
        return _model
    if _model_load_failed:
        return None
    with _model_lock:
        if _model is not None:
            return _model
        candidate = LocalModel()
        try:
            candidate._ensure_loaded()
            _model = candidate
            return _model
        except ModelUnavailableError:
            _model_load_failed = True
            return None


_stt_lock = threading.Lock()
_stt = None
_stt_load_failed = False


def _get_stt():
    global _stt, _stt_load_failed
    if _stt is not None:
        return _stt
    if _stt_load_failed:
        return None
    with _stt_lock:
        if _stt is not None:
            return _stt
        candidate = SpeechToText()
        try:
            candidate._ensure_loaded()
            _stt = candidate
            return _stt
        except STTUnavailableError:
            _stt_load_failed = True
            return None


_tts_lock = threading.Lock()
_tts = None
_tts_load_failed = False


def _get_tts():
    global _tts, _tts_load_failed
    if _tts is not None:
        return _tts
    if _tts_load_failed:
        return None
    with _tts_lock:
        if _tts is not None:
            return _tts
        candidate = TextToSpeech()
        try:
            candidate._ensure_loaded()
            _tts = candidate
            return _tts
        except TTSUnavailableError:
            _tts_load_failed = True
            return None


_BOOL_FIELDS = [
    "unable_to_drink", "vomits_everything", "convulsions_history",
    "lethargic_or_unconscious", "convulsing_now",
    "cough", "fast_breathing", "chest_indrawing", "stridor", "wheeze",
    "diarrhoea", "blood_in_stool", "restless_or_irritable", "sunken_eyes",
    "drinks_eagerly_thirsty", "unable_to_drink_or_drinking_poorly",
    "skin_pinch_slow", "skin_pinch_very_slow",
    "fever", "stiff_neck", "other_fever_source_found",
    "measles_now_or_recent", "clouded_cornea", "deep_mouth_ulcers",
    "eye_infection_or_small_mouth_ulcers",
    "ear_pain", "ear_pus_discharge", "tender_swelling_behind_ear",
    "throat_pain", "red_throat_or_exudate", "tender_neck_lymph_nodes",
    "visible_severe_wasting", "bilateral_oedema", "very_low_weight_for_age",
]
_INT_FIELDS = ["age_months", "cough_days", "diarrhoea_days", "fever_days", "ear_pus_days"]
_STR_FIELDS = ["malaria_risk_area", "palmar_pallor"]


def _visit_from_payload(payload):
    kwargs = {}
    for f in _BOOL_FIELDS:
        if f in payload:
            kwargs[f] = bool(payload[f])
    for f in _INT_FIELDS:
        if f in payload and payload[f] not in (None, ""):
            kwargs[f] = int(payload[f])
    for f in _STR_FIELDS:
        if f in payload and payload[f]:
            kwargs[f] = str(payload[f])
    if "age_months" not in kwargs:
        kwargs["age_months"] = 0
    return Visit(**kwargs)


_URGENCY_LABELS = {
    "urgent_referral": "Urgent referral",
    "refer_soon": "Refer for assessment",
    "follow_up": "Follow-up needed",
    "home_care": "Home care",
    "no_classification": "No classification triggered",
}


@app.route("/api/assess", methods=["POST"])
def api_assess():
    payload = request.get_json(force=True, silent=True) or {}
    visit = _visit_from_payload(payload)
    assessment = assess(visit)

    fallback = build_fallback_note(assessment)
    model = _get_model()
    used_llm = False
    note = fallback
    if model is not None:
        try:
            prompt = build_note_prompt(assessment, visit.age_months)
            formatted_prompt = "<|user|>\n" + prompt + "<|end|>\n<|assistant|>\n"
            raw = model.generate(formatted_prompt)
            note = safe_or_fallback(raw, fallback)
            used_llm = note.strip() != fallback.strip() or note.strip() == raw.strip()
        except Exception:
            note = fallback
            used_llm = False

    return jsonify({
        "note": note,
        "urgency": assessment.overall_urgency,
        "urgency_label": _URGENCY_LABELS.get(assessment.overall_urgency, assessment.overall_urgency),
        "action_level": assessment.overall_action_level,
        "used_llm": used_llm,
        "disclaimer": config.DISCLAIMER_TEXT,
    })


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    """Voice input. The transcript is NEVER sent to the LLM as a
    question — it's only used client-side to fill in the currently
    active structured question (see applyVoiceTranscript in the
    frontend). The rules engine still decides everything."""
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded."}), 400
    audio_file = request.files["audio"]
    suffix = os.path.splitext(audio_file.filename or "")[1] or ".webm"
    audio_bytes = audio_file.read()

    stt = _get_stt()
    if stt is None:
        return jsonify({
            "error": "Voice input isn't set up yet. Check README for the "
                    "whisper.cpp model + ffmpeg setup steps."
        }), 503
    try:
        text = stt.transcribe_bytes(audio_bytes, source_suffix=suffix)
        return jsonify({"text": text})
    except STTUnavailableError as e:
        return jsonify({"error": str(e)}), 503


@app.route("/api/speak", methods=["POST"])
def api_speak():
    payload = request.get_json(force=True, silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "No text provided."}), 400

    tts = _get_tts()
    if tts is None:
        return jsonify({
            "error": "Voice output isn't set up yet. Check README for the "
                    "Piper voice setup steps."
        }), 503
    try:
        audio_bytes = tts.synthesize_to_bytes(text)
        return send_file(io.BytesIO(audio_bytes), mimetype="audio/wav")
    except TTSUnavailableError as e:
        return jsonify({"error": str(e)}), 503


@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        _PAGE_TEMPLATE,
        disclaimer=config.DISCLAIMER_TEXT,
        voice_enabled=config.VOICE_ENABLED,
        intro_text=config.INTRO_TEXT,
    )


def run():
    app.run(host=config.UI_HOST, port=config.UI_PORT, debug=False)


_PAGE_TEMPLATE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gidion</title>
<style>
  :root {
    --bg: #0f1420;
    --panel: #161d2e;
    --panel-2: #1d2740;
    --accent: #5b8cff;
    --accent-2: #7ad1c9;
    --text: #e8ecf7;
    --text-dim: #93a0c0;
    --urgent: #ff5b6e;
    --refer: #ffb84d;
    --follow: #6fc3ff;
    --home: #6fe0a0;
    --radius: 16px;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: radial-gradient(1200px 800px at 20% -10%, #1a2440 0%, var(--bg) 55%);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    padding: 18px 24px;
    border-bottom: 1px solid #232d47;
    background: rgba(15, 20, 32, 0.85);
    backdrop-filter: blur(6px);
    position: sticky;
    top: 0;
    z-index: 10;
  }
  header h1 {
    margin: 0;
    font-size: 20px;
    letter-spacing: 0.3px;
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    display: inline-block;
  }
  .disclaimer {
    margin: 4px 0 0;
    font-size: 12.5px;
    color: var(--text-dim);
    font-weight: 600;
    letter-spacing: 0.2px;
  }
  main {
    flex: 1;
    display: flex;
    justify-content: center;
    padding: 24px 16px 120px;
  }
  .chat {
    width: 100%;
    max-width: 640px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .bubble {
    max-width: 88%;
    padding: 13px 16px;
    border-radius: var(--radius);
    line-height: 1.5;
    font-size: 15px;
    animation: rise 0.25s ease;
  }
  @keyframes rise {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .bubble.assistant {
    background: var(--panel);
    border: 1px solid #263153;
    align-self: flex-start;
    border-bottom-left-radius: 4px;
  }
  .bubble.user {
    background: linear-gradient(135deg, var(--accent), #4468d8);
    align-self: flex-end;
    border-bottom-right-radius: 4px;
    color: white;
  }
  .bubble.answer {
    background: var(--panel-2);
    border: 1px solid #2c3a63;
    align-self: flex-start;
    border-bottom-left-radius: 4px;
    max-width: 92%;
  }
  .urgency-tag {
    display: inline-block;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 4px 10px;
    border-radius: 999px;
    margin-bottom: 10px;
  }
  .urgency-urgent_referral { background: rgba(255,91,110,0.15); color: var(--urgent); border: 1px solid rgba(255,91,110,0.4); }
  .urgency-refer_soon { background: rgba(255,184,77,0.15); color: var(--refer); border: 1px solid rgba(255,184,77,0.4); }
  .urgency-follow_up { background: rgba(111,195,255,0.15); color: var(--follow); border: 1px solid rgba(111,195,255,0.4); }
  .urgency-home_care { background: rgba(111,224,160,0.15); color: var(--home); border: 1px solid rgba(111,224,160,0.4); }
  .urgency-no_classification { background: rgba(147,160,192,0.15); color: var(--text-dim); border: 1px solid rgba(147,160,192,0.4); }

  .choices {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-self: flex-start;
    max-width: 92%;
  }
  .chip {
    padding: 9px 15px;
    border-radius: 999px;
    border: 1px solid #2c3a63;
    background: var(--panel);
    color: var(--text);
    cursor: pointer;
    font-size: 14px;
    transition: all 0.15s ease;
    user-select: none;
  }
  .chip:hover { border-color: var(--accent); background: #1c2440; }
  .chip.selected { background: var(--accent); border-color: var(--accent); color: white; }
  .chip.primary { background: var(--accent); border-color: var(--accent); color: white; }
  .chip.primary:hover { filter: brightness(1.1); }

  .input-row {
    display: flex;
    gap: 8px;
    align-self: flex-start;
    max-width: 92%;
    width: 100%;
  }
  .input-row input, .input-row select {
    flex: 1;
    padding: 11px 14px;
    border-radius: 12px;
    border: 1px solid #2c3a63;
    background: var(--panel);
    color: var(--text);
    font-size: 15px;
  }
  .input-row button {
    padding: 11px 18px;
    border-radius: 12px;
    border: none;
    background: var(--accent);
    color: white;
    font-weight: 600;
    cursor: pointer;
  }

  .spinner-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    align-self: flex-start;
    color: var(--text-dim);
    font-size: 14px;
    padding: 6px 4px;
  }
  .spinner {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 3px solid #2c3a63;
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .restart-row { align-self: center; margin-top: 10px; }
  .restart-btn {
    padding: 9px 18px;
    border-radius: 999px;
    border: 1px solid #2c3a63;
    background: transparent;
    color: var(--text-dim);
    cursor: pointer;
    font-size: 13px;
  }
  .restart-btn:hover { color: var(--text); border-color: var(--accent); }

  .llm-note {
    margin-top: 10px;
    font-size: 11.5px;
    color: var(--text-dim);
  }

  .mic-btn, .speak-btn {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: 1px solid #2c3a63;
    background: var(--panel);
    color: var(--text);
    cursor: pointer;
    font-size: 17px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.15s ease;
  }
  .mic-btn:hover, .speak-btn:hover { border-color: var(--accent); }
  .mic-btn.recording {
    background: var(--urgent);
    border-color: var(--urgent);
    animation: pulse 1s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,91,110,0.5); }
    50% { box-shadow: 0 0 0 8px rgba(255,91,110,0); }
  }
  .speak-btn {
    width: auto;
    height: auto;
    border-radius: 999px;
    padding: 8px 16px;
    font-size: 13px;
    gap: 6px;
    margin-top: 10px;
  }
  .voice-error {
    font-size: 12px;
    color: var(--refer);
    margin-top: 6px;
    align-self: flex-start;
  }
</style>
</head>
<body>
<header>
  <h1>Gidion</h1>
  <p class="disclaimer">{{ disclaimer }}</p>
</header>
<main>
  <div class="chat" id="chat"></div>
</main>

<script>
const chat = document.getElementById('chat');
const answers = {};
const VOICE_ENABLED = {{ 'true' if voice_enabled else 'false' }};
const INTRO_TEXT = {{ intro_text|tojson }};

function scrollDown() { window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); }

// Shared by the intro button and the final "Play answer" button — one
// code path for turning text into audio and playing it, so both use
// exactly the same (cloned-voice, if configured) pipeline.
async function speakText(text, btnEl, idleLabel) {
  const original = btnEl.textContent;
  btnEl.textContent = 'Loading...';
  try {
    const res = await fetch('/api/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      const err = await res.json();
      btnEl.textContent = err.error || 'Voice output unavailable';
      return;
    }
    const audioBlob = await res.blob();
    const audio = new Audio(URL.createObjectURL(audioBlob));
    btnEl.textContent = idleLabel || original;
    audio.play();
  } catch (err) {
    btnEl.textContent = 'Voice output unavailable';
  }
}

function scrollDown() { window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); }

function addBubble(text, cls) {
  const el = document.createElement('div');
  el.className = 'bubble ' + cls;
  el.textContent = text;
  chat.appendChild(el);
  scrollDown();
  return el;
}

function addSpinner(label) {
  const el = document.createElement('div');
  el.className = 'spinner-wrap';
  el.innerHTML = '<div class="spinner"></div><span>' + label + '</span>';
  chat.appendChild(el);
  scrollDown();
  return el;
}

function clearInputArea() {
  const existing = document.querySelectorAll('.step-io, .voice-error');
  existing.forEach(e => e.remove());
}

// ---- Voice input: record -> upload -> transcript -> match onto the
// currently active question. The transcript NEVER goes to the LLM or
// gets treated as a free-form clinical question — it only fills in
// whichever structured field is currently being asked about. ----

let mediaRecorder = null;
let recordedChunks = [];

async function toggleRecording(micBtn, onTranscript) {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordedChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data); };
    mediaRecorder.onstop = async () => {
      micBtn.classList.remove('recording');
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(recordedChunks, { type: 'audio/webm' });
      const spinner = addSpinner('Transcribing...');
      try {
        const formData = new FormData();
        formData.append('audio', blob, 'recording.webm');
        const res = await fetch('/api/transcribe', { method: 'POST', body: formData });
        const data = await res.json();
        spinner.remove();
        if (data.error) {
          const errEl = document.createElement('div');
          errEl.className = 'voice-error';
          errEl.textContent = data.error;
          micBtn.parentElement.appendChild(errEl);
          return;
        }
        onTranscript(data.text);
      } catch (err) {
        spinner.remove();
      }
    };
    mediaRecorder.start();
    micBtn.classList.add('recording');
  } catch (err) {
    const errEl = document.createElement('div');
    errEl.className = 'voice-error';
    errEl.textContent = 'Microphone access denied or unavailable.';
    micBtn.parentElement.appendChild(errEl);
  }
}

function addMicButton(container, onTranscript) {
  if (!VOICE_ENABLED) return;
  const btn = document.createElement('div');
  btn.className = 'mic-btn';
  btn.textContent = '\u{1F3A4}';
  btn.title = 'Tap to speak your answer';
  btn.onclick = () => toggleRecording(btn, onTranscript);
  container.appendChild(btn);
}

function applyVoiceTranscript(step, container, transcript) {
  const lower = transcript.toLowerCase();

  if (step.render) {
    // Numeric steps: pull the first number out of the transcript.
    const match = lower.match(/\d+/);
    const input = container.querySelector('input');
    if (match && input) input.value = match[0];
    return;
  }
  if (step.yesNo) {
    const yesLike = /\byes\b|\byeah\b|\bcorrect\b|\bpresent\b/.test(lower);
    const noLike = /\bno\b|\bnope\b|\bnot\b|\babsent\b/.test(lower);
    const chips = container.querySelectorAll('.chip');
    if (yesLike && !noLike) chips[0].click();
    else if (noLike) chips[1].click();
    return;
  }
  if (step.choiceButtons) {
    step.options.forEach(([val, label], i) => {
      if (lower.includes(label.toLowerCase().split(' ')[0])) {
        container.querySelectorAll('.chip')[i].click();
      }
    });
    return;
  }
  if (step.multiChoice) {
    const chips = container.querySelectorAll('.chip:not(.primary)');
    step.options.forEach(([field, label], i) => {
      const keyword = label.toLowerCase().split(' ').slice(0, 2).join(' ');
      if (lower.includes(keyword) || lower.includes(label.toLowerCase())) {
        if (!chips[i].classList.contains('selected')) chips[i].click();
      }
    });
  }
}


const steps = [
  {
    id: 'age',
    ask: "How old is the child, in months?",
    render(container, onDone) {
      const row = document.createElement('div');
      row.className = 'input-row';
      row.innerHTML = '<input type="number" min="0" max="59" id="age_input" placeholder="e.g. 24"><button id="age_btn">Next</button>';
      container.appendChild(row);
      const submit = () => {
        const v = document.getElementById('age_input').value;
        if (!v) return;
        onDone({ age_months: parseInt(v, 10) }, v + ' months');
      };
      document.getElementById('age_btn').onclick = submit;
      document.getElementById('age_input').addEventListener('keydown', e => { if (e.key === 'Enter') submit(); });
    }
  },
  {
    id: 'danger_signs',
    ask: "Does the child have any general danger signs? Select any that apply, or Continue if none.",
    multiChoice: true,
    options: [
      ['unable_to_drink', 'Unable to drink or breastfeed'],
      ['vomits_everything', 'Vomits everything'],
      ['convulsions_history', 'History of convulsions'],
      ['lethargic_or_unconscious', 'Lethargic or unconscious'],
      ['convulsing_now', 'Convulsing now'],
    ],
  },
  {
    id: 'cough_yn',
    ask: "Does the child have a cough or difficult breathing?",
    yesNo: true,
    field: 'cough',
  },
  {
    id: 'cough_details',
    ask: "Any of the following present?",
    multiChoice: true,
    condition: () => answers.cough === true,
    options: [
      ['fast_breathing', 'Fast breathing for age'],
      ['chest_indrawing', 'Chest indrawing'],
      ['stridor', 'Stridor'],
      ['wheeze', 'Wheeze'],
    ],
  },
  {
    id: 'diarrhoea_yn',
    ask: "Does the child have diarrhoea?",
    yesNo: true,
    field: 'diarrhoea',
  },
  {
    id: 'diarrhoea_days',
    ask: "For how many days?",
    condition: () => answers.diarrhoea === true,
    render(container, onDone) {
      const row = document.createElement('div');
      row.className = 'input-row';
      row.innerHTML = '<input type="number" min="0" id="dd_input" placeholder="days"><button id="dd_btn">Next</button>';
      container.appendChild(row);
      const submit = () => {
        const v = document.getElementById('dd_input').value || '0';
        onDone({ diarrhoea_days: parseInt(v, 10) }, v + ' days');
      };
      document.getElementById('dd_btn').onclick = submit;
    }
  },
  {
    id: 'diarrhoea_details',
    ask: "Any of the following present?",
    multiChoice: true,
    condition: () => answers.diarrhoea === true,
    options: [
      ['blood_in_stool', 'Blood in stool'],
      ['sunken_eyes', 'Sunken eyes'],
      ['skin_pinch_very_slow', 'Skin pinch goes back very slowly'],
      ['skin_pinch_slow', 'Skin pinch goes back slowly'],
      ['drinks_eagerly_thirsty', 'Drinks eagerly, thirsty'],
      ['unable_to_drink_or_drinking_poorly', 'Unable to drink / drinking poorly'],
      ['restless_or_irritable', 'Restless or irritable'],
    ],
  },
  {
    id: 'fever_yn',
    ask: "Does the child have a fever?",
    yesNo: true,
    field: 'fever',
  },
  {
    id: 'fever_details',
    ask: "Any of the following present?",
    multiChoice: true,
    condition: () => answers.fever === true,
    options: [
      ['stiff_neck', 'Stiff neck'],
      ['other_fever_source_found', 'Another source of fever found (ear, throat, ARI, etc.)'],
    ],
  },
  {
    id: 'malaria_risk',
    ask: "Is this a high or low malaria-risk area?",
    condition: () => answers.fever === true,
    choiceButtons: true,
    options: [['high', 'High risk'], ['low', 'Low risk']],
    field: 'malaria_risk_area',
  },
  {
    id: 'other_findings',
    ask: "Any other findings? Select any that apply, or Continue if none.",
    multiChoice: true,
    options: [
      ['ear_pain', 'Ear pain'],
      ['tender_swelling_behind_ear', 'Tender swelling behind ear'],
      ['throat_pain', 'Throat pain'],
      ['very_low_weight_for_age', 'Very low weight for age'],
      ['visible_severe_wasting', 'Visible severe wasting'],
    ],
  },
];

let stepIndex = 0;

function askStep() {
  const step = steps[stepIndex];
  if (!step) { finish(); return; }
  if (step.condition && !step.condition()) { stepIndex++; askStep(); return; }

  addBubble(step.ask, 'assistant');
  const container = document.createElement('div');
  container.classList.add('step-io');
  chat.appendChild(container);

  if (step.render) {
    container.style.display = 'flex';
    container.style.alignItems = 'center';
    container.style.gap = '8px';
    step.render(container, (fields, displayText) => {
      Object.assign(answers, fields);
      clearInputArea();
      addBubble(displayText, 'user');
      stepIndex++;
      askStep();
    });
    addMicButton(container, transcript => applyVoiceTranscript(step, container, transcript));
    return;
  }

  if (step.yesNo) {
    container.classList.add('choices');
    ['Yes', 'No'].forEach(label => {
      const chip = document.createElement('div');
      chip.className = 'chip';
      chip.textContent = label;
      chip.onclick = () => {
        const value = label === 'Yes';
        answers[step.field] = value;
        clearInputArea();
        addBubble(label, 'user');
        stepIndex++;
        askStep();
      };
      container.appendChild(chip);
    });
    addMicButton(container, transcript => applyVoiceTranscript(step, container, transcript));
    return;
  }

  if (step.choiceButtons) {
    container.classList.add('choices');
    step.options.forEach(([val, label]) => {
      const chip = document.createElement('div');
      chip.className = 'chip';
      chip.textContent = label;
      chip.onclick = () => {
        answers[step.field] = val;
        clearInputArea();
        addBubble(label, 'user');
        stepIndex++;
        askStep();
      };
      container.appendChild(chip);
    });
    addMicButton(container, transcript => applyVoiceTranscript(step, container, transcript));
    return;
  }

  if (step.multiChoice) {
    container.classList.add('choices');
    const selected = new Set();
    step.options.forEach(([field, label]) => {
      const chip = document.createElement('div');
      chip.className = 'chip';
      chip.textContent = label;
      chip.onclick = () => {
        if (selected.has(field)) { selected.delete(field); chip.classList.remove('selected'); }
        else { selected.add(field); chip.classList.add('selected'); }
      };
      container.appendChild(chip);
    });
    const cont = document.createElement('div');
    cont.className = 'chip primary';
    cont.textContent = 'Continue';
    cont.onclick = () => {
      step.options.forEach(([field]) => { answers[field] = selected.has(field); });
      clearInputArea();
      const chosen = step.options.filter(([f]) => selected.has(f)).map(([, l]) => l);
      addBubble(chosen.length ? chosen.join(', ') : 'None', 'user');
      stepIndex++;
      askStep();
    };
    container.appendChild(cont);
    addMicButton(container, transcript => applyVoiceTranscript(step, container, transcript));
    return;
  }
}

async function finish() {
  const spinner = addSpinner('Working out the assessment...');
  try {
    const res = await fetch('/api/assess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(answers),
    });
    const data = await res.json();
    spinner.remove();

    const answerBubble = document.createElement('div');
    answerBubble.className = 'bubble answer';
    const tag = document.createElement('div');
    tag.className = 'urgency-tag urgency-' + data.urgency;
    tag.textContent = data.urgency_label || data.urgency;
    answerBubble.appendChild(tag);
    const noteEl = document.createElement('div');
    noteEl.textContent = data.note;
    answerBubble.appendChild(noteEl);
    if (!data.used_llm) {
      const note = document.createElement('div');
      note.className = 'llm-note';
      note.textContent = 'Rule-based phrasing (language model not loaded).';
      answerBubble.appendChild(note);
    }
    chat.appendChild(answerBubble);
    scrollDown();

    if (VOICE_ENABLED) {
      const speakBtn = document.createElement('div');
      speakBtn.className = 'speak-btn';
      speakBtn.style.display = 'inline-flex';
      speakBtn.textContent = '\u{1F50A} Play answer';
      speakBtn.onclick = () => speakText(data.note, speakBtn, '\u{1F50A} Play answer');
      answerBubble.appendChild(speakBtn);
    }

    const restartRow = document.createElement('div');
    restartRow.className = 'restart-row';
    const restartBtn = document.createElement('button');
    restartBtn.className = 'restart-btn';
    restartBtn.textContent = 'Start a new assessment';
    restartBtn.onclick = () => location.reload();
    restartRow.appendChild(restartBtn);
    chat.appendChild(restartRow);
    scrollDown();
  } catch (err) {
    spinner.remove();
    addBubble('Something went wrong reaching Gidion. Please try again.', 'assistant');
  }
}

addBubble("Hi, I'll ask a few structured questions to help triage this visit.", 'assistant');
if (VOICE_ENABLED) {
  const introRow = document.createElement('div');
  introRow.className = 'choices';
  const introBtn = document.createElement('div');
  introBtn.className = 'speak-btn';
  introBtn.style.display = 'inline-flex';
  introBtn.textContent = '\u{1F50A} Hear Gidion introduce itself';
  introBtn.onclick = () => speakText(INTRO_TEXT, introBtn, '\u{1F50A} Hear Gidion introduce itself');
  introRow.appendChild(introBtn);
  chat.appendChild(introRow);
}
askStep();
</script>
</body>
</html>
"""