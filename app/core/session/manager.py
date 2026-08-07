"""
Patient Session Manager.
Handles session lifecycle and in-memory state.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.session.store import Database, db
from app import config


@dataclass
class PatientState:
    session_id: str
    protocol: str
    facts: Dict[str, Any] = field(default_factory=dict)
    pending_facts: List[Dict] = field(default_factory=list)
    assessment: Optional[Any] = None
    conversation_history: List[Dict] = field(default_factory=list)
    voice_enabled: bool = False
    last_activity: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        return datetime.now() - self.last_activity > timedelta(minutes=getattr(config, 'SESSION_TIMEOUT_MINUTES', 30))
    
    def touch(self):
        self.last_activity = datetime.now()


class SessionManager:
    def __init__(self):
        self.db = db
        self._active_states: Dict[str, PatientState] = {}
    
    def create_session(self, protocol: str = "imci_child", 
                       patient_name: str = None,
                       chw_id: str = None) -> PatientState:
        session_id = self.db.create_session(protocol, patient_name, chw_id)
        
        state = PatientState(
            session_id=session_id,
            protocol=protocol,
            context={"patient_name": patient_name, "chw_id": chw_id}
        )
        self._active_states[session_id] = state
        return state
    
    def load_session(self, session_id: str) -> Optional[PatientState]:
        if session_id in self._active_states:
            state = self._active_states[session_id]
            if not state.is_expired():
                state.touch()
                return state
            del self._active_states[session_id]
        
        session = self.db.get_session(session_id)
        if not session:
            return None
        
        facts = self.db.get_facts(session_id)
        messages = self.db.get_messages(session_id)
        assessment_row = self.db.get_latest_assessment(session_id)
        
        state = PatientState(
            session_id=session_id,
            protocol=session.get("active_protocol", "imci_child"),
            facts=facts,
            assessment=assessment_row,
            conversation_history=messages,
            context={
                "patient_name": session.get("patient_name"),
                "chw_id": session.get("chw_id"),
                "status": session.get("status")
            }
        )
        self._active_states[session_id] = state
        return state
    
    def save_state(self, state: PatientState) -> None:
        state.touch()
        self._active_states[state.session_id] = state
    
    def add_message(self, session_id: str, role: str, text: str,
                    intent: str = None, audio_path: str = None) -> None:
        self.db.add_message(session_id, role, text, intent, audio_path)
        if session_id in self._active_states:
            state = self._active_states[session_id]
            state.conversation_history.append({
                "role": role, "text": text, "intent": intent,
                "created_at": datetime.now().isoformat()
            })
    
    def add_fact(self, session_id: str, field_name: str, value: Any,
                 value_type: str = None, confidence: float = 1.0,
                 confirmed: bool = True, source: str = "llm_extraction") -> None:
        self.db.add_fact(session_id, field_name, value, value_type,
                         confidence, confirmed, source)
        
        if session_id in self._active_states:
            state = self._active_states[session_id]
            if confirmed:
                state.facts[field_name] = value
                state.pending_facts = [
                    f for f in state.pending_facts 
                    if f.get("field_name") != field_name
                ]
            else:
                state.pending_facts.append({
                    "field_name": field_name, "value": value,
                    "value_type": value_type, "confidence": confidence
                })
    
    def save_assessment(self, session_id: str, assessment) -> None:
        self.db.save_assessment(session_id, assessment)
        if session_id in self._active_states:
            self._active_states[session_id].assessment = assessment
    
    def complete_session(self, session_id: str) -> None:
        self.db.update_session(session_id, status="completed", 
                               completed_at=datetime.now().isoformat())
        if session_id in self._active_states:
            self._active_states[session_id].context["status"] = "completed"
    
    def get_or_create_session(self, session_id: str = None) -> PatientState:
        if session_id:
            state = self.load_session(session_id)
            if state:
                return state
        return self.create_session()