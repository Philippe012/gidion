"""
Fast intent detection. No LLM for common cases.
"""

from enum import Enum


class Intent(Enum):
    CLINICAL_INFO = "clinical_info"
    QUESTION = "question"
    GREETING = "greeting"
    CHITCHAT = "chitchat"
    CLARIFICATION = "clarification"
    FINISH = "finish"
    UNKNOWN = "unknown"


class IntentDetector:
    def detect(self, text: str) -> Intent:
        text_lower = text.lower().strip()
        
        # Finish
        if any(w in text_lower for w in ["done", "finish", "bye", "goodbye", "that's all", "thank you", "thanks", "ok bye", "see you"]):
            return Intent.FINISH
        
        # Greeting
        if any(w in text_lower for w in ["hello", "hi ", "hey", "good morning", "good afternoon", "good evening", "howdy", "greetings"]):
            return Intent.GREETING
        
        # Clarification
        if any(w in text_lower for w in ["why do you", "why are you", "why ask", "what do you mean", "i don't understand why", "why do you need"]):
            return Intent.CLARIFICATION
        
        # Question
        if text_lower.startswith(("what is", "what are", "how does", "how do", "explain", "tell me about", "what do you know about", "can you explain", "define", "what does", "how is")):
            return Intent.QUESTION
        
        # Chitchat
        if any(w in text_lower for w in ["how are you", "what's up", "nice to meet", "who are you", "what can you do", "what is your name"]):
            return Intent.CHITCHAT
        
        # Default: clinical
        return Intent.CLINICAL_INFO