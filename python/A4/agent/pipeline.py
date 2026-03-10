"""
Pipeline de matching sémantique :
  1) Filtrage minimal (domaine, optionnel: compétences critiques)
  2) Similarité vectorielle (cosine)
  3) Classement par score décroissant
  4) Top N
  5) Optionnel : re-ranking avec feedback (bonus/pénalité)
"""
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from A4.agent.config import DEFAULT_TOP_N, MIN_SIMILARITY_THRESHOLD
from A4.agent.embeddings import EmbeddingService
from A4.agent.feedback import FeedbackStore


def _load_job_domaine(job_id: int) -> Optional[str]:
    """Retourne le domaine de l'offre (pour filtrer les candidats). Gère l'absence de colonne."""
    from database.connection import DatabaseConnection
    DatabaseConnection.initialize()
    with DatabaseConnection.get_connection() as db:
        cur = db.cursor(dictionary=True)
        try:
            cur.execute("SELECT domaine_activite, categorie_profil FROM jobs WHERE id = %s", (job_id,))
            row = cur.fetchone()
        except Exception as e:
            if "1054" in str(e) or "Unknown column" in str(e):
                try:
                    cur.execute("SELECT domaine_activite FROM jobs WHERE id = %s", (job_id,))
                    row = cur.fetchone()
                except Exception:
                    row = None
            else:
                row = None
        cur.close()
    if not row:
        return None
    # Priorité à categorie_profil (domaine exact) puis domaine_activite
    v = (row.get("categorie_profil") or row.get("domaine_activite") or "").strip()
    return v if v else None


def _load_candidate_ids_for_domaine(domaine_activite: Optional[str]) -> List[int]:
    """Liste des id candidats du domaine (categorie_profil)."""
    from database.connection import DatabaseConnection
    from candidate_minio_path import normalize_categorie_profil
    DatabaseConnection.initialize()
    categorie = normalize_categorie_profil(domaine_activite or "") if domaine_activite else None
    with DatabaseConnection.get_connection() as db:
        cur = db.cursor()
        if categorie:
            cur.execute("SELECT id FROM candidates WHERE categorie_profil = %s ORDER BY id", (categorie,))
        else:
            cur.execute("SELECT id FROM candidates ORDER BY id")
        ids = [r[0] for r in cur.fetchall()]
        cur.close()
    return ids


class MatchingPipeline:
    """
    Pipeline : filtre → embeddings → similarité cosine → tri → top N → (feedback).
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        feedback_store: Optional[FeedbackStore] = None,
        min_similarity: float = MIN_SIMILARITY_THRESHOLD,
    ):
        self.embedding = embedding_service or EmbeddingService()
        self.feedback = feedback_store or FeedbackStore()
        self.min_similarity = min_similarity

    def run(
        self,
        job_id: int,
        top_n: int = DEFAULT_TOP_N,
        apply_feedback: bool = True,
        domaine_override: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Exécute le matching pour une offre.
        Retourne une liste de dicts : candidate_id, similarity_score, score (après feedback), candidate (snapshot optionnel).
        """
        # Étape 1 : Filtrage minimal (domaine)
        domaine = domaine_override or _load_job_domaine(job_id)
        candidate_ids = _load_candidate_ids_for_domaine(domaine)
        if not candidate_ids:
            return []

        # Étape 2 : Similarité vectorielle
        job_emb = self.embedding.embed_job(job_id)
        if job_emb is None:
            return []

        scored: List[Tuple[int, float]] = []
        for cid in candidate_ids:
            cand_emb = self.embedding.embed_candidate(cid, store=True)
            if cand_emb is None:
                continue
            sim = self.embedding.cosine_similarity(job_emb, cand_emb)
            if sim >= self.min_similarity:
                scored.append((cid, sim))

        # Étape 3 & 4 : Tri décroissant et Top N
        scored.sort(key=lambda x: -x[1])
        top = scored[:top_n]
        original_scores = {cid: s for cid, s in top}

        # Étape 5 : Re-ranking avec feedback (bonus/pénalité)
        if apply_feedback and self.feedback:
            top = self.feedback.apply_feedback_to_ranking(job_id, top)

        return [
            {
                "candidate_id": cid,
                "similarity_score": round(original_scores.get(cid, adj), 4),
                "score": round(adj, 4),
                "rank": i + 1,
            }
            for i, (cid, adj) in enumerate(top)
        ]
