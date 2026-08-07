"""
Knowledge Retriever — placeholder for FAISS-based document search.
For now, returns empty (knowledge brain uses LLM directly).
Can be enhanced later with sentence-transformers + FAISS.
"""

from typing import List, Dict


class KnowledgeRetriever:
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """Retrieve relevant knowledge chunks. Returns empty for now."""
        return []


_retriever = None

def get_retriever() -> KnowledgeRetriever:
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeRetriever()
    return _retriever