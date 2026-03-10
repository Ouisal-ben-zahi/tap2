# ======================================================
# Mémoire des validations utilisateur pour les agents
# Permet à l'IA d'apprendre à partir des validations
# (option : l'agent corrige ses problèmes lui-même)
# On n'injecte que du feedback GÉNÉRALISABLE (règles, format, style)
# pour ne pas appliquer les corrections personnelles d'un candidat aux autres.
# ======================================================

import re
from typing import Optional, List, Dict, Any


def _looks_personal_feedback(comment: str) -> bool:
    """
    Détecte si le commentaire concerne des données personnelles d'un candidat
    (nom, formation, expérience précise) qu'il ne faut pas réinjecter pour les autres.
    Retourne True si le feedback est personnel (à exclure de l'injection globale).
    """
    if not comment or not comment.strip():
        return True
    text = comment.strip().lower()
    # Très court = souvent un nom ou une valeur unique
    if len(text) < 15:
        return True
    # Références explicites aux données du candidat (à ne pas réutiliser telles quelles)
    personal_patterns = [
        r"\bmon\s+nom\b",
        r"\bma\s+formation\b",
        r"\bmes\s+formations\b",
        r"\bmon\s+pr[eé]nom\b",
        r"\bmes\s+exp[eé]riences\b",
        r"\bmon\s+dipl[oô]me\b",
        r"\bmes\s+dipl[oô]mes\b",
        r"\bmon\s+parcours\b",
        r"\bmes\s+([eé]tudes|comp[eé]tences)\b",
        r"pr[eé]nom\s*[:\=]",
        r"nom\s*[:\=]\s*\w+",  # "nom : Dupont"
        r"formation\s*[:\=]\s*\w+",
        r"remplacer\s+par\s+",  # "remplacer par X"
        r"mettre\s+(mon|ma|le)\s+",
        r"corriger\s+(mon|ma|le)\s+(nom|pr[eé]nom)",
        r"c['']est\s+[\w\-]+",  # "c'est Dupont"
        r"(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}",  # plage d'années
    ]
    for pat in personal_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    # Beaucoup de chiffres (dates, numéros) = souvent des données personnelles
    digit_count = sum(1 for c in text if c.isdigit())
    if digit_count > 4:
        return True
    return False


def save_validation(
    agent_id: str,
    validation_status: str,
    feedback_comment: Optional[str] = None,
    candidate_id: Optional[int] = None,
) -> bool:
    """
    Enregistre une validation utilisateur (approved / rejected / needs_revision)
    pour qu'elle soit réutilisée dans les prochains prompts de l'agent.

    Args:
        agent_id: Identifiant de l'agent (ex: 'B1', 'B2', 'B3')
        validation_status: 'approved', 'rejected', 'needs_revision'
        feedback_comment: Commentaire de l'utilisateur pour amélioration
        candidate_id: ID du candidat concerné (optionnel)

    Returns:
        True si l'enregistrement a réussi, False sinon
    """
    try:
        from database.connection import DatabaseConnection

        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor()
            cursor.execute(
                """
                INSERT INTO agent_validation_memory
                (agent_id, validation_status, feedback_comment, candidate_id)
                VALUES (%s, %s, %s, %s)
                """,
                (agent_id, validation_status, (feedback_comment or "").strip() or None, candidate_id),
            )
            db.commit()
            cursor.close()
        return True
    except Exception as e:
        print(f"⚠️ agent_memory.save_validation: {e}")
        return False


def get_memory_for_prompt(agent_id: str, max_items: int = 10) -> str:
    """
    Retourne un texte résumant les validations récentes (rejets / révisions)
    à injecter dans le prompt de l'agent pour qu'il apprenne des retours utilisateur.

    On ne garde que les cas où l'utilisateur a rejeté ou demandé une révision,
    avec un commentaire, pour éviter le bruit.

    Args:
        agent_id: Identifiant de l'agent (ex: 'B1')
        max_items: Nombre maximum d'entrées à inclure

    Returns:
        Chaîne à ajouter au prompt (vide si rien à apprendre)
    """
    try:
        from database.connection import DatabaseConnection

        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT validation_status, feedback_comment, created_at
                FROM agent_validation_memory
                WHERE agent_id = %s
                  AND validation_status IN ('rejected', 'needs_revision')
                  AND feedback_comment IS NOT NULL AND TRIM(feedback_comment) != ''
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (agent_id, max_items),
            )
            rows = cursor.fetchall()
            cursor.close()
    except Exception as e:
        print(f"⚠️ agent_memory.get_memory_for_prompt: {e}")
        return ""

    if not rows:
        return ""

    lines = []
    had_personal = False
    for r in rows:
        status = r.get("validation_status", "")
        comment = (r.get("feedback_comment") or "").strip()
        if not comment:
            continue
        if _looks_personal_feedback(comment):
            had_personal = True
            continue  # Ne pas réinjecter les retours personnels (nom, formation, etc.)
        label = "Révision demandée" if status == "needs_revision" else "Rejet"
        lines.append(f"- {label}: « {comment[:200]}{'…' if len(comment) > 200 else ''} »")

    # Rappel générique si on a exclu du feedback personnel (sans exposer les données)
    if had_personal:
        lines.append(
            "- Rappel : respecter strictement les données de la fiche candidat (noms, formations, expériences) sans en inventer."
        )

    if not lines:
        return ""

    return (
        "\n\n⚠️ APPRENTISSAGE À PARTIR DES VALIDATIONS UTILISATEUR (règles générales) :\n"
        "Lors des validations récentes, les utilisateurs ont indiqué :\n"
        + "\n".join(lines[: max_items + 1])  # +1 pour la ligne rappel si had_personal
        + "\nTiens compte de ces retours pour améliorer ta sortie."
    )
