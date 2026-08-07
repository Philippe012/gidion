import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app import config


class Database:
    """Simple JSON file storage. In-memory with disk persistence."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance
    
    def _init_db(self):
        # Save as .json next to where the old .db was
        self.db_path = Path(config.STORAGE_DB_PATH).with_suffix('.json')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory data stores
        self.sessions: Dict[str, Dict] = {}
        self.messages: Dict[str, List[Dict]] = {}      # session_id -> list of messages
        self.facts: Dict[str, Dict[str, Dict]] = {}    # session_id -> {field: fact_record}
        self.assessments: Dict[str, List[Dict]] = {}   # session_id -> list of assessments
        
        self._load()
    
    def _load(self):
        """Load from JSON file if it exists."""
        if not self.db_path.exists():
            return
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.sessions = data.get('sessions', {})
            self.messages = data.get('messages', {})
            self.facts = data.get('facts', {})
            self.assessments = data.get('assessments', {})
        except Exception as e:
            print(f"[Storage] Warning: could not load {self.db_path}: {e}")
            print("[Storage] Starting with empty database.")
    
    def _save(self):
        """Persist memory to JSON file."""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'sessions': self.sessions,
                    'messages': self.messages,
                    'facts': self.facts,
                    'assessments': self.assessments
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"[Storage] Warning: could not save: {e}")
    
    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------
    def create_session(self, protocol: str = "imci_child", 
                       patient_name: str = None,
                       chw_id: str = None) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        self.sessions[session_id] = {
            'id': session_id,
            'created_at': now,
            'updated_at': now,
            'active_protocol': protocol,
            'status': 'active',
            'patient_name': patient_name,
            'patient_age_months': None,
            'chw_id': chw_id,
            'location': None,
            'completed_at': None
        }
        self.messages[session_id] = []
        self.facts[session_id] = {}
        self.assessments[session_id] = []
        
        self._save()
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, **kwargs) -> None:
        if session_id not in self.sessions:
            return
        
        allowed = {"status", "patient_name", "patient_age_months", "chw_id", 
                   "location", "completed_at", "active_protocol"}
        for k, v in kwargs.items():
            if k in allowed:
                self.sessions[session_id][k] = v
        
        self.sessions[session_id]['updated_at'] = datetime.now().isoformat()
        self._save()
    
    # ------------------------------------------------------------------
    # Messages (conversation history)
    # ------------------------------------------------------------------
    def add_message(self, session_id: str, role: str, text: str,
                    intent: str = None, audio_path: str = None) -> int:
        if session_id not in self.messages:
            self.messages[session_id] = []
        
        msg = {
            'id': len(self.messages[session_id]) + 1,
            'session_id': session_id,
            'role': role,
            'text': text,
            'intent': intent,
            'audio_path': audio_path,
            'created_at': datetime.now().isoformat()
        }
        self.messages[session_id].append(msg)
        self._save()
        return msg['id']
    
    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict]:
        msgs = self.messages.get(session_id, [])
        # Return oldest-first, only last 'limit' messages
        if len(msgs) > limit:
            return msgs[-limit:]
        return msgs.copy()
    
    # ------------------------------------------------------------------
    # Facts (extracted clinical data)
    # ------------------------------------------------------------------
    def add_fact(self, session_id: str, field_name: str, value: Any,
                 value_type: str = None, confidence: float = 1.0,
                 confirmed: bool = True, source: str = "llm_extraction") -> int:
        if session_id not in self.facts:
            self.facts[session_id] = {}
        
        if value_type is None:
            if isinstance(value, bool):
                value_type = "bool"
            elif isinstance(value, int):
                value_type = "int"
            elif isinstance(value, float):
                value_type = "float"
            else:
                value_type = "str"
        
        # Store simple values as strings for JSON safety
        stored_value = value if isinstance(value, (list, dict)) else str(value)
        
        self.facts[session_id][field_name] = {
            'field_name': field_name,
            'value': stored_value,
            'value_type': value_type,
            'confidence': confidence,
            'confirmed': confirmed,
            'source': source,
            'set_at': datetime.now().isoformat()
        }
        self._save()
        return 1  # dummy id
    
    def get_facts(self, session_id: str) -> Dict[str, Any]:
        """Return only confirmed facts, cast to proper Python types."""
        result = {}
        for field_name, fact in self.facts.get(session_id, {}).items():
            if not fact.get('confirmed', True):
                continue
            
            value = fact['value']
            vtype = fact.get('value_type', 'str')
            
            if vtype == "bool":
                result[field_name] = str(value).lower() in ("true", "1", "yes")
            elif vtype == "int":
                try:
                    result[field_name] = int(value)
                except (ValueError, TypeError):
                    result[field_name] = value
            elif vtype == "float":
                try:
                    result[field_name] = float(value)
                except (ValueError, TypeError):
                    result[field_name] = value
            else:
                result[field_name] = value
        return result
    
    # ------------------------------------------------------------------
    # Assessments (rules engine output)
    # ------------------------------------------------------------------
    def save_assessment(self, session_id: str, assessment) -> int:
        # Convert assessment object to plain dict for JSON
        results = getattr(assessment, 'results', [])
        results_list = []
        for r in results:
            if hasattr(r, '__dict__'):
                results_list.append(r.__dict__)
            elif isinstance(r, dict):
                results_list.append(r)
            else:
                results_list.append({"repr": str(r)})
        
        assessment_data = {
            'id': len(self.assessments.get(session_id, [])) + 1,
            'session_id': session_id,
            'overall_urgency': getattr(assessment, 'overall_urgency', 'no_classification'),
            'overall_action_level': getattr(assessment, 'overall_action_level', 0),
            'danger_sign_present': getattr(assessment, 'danger_sign_present', False),
            'results_json': results_list,
            'routine_reminders_json': getattr(assessment, 'routine_reminders', []),
            'assessed_at': datetime.now().isoformat()
        }
        
        if session_id not in self.assessments:
            self.assessments[session_id] = []
        
        self.assessments[session_id].append(assessment_data)
        self._save()
        return assessment_data['id']
    
    def get_latest_assessment(self, session_id: str) -> Optional[Dict]:
        assessments = self.assessments.get(session_id, [])
        return assessments[-1] if assessments else None
    
    def close(self):
        self._save()


# Global singleton — same interface as before
db = Database()