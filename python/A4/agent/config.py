"""
Configuration centralisée pour l'agent de matching sémantique.
"""
import os
from typing import Optional

# Modèle sentence-transformers (multilingue, bon pour FR)
EMBEDDING_MODEL = os.environ.get("A4_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

# Dimension des vecteurs (dépend du modèle)
EMBEDDING_DIM: Optional[int] = None  # Rempli au chargement du modèle

# Seuils et limites
MIN_SIMILARITY_THRESHOLD = 0.0   # Seuil minimal pour inclure un candidat (peut être relevé)
DEFAULT_TOP_N = 20
MAX_TOP_N = 100

# Feedback learning
FEEDBACK_BONUS_SELECTED = 0.05   # Bonus si candidat souvent sélectionné
FEEDBACK_PENALTY_REJECTED = 0.05 # Pénalité si candidat souvent rejeté
FEEDBACK_MIN_DECISIONS = 1       # Nombre min de décisions pour appliquer bonus/pénalité

# LLM justification (Google Generative AI par défaut, comme le reste du projet)
# Même variable .env que les autres agents : GOOGLE_MODEL
LLM_PROVIDER = os.environ.get("A4_LLM_PROVIDER", "google")
GEMINI_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
