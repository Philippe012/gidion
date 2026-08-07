import json
import re 
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from app.core.session.manager import SessionManager
from app.core.conversation.extractor import ClinicalExtractor, FactProposal
from app.core.conversation.intent import IntentDetector, Intent
from app.core.llm.model_wrapper import LocalModel, ModelUnavailableError
from app.core.data.visit import Visit, Assessment
from app.core.rules.imci_child import assess as imci_assess


@dataclass
class ConversationResult:
    reply_text: str
    pending_confirmations: list = field(default_factory=list)
    assessment: Optional[Dict] = None
    urgency: str = "normal"
    audio_url: Optional[str] = None
    auto_listen: bool = False


class ConversationManager:
    """
    The central hub. Routes every user message to the right brain.
    """
    
    def __init__(self):
        self.llm = None
        self.extractor = None
        self.intent_detector = IntentDetector()
        self.session_manager = SessionManager()
        self._llm_available = False
        self._init_llm()
    
    def _init_llm(self):
        """Lazy-init LLM. If unavailable, rules engine still works."""
        try:
            self.llm = LocalModel()
            self.llm._ensure_loaded()
            self.extractor = ClinicalExtractor(self.llm)
            self._llm_available = True
            print("[Gidion] LLM loaded successfully.")
        except ModelUnavailableError as e:
            print(f"[Gidion] LLM not available: {e}")
            print("[Gidion] Running in rules-only mode. Responses will be basic.")
            self._llm_available = False
    
    def handle_message(self, session_id: str, text: str) -> ConversationResult:
        """Process one user message through the three-brain pipeline."""
        
        # Load or create session
        state = self.session_manager.load_session(session_id)
        if state is None:
            state = self.session_manager.create_session(protocol="imci_child")
            session_id = state.session_id
        
        # Save user message
        self.session_manager.add_message(session_id, "user", text)
        
        # Detect intent (fast, no LLM)
        intent = self.intent_detector.detect(text)
        
        # Route to appropriate brain
        if intent == Intent.CLINICAL_INFO:
            return self._clinical_brain(session_id, state, text)
        elif intent == Intent.QUESTION:
            return self._knowledge_brain(session_id, state, text)
        else:
            return self._conversation_brain(session_id, state, text, intent)
    
    def _clinical_brain(self, session_id: str, state, text: str) -> ConversationResult:
        """
        Clinical Brain:
        1. Extract facts (LLM or keyword fallback)
        2. Save confirmed facts
        3. Build Visit -> Run rules engine
        4. If urgent: instant emergency response
        5. If not urgent: LLM generates natural response
        """
        
        # 1. Extract facts
        proposals = []
        if self._llm_available and self.extractor:
            try:
                proposals = self.extractor.extract(text, state.facts)
            except Exception as e:
                print(f"[Manager] LLM extractor crashed: {e}")
                print("[Manager] Falling back to keyword extraction.")
                proposals = []
        
        if not proposals:
            proposals = self._keyword_extract(text)
        
        # 2. Confirm and save facts
        pending = []
        for prop in proposals:
            if prop.confidence >= 0.80:
                self.session_manager.add_fact(
                    session_id, prop.field_name, prop.value,
                    confidence=prop.confidence, source="llm_extraction"
                )
            elif prop.confidence >= 0.45:
                pending.append({
                    "field": prop.field_name,
                    "value": str(prop.value),
                    "confidence": round(prop.confidence, 2)
                })
        
        # Reload state with new facts
        state = self.session_manager.load_session(session_id)
        
        # 3. Build Visit and run rules engine
        try:
            visit = self._build_visit(state.facts)
            assessment = imci_assess(visit)
        except Exception as e:
            print(f"[Rules Engine Error] {e}")
            reply = "I had trouble processing the clinical information. Please tell me more about the symptoms."
            self.session_manager.add_message(session_id, "assistant", reply)
            return ConversationResult(reply_text=reply, urgency="normal")
        
        # Save assessment to DB
        self.session_manager.save_assessment(session_id, assessment)
        
        # 4. Check for danger signs / urgent referral
        danger = getattr(assessment, 'danger_sign_present', False)
        action_level = getattr(assessment, 'overall_action_level', 0)
        
        if danger or action_level >= 3:
            reply = self._emergency_response(assessment)
            self.session_manager.add_message(session_id, "assistant", reply)
            return ConversationResult(
                reply_text=reply,
                assessment=self._assessment_to_dict(assessment),
                urgency="critical"
            )
        
        # 5. Generate natural clinical response
        reply = self._generate_clinical_reply(state, assessment, pending)
        self.session_manager.add_message(session_id, "assistant", reply)
        
        urgency = "normal"
        if action_level == 2:
            urgency = "moderate"
        elif action_level == 1:
            urgency = "mild"
        
        return ConversationResult(
            reply_text=reply,
            pending_confirmations=pending,
            assessment=self._assessment_to_dict(assessment),
            urgency=urgency
        )
    
    def _knowledge_brain(self, session_id: str, state, text: str) -> ConversationResult:
        """Answer medical questions. If LLM unavailable, give generic response."""
        
        if not self._llm_available:
            reply = "I'm not able to answer detailed questions right now. Please consult a healthcare professional."
            self.session_manager.add_message(session_id, "assistant", reply)
            return ConversationResult(reply_text=reply, urgency="normal")
        
        prompt = f"""You are Gidion, a clinical assistant. Answer the user's question in plain text only.

        User question: {text}

        Instructions:
        - Be accurate and brief (2-3 sentences)
        - If unsure, say so honestly
        - Never make up medical facts
        - Do not include any labels such as "Answer:", "assistant:", or "user:"
        - Please consult a healthcare professional for personalized advice.
        """
        
        reply = self._safe_llm_call(prompt, max_tokens=250)
        if not reply:
            reply = "I'm not certain about that. Please consult a healthcare professional."
        
        self.session_manager.add_message(session_id, "assistant", reply)
        return ConversationResult(reply_text=reply, urgency="normal")
    
    def _conversation_brain(self, session_id: str, state, text: str, intent: Intent) -> ConversationResult:
        """Natural dialogue: greetings, chitchat, clarification, goodbye."""
        
        if intent == Intent.FINISH:
            return self._handle_finish(session_id, state)
        
        if not self._llm_available:
            if intent == Intent.GREETING:
                reply = "Hello. Please tell me the patient's symptoms."
                self.session_manager.add_message(session_id, "assistant", reply)
                return ConversationResult(reply_text=reply, urgency="normal")
        
        # Build compact conversation context
        recent = state.conversation_history[-4:]
        convo = "\n".join([
            f"{'User' if m.get('role')=='user' else 'Gidion'}: {m.get('text','')[:80]}"
            for m in recent
        ])
        
        if intent == Intent.GREETING:
            system = "You are Gidion, a warm clinical assistant. Greet naturally. If first interaction, introduce yourself briefly and ask what symptoms to discuss."
        elif intent == Intent.CLARIFICATION:
            system = "You are Gidion. Briefly explain that you ask questions to provide better clinical guidance. Reassure the user."
        else:
            system = "You are Gidion, a friendly clinical assistant. Respond naturally. Guide back to clinical discussion if needed."
        
        prompt = f"""{system}

        Recent conversation:
        {convo}

        Incoming message:
        {text}

        Reply in one brief sentence, with no greetings or role labels."""
        
        reply = self._safe_llm_call(prompt, max_tokens=120, temperature=0.5)
        if not reply:
            reply = "I'm here to help. What symptoms can you tell me about?"
        
        self.session_manager.add_message(session_id, "assistant", reply)
        return ConversationResult(reply_text=reply, urgency="normal")
    
    def _handle_finish(self, session_id: str, state) -> ConversationResult:
        """Generate summary and close session."""
        
        facts_summary = "\n".join([f"• {k}: {v}" for k, v in state.facts.items()]) or "No symptoms recorded."
        
        if self._llm_available:
            prompt = f"""You are Gidion. The user is ending the conversation. Provide a warm closing summary.

Patient information:
{facts_summary}

Remind them to consult a healthcare professional. Wish them well. Keep to 2-3 sentences."""
            reply = self._safe_llm_call(prompt, max_tokens=150)
        else:
            reply = f"Thank you.\n\nSummary:\n{facts_summary}\n\nPlease consult a healthcare professional."
        
        if not reply:
            reply = "Thank you for sharing that information. Please consult a healthcare professional for a proper diagnosis. Take care!"
        
        self.session_manager.complete_session(session_id)
        self.session_manager.add_message(session_id, "assistant", reply)
        return ConversationResult(reply_text=reply, urgency="complete")
    
    def _generate_clinical_reply(self, state, assessment, pending) -> str:
        """Generate natural clinical response. One LLM call with full context."""
        
        if not self._llm_available:
            results = getattr(assessment, 'results', [])
            if results:
                top = max(results, key=lambda r: getattr(r, 'action_level', 0))
                return f"{getattr(top, 'classification', 'Unknown').replace('_', ' ').title()}: {getattr(top, 'action', 'See a doctor.')}"
            return "Tell me more about what you're observing."
        
        facts_text = "\n".join([f"• {k}: {v}" for k, v in state.facts.items()]) or "No facts yet."
        
        pending_text = ""
        if pending:
            pending_text = "\nPending confirmation:\n" + "\n".join([
                f"• {p['field']} = {p['value']} ({p['confidence']:.0%} confident)"
                for p in pending
            ])
        
        assessment_text = ""
        results = getattr(assessment, 'results', [])
        if results:
            for r in results:
                classification = getattr(r, 'classification', 'Unknown')
                action = getattr(r, 'action', '')
                assessment_text += f"\n- {classification.replace('_', ' ').title()}: {action}"
        else:
            assessment_text = "No classification triggered yet."
        
        recent = state.conversation_history[-3:]
        convo = "\n".join([
            f"{'User' if m.get('role')=='user' else 'Gidion'}: {m.get('text','')[:60]}"
            for m in recent
        ])
        
        prompt = f"""You are Gidion, a clinical triage assistant helping a health worker in Rwanda.

Patient information:
{facts_text}{pending_text}

Clinical assessment:
{assessment_text}

Recent conversation:
{convo}

Instructions:
- Respond warmly and professionally (1-3 sentences)
- Acknowledge what the health worker shared
- Ask ONE focused follow-up question about the most important missing information
- OR give brief reassurance/guidance if you have enough information
- Do NOT diagnose. Do NOT prescribe medication.
- If assessment shows urgent referral needed, emphasize urgency calmly but firmly

Gidion:"""
        
        reply = self._safe_llm_call(prompt, max_tokens=180, temperature=0.3)
        return reply or "Tell me more about what you're observing."
    
    def _emergency_response(self, assessment) -> str:
        """Instant emergency message. No LLM — speed matters for danger signs."""
        
        results = getattr(assessment, 'results', [])
        if results:
            top = max(results, key=lambda r: getattr(r, 'action_level', 0))
            classification = getattr(top, 'classification', 'Emergency').replace("_", " ").title()
            action = getattr(top, 'action', 'Refer urgently to hospital.')
        else:
            classification = "Emergency"
            action = "Refer urgently to hospital."
        
        return (
            f"🚨 URGENT: {classification}. {action} "
            f"Do not wait — this requires immediate professional care. "
            f"Use the fastest transport available."
        )
    
    def _build_visit(self, facts: Dict[str, Any]) -> Visit:
        """Build a Visit object from extracted facts."""
        kwargs = {
            "age_months": 0,
            "unable_to_drink": False,
            "vomits_everything": False,
            "convulsions_history": False,
            "lethargic_or_unconscious": False,
            "convulsing_now": False,
            "cough": False,
            "cough_days": 0,
            "fast_breathing": False,
            "chest_indrawing": False,
            "stridor": False,
            "wheeze": False,
            "diarrhoea": False,
            "diarrhoea_days": 0,
            "blood_in_stool": False,
            "restless_or_irritable": False,
            "sunken_eyes": False,
            "drinks_eagerly_thirsty": False,
            "unable_to_drink_or_drinking_poorly": False,
            "skin_pinch_slow": False,
            "skin_pinch_very_slow": False,
            "fever": False,
            "fever_days": 0,
            "stiff_neck": False,
            "malaria_risk_area": "low",
            "other_fever_source_found": False,
            "measles_now_or_recent": False,
            "clouded_cornea": False,
            "deep_mouth_ulcers": False,
            "eye_infection_or_small_mouth_ulcers": False,
            "ear_pain": False,
            "ear_pus_discharge": False,
            "ear_pus_days": 0,
            "tender_swelling_behind_ear": False,
            "throat_pain": False,
            "red_throat_or_exudate": False,
            "tender_neck_lymph_nodes": False,
            "visible_severe_wasting": False,
            "bilateral_oedema": False,
            "very_low_weight_for_age": False,
            "palmar_pallor": "none",
            "vitamin_a_last_6_months": True,
            "dewormed_last_6_months": True,
        }
        
        for k, v in facts.items():
            if k in kwargs:
                kwargs[k] = v
        
        return Visit(**kwargs)
    
    def _keyword_extract(self, text: str) -> list:
        """Fallback fact extraction when LLM unavailable. Simple keyword matching."""
        proposals = []
        text_lower = text.lower()
        
        # Age extraction
        age_match = None
        for pattern in [r'(\d+)\s*months?', r'(\d+)\s*mo', r'(\d+)\s*month']:
            m = re.search(pattern, text_lower)
            if m:
                age_match = int(m.group(1))
                break
        if age_match is None:
            for pattern in [r'(\d+)\s*years?', r'(\d+)\s*yr']:
                m = re.search(pattern, text_lower)
                if m:
                    age_match = int(m.group(1)) * 12
                    break
        if age_match is not None:
            proposals.append(FactProposal("age_months", age_match, 0.9))
        
        # Simple keyword matching for symptoms
        keywords = {
            "fever": "fever", "hot": "fever", "burning up": "fever",
            "cough": "cough", "coughing": "cough",
            "diarrhea": "diarrhoea", "diarrhoea": "diarrhoea", "loose stool": "diarrhoea",
            "vomiting": "vomits_everything", "throwing up": "vomits_everything",
            "can't drink": "unable_to_drink", "not drinking": "unable_to_drink",
            "convulsion": "convulsions_history", "seizure": "convulsions_history", "fit": "convulsions_history",
            "unconscious": "lethargic_or_unconscious", "not responding": "lethargic_or_unconscious",
            "sleepy": "lethargic_or_unconscious", "lethargic": "lethargic_or_unconscious",
            "fast breathing": "fast_breathing", "breathing fast": "fast_breathing",
            "chest indrawing": "chest_indrawing", "chest pulls in": "chest_indrawing",
            "stridor": "stridor", "noisy breathing": "stridor",
            "wheeze": "wheeze", "wheezing": "wheeze",
            "blood in stool": "blood_in_stool", "bloody stool": "blood_in_stool",
            "sunken eyes": "sunken_eyes",
            "stiff neck": "stiff_neck",
            "ear pain": "ear_pain", "earache": "ear_pain",
            "ear discharge": "ear_pus_discharge", "pus from ear": "ear_pus_discharge",
            "swelling behind ear": "tender_swelling_behind_ear",
            "sore throat": "throat_pain", "throat pain": "throat_pain",
            "red throat": "red_throat_or_exudate",
            "swollen feet": "bilateral_oedema", "oedema": "bilateral_oedema",
            "wasting": "visible_severe_wasting",
            "low weight": "very_low_weight_for_age",
        }
        
        for keyword, field in keywords.items():
            if keyword in text_lower:
                negated = False
                for neg in ["no ", "not ", "doesn't ", "no ", "without "]:
                    if neg + keyword in text_lower or "not have " + keyword in text_lower:
                        negated = True
                        break
                if not negated:
                    proposals.append(FactProposal(field, True, 0.7))
        
        return proposals
    
    def _safe_llm_call(self, prompt: str, max_tokens: int = 200, temperature: float = 0.3) -> str:
        """Safe LLM call with error handling and prompt truncation."""
        if not self._llm_available or not self.llm:
            return ""
        
        try:
            if len(prompt) > 3500:
                prompt = prompt[:3500] + "\n...[truncated]\n"
            
            return self.llm.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        except Exception as e:
            print(f"[LLM] Generation error: {e}")
            return ""
    
    def _assessment_to_dict(self, assessment) -> Dict:
        """Convert Assessment to serializable dict."""
        return {
            "overall_urgency": getattr(assessment, 'overall_urgency', 'no_classification'),
            "overall_action_level": getattr(assessment, 'overall_action_level', 0),
            "danger_sign_present": getattr(assessment, 'danger_sign_present', False),
            "classifications": [
                {
                    "category": getattr(r, 'category', ''),
                    "classification": getattr(r, 'classification', ''),
                    "action": getattr(r, 'action', ''),
                    "action_level": getattr(r, 'action_level', 0)
                }
                for r in getattr(assessment, 'results', [])
            ],
            "routine_reminders": getattr(assessment, 'routine_reminders', [])
        }
    
    def create_session(self) -> str:
        """Create new session and return ID."""
        state = self.session_manager.create_session()
        return state.session_id