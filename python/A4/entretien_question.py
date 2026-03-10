# ======================================================
# A4 – Questions d'entretien à partir du CV du candidat validé
# Prend en entrée le CV (texte ou candidate_id) et retourne une liste de questions
# à poser en entretien, personnalisées selon le parcours du candidat.
# ======================================================

import os
import json
import re
import time
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    _gemini_model = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
    _model = genai.GenerativeModel(_gemini_model)
except Exception:
    _model = None


def get_cv_text_for_candidate(candidate_id: int) -> Tuple[bool, str, Optional[str]]:
    """
    Récupère le CV du candidat depuis MinIO et en extrait le texte.
    Utilise le CV corrigé si disponible, sinon le CV original.

    Returns:
        Tuple (success, cv_text, error_message)
    """
    try:
        from B2.agent_portfolio import get_cv_from_minio, extract_text_from_cv_bytes

        success, filename, cv_bytes = get_cv_from_minio(candidate_id, use_original_only=False)
        if not success or not cv_bytes:
            return False, "", "CV introuvable pour ce candidat"

        cv_text = extract_text_from_cv_bytes(cv_bytes, filename or "cv.pdf")
        if not (cv_text and cv_text.strip()):
            return False, "", "Impossible d'extraire le texte du CV"

        return True, cv_text.strip(), None
    except Exception as e:
        return False, "", str(e)


def generate_interview_questions_from_cv(
    cv_text: str,
    job_title: Optional[str] = None,
    max_questions: int = 12,
    lang: str = "fr",
) -> Dict:
    """
    Génère une liste de questions d'entretien personnalisées à partir du texte du CV
    du candidat validé par le recruteur.

    Les questions couvrent : présentation, expériences, projets, compétences techniques,
    outils, et questions comportementales adaptées au parcours du candidat.

    Args:
        cv_text: Texte extrait du CV du candidat.
        job_title: Poste visé (optionnel), pour adapter les questions au contexte.
        max_questions: Nombre maximum de questions à générer (défaut 12).
        lang: Langue des questions ("fr" par défaut).

    Returns:
        dict: {
            "success": bool,
            "questions": [ {"id": str, "text": str, "category": str} ],
            "error": str | None
        }
    """
    if not _model:
        return {
            "success": False,
            "questions": [],
            "error": "Gemini non configuré (GOOGLE_API_KEY manquant ou erreur d'import).",
        }

    if not (cv_text and cv_text.strip()):
        return {
            "success": False,
            "questions": [],
            "error": "Le texte du CV est vide.",
        }

    job_context = ""
    if job_title and job_title.strip():
        job_context = f"\nPoste visé par le candidat : {job_title.strip()}. Adapte les questions à ce contexte métier."

    prompt = f"""Tu es un recruteur senior qui prépare un entretien. À partir du CV du candidat ci-dessous, génère une liste de questions à poser pendant l'entretien. Les questions doivent être PERSONNALISÉES selon son parcours : expériences, projets, compétences, formation, et poste visé.
{job_context}

RÈGLES :
1. Génère entre 8 et {max_questions} questions maximum.
2. Répartis les questions dans les catégories suivantes (au moins une par catégorie quand le CV le permet) :
   - "presentation" : présentation du candidat, parcours, motivation pour le poste
   - "experience" : questions sur ses expériences professionnelles (entreprises, rôles, réalisations)
   - "projet" : questions sur des projets concrets mentionnés dans le CV
   - "technique" : compétences techniques, outils, stack, méthodes
   - "comportemental" : situations passées, travail en équipe, gestion de conflits, prise d'initiative
3. Chaque question doit faire référence à un élément concret du CV (entreprise, projet, technologie, diplôme) quand c'est pertinent.
4. Formule les questions comme un recruteur le ferait : clair, professionnel, en français.
5. Pas de formatage markdown (pas d'astérisques) dans le texte des questions.
6. Retourne UNIQUEMENT un JSON valide, sans texte avant ni après.

FORMAT DE RÉPONSE :
{{
  "questions": [
    {{ "id": "q1", "text": "Pour commencer, pouvez-vous vous présenter et nous dire ce qui vous amène vers ce poste ?", "category": "presentation" }},
    {{ "id": "q2", "text": "Sur votre expérience chez [Entreprise X], comment avez-vous... ?", "category": "experience" }},
    ...
  ]
}}

CV DU CANDIDAT :
---
{cv_text[:15000]}
---
"""

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = _model.generate_content(prompt)
            raw_text = (response.text or "").strip()
            break
        except Exception as api_error:
            error_str = str(api_error)
            if ("429" in error_str or "quota" in error_str.lower()) and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            return {
                "success": False,
                "questions": [],
                "error": f"Erreur API Gemini : {error_str[:300]}",
            }

    # Extraire le JSON
    match = re.search(r"\{[\s\S]*\}", raw_text)
    if not match:
        return {
            "success": False,
            "questions": [],
            "error": "Réponse invalide : aucun JSON trouvé.",
        }

    try:
        data = json.loads(match.group())
        questions = data.get("questions", [])
        if not questions:
            return {
                "success": False,
                "questions": [],
                "error": "Aucune question générée.",
            }

        # Normaliser : s'assurer que chaque entrée a id, text, category
        out = []
        for i, q in enumerate(questions):
            if isinstance(q, dict):
                out.append({
                    "id": q.get("id") or f"q{i+1}",
                    "text": (q.get("text") or "").strip(),
                    "category": (q.get("category") or "autre").strip().lower(),
                })
            elif isinstance(q, str):
                out.append({"id": f"q{i+1}", "text": q.strip(), "category": "autre"})

        out = [x for x in out if x["text"]]

        return {
            "success": True,
            "questions": out,
            "error": None,
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "questions": [],
            "error": f"Erreur de parsing JSON : {e}",
        }


def get_interview_questions_for_validated_candidate(
    candidate_id: Optional[int] = None,
    cv_text: Optional[str] = None,
    job_title: Optional[str] = None,
    max_questions: int = 12,
    lang: str = "fr",
) -> Dict:
 


    text_to_use = None

    if candidate_id is not None:
        ok, text_to_use, err = get_cv_text_for_candidate(candidate_id)
        if not ok:
            return {"success": False, "questions": [], "error": err or "CV introuvable"}
    elif cv_text:
        text_to_use = cv_text.strip()

    if not text_to_use:
        return {
            "success": False,
            "questions": [],
            "error": "Fournir soit candidate_id soit cv_text.",
        }

    return generate_interview_questions_from_cv(
        cv_text=text_to_use,
        job_title=job_title,
        max_questions=max_questions,
        lang=lang,
    )
