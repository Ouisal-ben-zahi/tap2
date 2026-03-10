"""
Préfixe MinIO par candidat : candidates/{categorie_profil}/{candidate_id}/
Permet de diviser les dossiers par profil (dev, data, design, video, etc.).
"""
from typing import Optional

def normalize_categorie_profil(value: Optional[str]) -> str:
    """
    Retourne la catégorie telle qu'elle est fournie (sans normalisation).
    Fallback: "autre" si la valeur est vide.
    """
    if not value or not str(value).strip():
        return "autre"
    return str(value).strip()


def get_candidate_minio_prefix(candidate_id: int, categorie_profil: Optional[str] = None) -> str:
   
   
    if categorie_profil is not None:
        cat = normalize_categorie_profil(categorie_profil)
        return f"candidates/{cat}/{int(candidate_id)}/"
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                "SELECT categorie_profil FROM candidates WHERE id = %s",
                (int(candidate_id),),
            )
            row = cursor.fetchone()
            cursor.close()
            cat = normalize_categorie_profil((row or {}).get("categorie_profil") if row else None)
            return f"candidates/{cat}/{int(candidate_id)}/"
    except Exception:
        return f"candidates/autre/{int(candidate_id)}/"
