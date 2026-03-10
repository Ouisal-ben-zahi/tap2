"""
Agent intelligent de matching Offres / Candidats.

- Embeddings sémantiques (sentence-transformers)
- Pipeline : filtre → similarité → rank → top N
- Justification LLM (score /100, forces, manques)
- Feedback recruteur (bonus/pénalité)
"""

from A4.agent.config import (
    EMBEDDING_MODEL,
    DEFAULT_TOP_N,
    FEEDBACK_BONUS_SELECTED,
    FEEDBACK_PENALTY_REJECTED,
)
from A4.agent.embeddings import EmbeddingService
from A4.agent.pipeline import MatchingPipeline
from A4.agent.justification import JustificationService
from A4.agent.feedback import FeedbackStore

__all__ = [
    "EmbeddingService",
    "MatchingPipeline",
    "JustificationService",
    "FeedbackStore",
    "EMBEDDING_MODEL",
    "DEFAULT_TOP_N",
    "FEEDBACK_BONUS_SELECTED",
    "FEEDBACK_PENALTY_REJECTED",
]
