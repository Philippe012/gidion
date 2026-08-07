import json
import re
from typing import List, Dict, Any
from dataclasses import dataclass

from app.core.llm.model_wrapper import LocalModel, ModelUnavailableError
from app import config


@dataclass
class FactProposal:
    field_name: str
    value: Any
    confidence: float
    reasoning: str = ""


# ── FIXED: shorter, denser prompt. Small models lose focus after ~20 lines. ──
_EXTRACTION_PROMPT = """You are a clinical information extractor for IMCI.

Extract facts from the user's message. Return ONLY a JSON array.

Fields (exact names):
age_months(int), unable_to_drink(bool), vomits_everything(bool),
convulsions_history(bool), lethargic_or_unconscious(bool), convulsing_now(bool),
cough(bool), cough_days(int), fast_breathing(bool), chest_indrawing(bool),
stridor(bool), wheeze(bool), diarrhoea(bool), diarrhoea_days(int),
blood_in_stool(bool), restless_or_irritable(bool), sunken_eyes(bool),
drinks_eagerly_thirsty(bool), unable_to_drink_or_drinking_poorly(bool),
skin_pinch_slow(bool), skin_pinch_very_slow(bool), fever(bool), fever_days(int),
stiff_neck(bool), malaria_risk_area(str: high/low), other_fever_source_found(bool),
measles_now_or_recent(bool), clouded_cornea(bool), deep_mouth_ulcers(bool),
eye_infection_or_small_mouth_ulcers(bool), ear_pain(bool),
ear_pus_discharge(bool), ear_pus_days(int), tender_swelling_behind_ear(bool),
throat_pain(bool), red_throat_or_exudate(bool), tender_neck_lymph_nodes(bool),
visible_severe_wasting(bool), bilateral_oedema(bool),
very_low_weight_for_age(bool), palmar_pallor(str: none/some/severe)

Rules:
- Return ONLY a JSON array: [{{"field_name":"...","value":...,"confidence":0.0-1.0,"reasoning":"..."}}]
- Infer bool from context (yes/has/is = true; no/not/doesn't = false)
- Convert age to months, durations to days
- Omit anything unclear

Example:
[
  {{"field_name":"fever","value":true,"confidence":0.95,"reasoning":"User said 'has a fever'"}},
  {{"field_name":"fever_days","value":3,"confidence":0.9,"reasoning":"User said 'for 3 days'"}}
]

Known facts so far:
{known_facts}

User message:
{text}

JSON array:"""


class ClinicalExtractor:
    def __init__(self, llm: LocalModel):
        self.llm = llm
    
    def extract(self, text: str, known_facts: Dict[str, Any]) -> List[FactProposal]:
        if not self.llm or getattr(self.llm, 'model', None) is None:
            return []
        
        try:
            # ── FIXED: human-readable known facts, not raw JSON noise ──
            if known_facts:
                known_str = "\n".join(f"- {k}: {v}" for k, v in known_facts.items())
            else:
                known_str = "(none yet)"
            
            # ── FIXED: raw text, NOT json.dumps(text). The quotes and escapes
            #    from json.dumps() were being fed straight into the prompt,
            #    so the model saw:  User message: "my child has a fever"
            #    instead of:        User message: my child has a fever
            prompt = _EXTRACTION_PROMPT.format(
                known_facts=known_str,
                text=text
            )
            
            n_ctx = getattr(config, 'LLM_N_CTX', 2048)
            max_prompt_chars = int((n_ctx - 300) * 3.5)
            if len(prompt) > max_prompt_chars:
                overflow = len(prompt) - max_prompt_chars + 50
                safe_text = text[:max(0, len(text) - overflow)] + "..."
                prompt = _EXTRACTION_PROMPT.format(
                    known_facts=known_str,
                    text=safe_text
                )
            
            # 200 tokens is plenty for a compact JSON array
            response = self.llm.generate(prompt, max_tokens=200, temperature=0.1)
            return self._parse_response(response)
        except Exception as e:
            print(f"[Extractor] Error: {e}")
            return []
    
    def _parse_response(self, text: str) -> List[FactProposal]:
        if not text:
            return []
        
        text = text.strip()
        # Strip markdown fences
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        
        # Try direct parse
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                data = data.get("facts", data.get("result", []))
            if isinstance(data, list):
                return self._to_proposals(data)
        except json.JSONDecodeError:
            pass
        
        # ── FIXED: non-greedy regex so we don't swallow trailing text ──
        try:
            match = re.search(r'\[.*?\]', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if isinstance(data, list):
                    return self._to_proposals(data)
        except Exception as e:
            print(f"[Extractor] Parse error: {e}")
        
        return []
    
    def _to_proposals(self, data: list) -> List[FactProposal]:
        proposals = []
        for item in data:
            if not isinstance(item, dict):
                continue
            val = item.get("value")
            
            if isinstance(val, str):
                v_lower = val.lower()
                if v_lower in ("true", "yes", "1", "y", "present"):
                    val = True
                elif v_lower in ("false", "no", "0", "n", "absent", "none"):
                    val = False
                # ── FIXED: handle negative ints too ──
                elif v_lower.lstrip('-').isdigit():
                    val = int(v_lower)
                else:
                    try:
                        val = float(v_lower)
                    except ValueError:
                        pass
            
            proposals.append(FactProposal(
                field_name=item.get("field_name", ""),
                value=val,
                confidence=float(item.get("confidence", 0.5)),
                reasoning=item.get("reasoning", "")
            ))
        return proposals