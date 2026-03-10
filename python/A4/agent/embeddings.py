"""
Service d'embeddings sémantiques (sentence-transformers).
Convertit texte, offre ou profil candidat en vecteur pour similarité cosine.
"""
import json
import os
import sys
from typing import Any, Dict, List, Optional, Union

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database.connection import DatabaseConnection

from A4.agent.config import EMBEDDING_MODEL


def _get_model():
    """Charge le modèle sentence-transformers (lazy)."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(EMBEDDING_MODEL)
    except ImportError:
        return None


class EmbeddingService:
    """
    Embeddings pour jobs et candidats.
    Stocke les vecteurs candidats en base (table candidate_embeddings).
    """

    def __init__(self, model_name: Optional[str] = None):
        self._model = None
        self._model_name = model_name or EMBEDDING_MODEL

    @property
    def model(self):
        if self._model is None:
            self._model = _get_model()
        return self._model

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Encode un texte en vecteur. Retourne liste de floats (JSON-serializable)."""
        if not text or not text.strip():
            return None
        if self.model is None:
            return None
        try:
            vec = self.model.encode(text.strip(), convert_to_numpy=True)
            return vec.tolist()
        except Exception:
            return None

    def embed_texts(self, texts: List[str]) -> Optional[np.ndarray]:
        """Encode une liste de textes (batch). Retourne array (n, dim)."""
        texts = [t.strip() for t in texts if t and str(t).strip()]
        if not texts or self.model is None:
            return None
        try:
            return self.model.encode(texts, convert_to_numpy=True)
        except Exception:
            return None

    def _job_to_text(self, row: Dict[str, Any]) -> str:
        """Construit un bloc texte représentant l'offre pour l'embedding."""
        parts = []
        if row.get("title"):
            parts.append(str(row["title"]))
        if row.get("reason"):
            parts.append(str(row["reason"]))
        if row.get("main_mission"):
            parts.append(str(row["main_mission"]))
        if row.get("skills"):
            s = row["skills"]
            if isinstance(s, str):
                try:
                    s = json.loads(s)
                except Exception:
                    s = []
            if isinstance(s, list):
                for x in s:
                    if isinstance(x, dict) and x.get("name"):
                        parts.append(x["name"])
                    elif isinstance(x, str):
                        parts.append(x)
        if row.get("languages"):
            lang = row["languages"]
            if isinstance(lang, str):
                try:
                    lang = json.loads(lang)
                except Exception:
                    lang = []
            if isinstance(lang, list):
                for x in lang:
                    if isinstance(x, dict) and x.get("name"):
                        parts.append(x["name"])
                    elif isinstance(x, str):
                        parts.append(x)
        return " ".join(parts) if parts else ""

    def embed_job(self, job_id: int) -> Optional[List[float]]:
        """Charge l'offre en base et retourne son vecteur."""
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cur = db.cursor(dictionary=True)
            cur.execute(
                "SELECT title, reason, main_mission, skills, languages FROM jobs WHERE id = %s",
                (job_id,),
            )
            row = cur.fetchone()
            cur.close()
        if not row:
            return None
        text = self._job_to_text(row)
        return self.embed_text(text)

    def _candidate_to_text(self, row: Dict[str, Any], skills_csv: str = "", languages_csv: str = "") -> str:
        """Construit un bloc texte représentant le candidat pour l'embedding."""
        parts = []
        if row.get("titre_profil"):
            parts.append(str(row["titre_profil"]))
        if row.get("resume_bref"):
            parts.append(str(row["resume_bref"]))
        if skills_csv:
            parts.append(skills_csv.replace(",", " "))
        if languages_csv:
            parts.append(languages_csv.replace(",", " "))
        return " ".join(parts) if parts else ""

    def embed_candidate_from_row(self, row: Dict[str, Any], skills_csv: str = "", languages_csv: str = "") -> Optional[List[float]]:
        """Produit le vecteur d'un candidat à partir d'une ligne déjà chargée."""
        text = self._candidate_to_text(row, skills_csv, languages_csv)
        return self.embed_text(text)

    def get_candidate_embedding(self, candidate_id: int) -> Optional[List[float]]:
        """
        Récupère le vecteur candidat depuis la table candidate_embeddings.
        Retourne None si absent ou modèle différent.
        """
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cur = db.cursor(dictionary=True)
            try:
                cur.execute(
                    "SELECT embedding, model_version FROM candidate_embeddings WHERE candidate_id = %s ORDER BY updated_at DESC LIMIT 1",
                    (candidate_id,),
                )
                r = cur.fetchone()
            except Exception:
                r = None
            cur.close()
        if not r:
            return None
        model_version = r.get("model_version")
        if model_version != self._model_name:
            return None
        emb = r.get("embedding")
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except Exception:
                return None
        return emb if isinstance(emb, list) else None

    def set_candidate_embedding(self, candidate_id: int, embedding: List[float]) -> bool:
        """Enregistre ou met à jour le vecteur d'un candidat."""
        DatabaseConnection.initialize()
        emb_json = json.dumps(embedding)
        with DatabaseConnection.get_connection() as db:
            cur = db.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO candidate_embeddings (candidate_id, embedding, model_version, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE embedding = VALUES(embedding), model_version = VALUES(model_version), updated_at = NOW()
                    """,
                    (candidate_id, emb_json, self._model_name),
                )
                db.commit()
            except Exception:
                db.rollback()
                return False
            cur.close()
        return True

    def embed_candidate(self, candidate_id: int, store: bool = True) -> Optional[List[float]]:
        """
        Vecteur du candidat : depuis le cache (candidate_embeddings) ou calcul + stockage.
        """
        cached = self.get_candidate_embedding(candidate_id)
        if cached is not None:
            return cached
        # Charger candidat + skills + langues
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cur = db.cursor(dictionary=True)
            cur.execute(
                """
                SELECT c.id, c.titre_profil, c.resume_bref,
                       (SELECT GROUP_CONCAT(s.skill_name) FROM skills s WHERE s.candidate_id = c.id) AS skills_csv,
                       (SELECT GROUP_CONCAT(l.language_name) FROM languages l WHERE l.candidate_id = c.id) AS languages_csv
                FROM candidates c WHERE c.id = %s
                """,
                (candidate_id,),
            )
            row = cur.fetchone()
            cur.close()
        if not row:
            return None
        skills_csv = (row.get("skills_csv") or "").strip()
        languages_csv = (row.get("languages_csv") or "").strip()
        emb = self.embed_candidate_from_row(row, skills_csv, languages_csv)
        if emb and store:
            self.set_candidate_embedding(candidate_id, emb)
        return emb

    def cosine_similarity(self, a: Union[List[float], np.ndarray], b: Union[List[float], np.ndarray]) -> float:
        """Similarité cosine entre deux vecteurs."""
        from sklearn.metrics.pairwise import cosine_similarity as sk_cos
        a = np.array(a).reshape(1, -1) if not isinstance(a, np.ndarray) else a.reshape(1, -1)
        b = np.array(b).reshape(1, -1) if not isinstance(b, np.ndarray) else b.reshape(1, -1)
        return float(sk_cos(a, b)[0, 0])
