from __future__ import annotations

from typing import Any


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for v in values:
        key = v.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(v.strip())
    return out


def build_analysis_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """
    Construit une "analyse" simple (agent 1) à partir de la fiche candidate.

    But:
    - Donner à l'agent 2 des recommandations concrètes (ex: skills max 8, realisations max 3)
    - Fonctionne sans appel LLM (rapide, déterministe)
    """
    suggested_changes: dict[str, Any] = {}
    notes: list[str] = []

    # Skills
    skills_raw = candidate.get("skills", [])
    skills: list[str] = []
    if isinstance(skills_raw, str):
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    elif isinstance(skills_raw, list):
        skills = [str(s).strip() for s in skills_raw if str(s).strip()]
    skills = _dedupe_preserve_order(skills)
    if len(skills) > 8:
        suggested_changes["skills"] = skills[:8]
        notes.append("Compétences réduites à 8 maximum (suppression des doublons / moins pertinentes).")

    # Réalisations
    real_raw = candidate.get("realisations", [])
    real: list[str] = []
    if isinstance(real_raw, str):
        real = [r.strip() for r in real_raw.split("\n") if r.strip()]
    elif isinstance(real_raw, list):
        real = [str(r).strip() for r in real_raw if str(r).strip()]
    if len(real) > 3:
        suggested_changes["realisations"] = real[:3]
        notes.append("Réalisations réduites à 3 maximum.")

    # Titre
    titre = candidate.get("Titre de profil") or candidate.get("titre_profil") or candidate.get("titre") or ""
    if isinstance(titre, str) and titre.strip() and len(titre.strip()) < 3:
        notes.append("Titre de profil très court: préciser le rôle/specialité.")

    # Champs manquants importants
    required = ["nom", "prenom", "email", "phone", "ville", "pays", "linkedin"]
    missing = [k for k in required if not candidate.get(k)]
    if missing:
        notes.append(f"Champs manquants à compléter si possible: {', '.join(missing)}.")

    summary = " ".join(notes).strip() or "Aucune recommandation majeure détectée."
    return {
        "summary": summary,
        "suggested_changes": suggested_changes,
    }


