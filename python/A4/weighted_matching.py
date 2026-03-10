"""
Niveau 2 — Matching pondéré intelligent.

- Skills obligatoires (priority "Indispensable") = poids 3
- Skills optionnelles = poids 1
- Expérience = poids variable (score 0–1 × coefficient)
- Similarité sémantique sur les compétences : TF-IDF + cosine similarity
  (ex. "Data Analysis" ≈ "Data Analytics")
"""
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import DatabaseConnection
from candidate_minio_path import normalize_categorie_profil

# Poids du matching
WEIGHT_REQUIRED_SKILL = 3
WEIGHT_OPTIONAL_SKILL = 1
WEIGHT_EXPERIENCE_MAX = 2.0   
WEIGHT_TITRE = 1.5            
WEIGHT_DISPONIBILITE = 1.0    # disponibilité
WEIGHT_CONTRAT = 1.0          # type de contrat
WEIGHT_LANGUES = 1.5          # langues demandées vs parlées
WEIGHT_LOCALISATION = 1.2     # ville / prêt à recoler
SIMILARITY_THRESHOLD = 0.5    # seuil cosine pour considérer un match sémantique


SENIORITY_ORDER = ["Junior", "Débutant", "Mid", "Intermédiaire", "Senior", "Avancé", "Lead", "Expert"]


def _normalize_seniority(s: Optional[str]) -> str:
    if not s or not isinstance(s, str):
        return ""
    return s.strip().lower()


def _seniority_level(name: str) -> int:
    """Indice dans l'échelle de séniorité (plus grand = plus senior)."""
    if not name or not isinstance(name, str):
        return -1
    n = _normalize_seniority(name)
    for i, level in enumerate(SENIORITY_ORDER):
        if _normalize_seniority(level) == n or level.lower() in n or n in level.lower():
            return i
    return -1


def _parse_experience_min(value: Optional[str]) -> Optional[int]:
    """Parse experience_min (ex. '3', '5 ans', '1-3 ans') en nombre d'années."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    s = str(value).strip()
    numbers = re.findall(r"\d+\.?\d*", s)
    if numbers:
        try:
            return int(float(numbers[0]))
        except (ValueError, TypeError):
            pass
    return None


def _get_tfidf():
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        return TfidfVectorizer, cosine_similarity
    except ImportError:
        return None, None


def load_candidates_for_domaine(domaine_activite: Optional[str]) -> List[Dict[str, Any]]:
    """
    Charge les candidats (skills, langues, types de contrat, pret_a_relocater) pour un domaine.
    Si domaine_activite est vide, charge tous les candidats.
    """
    DatabaseConnection.initialize()
    categorie = normalize_categorie_profil(domaine_activite or "") if domaine_activite else None
    with DatabaseConnection.get_connection() as db:
        cursor = db.cursor(dictionary=True)
        base_cols = (
            "c.id, c.id_agent, c.candidate_uuid, c.nom, c.prenom, c.titre_profil, c.categorie_profil, "
            "c.ville, c.pays, c.annees_experience, c.disponibilite, c.niveau_seniorite, c.pret_a_relocater, "
            "c.pays_cible, c.constraints, c.search_criteria, c.salaire_minimum, "
            "(SELECT GROUP_CONCAT(s.skill_name) FROM skills s WHERE s.candidate_id = c.id) AS skills_csv, "
            "(SELECT GROUP_CONCAT(l.language_name) FROM languages l WHERE l.candidate_id = c.id) AS languages_csv, "
            "(SELECT GROUP_CONCAT(ct.type_name) FROM contract_types ct WHERE ct.candidate_id = c.id) AS contract_types_csv, "
            "(SELECT GROUP_CONCAT(r.description) FROM realisations r WHERE r.candidate_id = c.id) AS realisations_csv"
        )
        sql = f"SELECT {base_cols} FROM candidates c"
        if categorie:
            # Insensible à la casse : matcher design / Design / DESIGN (categorie passé en minuscules)
            sql += " WHERE LOWER(TRIM(COALESCE(c.categorie_profil, ''))) = %s"
        sql += " ORDER BY c.id"
        try:
            cursor.execute(sql, (categorie,) if categorie else ())
        except Exception as e:
            if "1054" in str(e) or "Unknown column" in str(e):
                base_cols = (
                    "c.id, c.id_agent, c.candidate_uuid, c.nom, c.prenom, c.titre_profil, c.categorie_profil, "
                    "c.ville, c.pays, c.annees_experience, c.disponibilite, c.niveau_seniorite, "
                    "(SELECT GROUP_CONCAT(s.skill_name) FROM skills s WHERE s.candidate_id = c.id) AS skills_csv, "
                    "(SELECT GROUP_CONCAT(l.language_name) FROM languages l WHERE l.candidate_id = c.id) AS languages_csv, "
                    "(SELECT GROUP_CONCAT(ct.type_name) FROM contract_types ct WHERE ct.candidate_id = c.id) AS contract_types_csv"
                )
                sql = f"SELECT {base_cols} FROM candidates c"
                if categorie:
                    sql += " WHERE LOWER(TRIM(COALESCE(c.categorie_profil, ''))) = %s"
                sql += " ORDER BY c.id"
                cursor.execute(sql, (categorie,) if categorie else ())
            else:
                raise
        rows = cursor.fetchall()
        cursor.close()
    # Si pret_a_relocater n'existe pas en base, on l'ajoute via une requête séparée ou on ignore
    out = []
    for r in rows:
        row = dict(r)
        for k, v in list(row.items()):
            if hasattr(v, "isoformat"):
                row[k] = v.isoformat()
        skills_csv = row.get("skills_csv") or ""
        row["skills"] = [s.strip() for s in skills_csv.split(",") if s.strip()]
        row.pop("skills_csv", None)
        lang_csv = row.get("languages_csv") or ""
        row["languages"] = [s.strip() for s in lang_csv.split(",") if s.strip()]
        row.pop("languages_csv", None)
        ct_csv = row.get("contract_types_csv") or ""
        row["contract_types"] = [s.strip() for s in ct_csv.split(",") if s.strip()]
        row.pop("contract_types_csv", None)
        if "pret_a_relocater" not in row:
            row["pret_a_relocater"] = None
        if "pays_cible" not in row:
            row["pays_cible"] = None
        if "constraints" not in row:
            row["constraints"] = None
        if "search_criteria" not in row:
            row["search_criteria"] = None
        if "salaire_minimum" not in row:
            row["salaire_minimum"] = None
        if "candidate_uuid" not in row or row.get("candidate_uuid") is None:
            row["candidate_uuid"] = row.get("id_agent") or ""
        real_csv = row.get("realisations_csv") or ""
        row["realisations"] = [s.strip() for s in (real_csv.split(",") if isinstance(real_csv, str) else []) if s.strip()]
        row.pop("realisations_csv", None)
        out.append(row)
    return out


def _parse_json_field(value: Any, default: Any = None) -> Any:
    if value is None:
        return default if default is not None else []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default if default is not None else []
    return default if default is not None else []


def load_job_criteria(job_id: int) -> Optional[Dict[str, Any]]:
    """Charge les critères d'une offre (skills, expérience, titre, disponibilité, salaire, lieu, langues, contrat, etc.)."""
    DatabaseConnection.initialize()
    with DatabaseConnection.get_connection() as db:
        cursor = db.cursor(dictionary=True)
        row = None
        # Essayer d'abord avec les colonnes essentielles (dont categorie_profil pour le matching)
        for columns in [
            "id, title, domaine_activite, categorie_profil, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salary_min, salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat",
            "id, title, domaine_activite, categorie_profil, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salaire_minimum AS salary_min, salaire_maximum AS salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat",
            "id, title, domaine_activite, categorie_profil, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salaire_min AS salary_min, salaire_max AS salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salary_min, salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat, domaine_activite, categorie_profil",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salaire_minimum AS salary_min, salaire_maximum AS salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat, domaine_activite, categorie_profil",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salaire_min AS salary_min, salaire_max AS salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat, domaine_activite, categorie_profil",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salary_min, salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat, domaine_activite",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salaire_minimum AS salary_min, salaire_maximum AS salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat, domaine_activite",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salaire_min AS salary_min, salaire_max AS salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat, domaine_activite",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salary_min, salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salaire_minimum AS salary_min, salaire_maximum AS salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salaire_min AS salary_min, salaire_max AS salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salary_min, salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat, domaine_activite",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salaire_minimum AS salary_min, salaire_maximum AS salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat, domaine_activite",
            "id, title, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site, reason, main_mission, tasks_other, disponibilite, salaire_min AS salary_min, salaire_max AS salary_max, urgent, location_type, tasks, soft_skills, skills, languages, contrat, domaine_activite",
            "skills, experience_min, niveau_attendu, niveau_seniorite, domaine_activite, categorie_profil, title, disponibilite, salary_min, salary_max, location_type, languages, contrat",
            "skills, experience_min, niveau_attendu, niveau_seniorite, domaine_activite, categorie_profil, title, disponibilite, salaire_minimum AS salary_min, salaire_maximum AS salary_max, location_type, languages, contrat",
            "skills, experience_min, niveau_attendu, niveau_seniorite, domaine_activite, categorie_profil, title, disponibilite, salaire_min AS salary_min, salaire_max AS salary_max, location_type, languages, contrat",
            "skills, experience_min, niveau_attendu, niveau_seniorite, domaine_activite, title, disponibilite, salary_min, salary_max, location_type, languages, contrat",
            "skills, experience_min, niveau_attendu, niveau_seniorite, domaine_activite, title, disponibilite, salaire_minimum AS salary_min, salaire_maximum AS salary_max, location_type, languages, contrat",
            "skills, experience_min, niveau_attendu, niveau_seniorite, domaine_activite, title, disponibilite, salaire_min AS salary_min, salaire_max AS salary_max, location_type, languages, contrat",
            "skills, experience_min, niveau_attendu, domaine_activite, title, disponibilite, salary_min, salary_max, location_type, languages, contrat",
            "skills, experience_min, niveau_attendu, domaine_activite, title, disponibilite, salaire_minimum AS salary_min, salaire_maximum AS salary_max, location_type, languages, contrat",
            "skills, experience_min, niveau_attendu, domaine_activite, title, disponibilite, salaire_min AS salary_min, salaire_max AS salary_max, location_type, languages, contrat",
            "skills, experience_min, niveau_attendu, domaine_activite, title, disponibilite, salary_min, salary_max, location_type, languages",
            "skills, experience_min, niveau_attendu, domaine_activite, title, disponibilite, salaire_minimum AS salary_min, salaire_maximum AS salary_max, location_type, languages",
            "skills, experience_min, niveau_attendu, domaine_activite, title, disponibilite, salaire_min AS salary_min, salaire_max AS salary_max, location_type, languages",
            "skills, experience_min, niveau_attendu, domaine_activite, title, disponibilite",
            "skills, experience_min, niveau_attendu, domaine_activite",
            "skills, experience_min, niveau_attendu",
        ]:
            try:
                cursor.execute(
                    f"SELECT {columns} FROM jobs WHERE id = %s",
                    (job_id,),
                )
                row = cursor.fetchone()
                break
            except Exception as e:
                if "1054" in str(e) or "Unknown column" in str(e):
                    continue
                raise
        else:
            return None
        cursor.close()
    if not row:
        return None
    skills_raw = row.get("skills")
    if isinstance(skills_raw, str):
        try:
            skills_raw = json.loads(skills_raw)
        except (json.JSONDecodeError, TypeError):
            skills_raw = []
    if not isinstance(skills_raw, list):
        skills_raw = []
    skills_obligatoires = []
    skills_optionnelles = []
    for s in skills_raw:
        if not isinstance(s, dict):
            continue
        name = (s.get("name") or "").strip()
        if not name:
            continue
        priority = (s.get("priority") or "").strip()
        if priority == "Indispensable":
            skills_obligatoires.append(name)
        else:
            skills_optionnelles.append(name)
    domaine = (row.get("domaine_activite") or "").strip().upper() or None
    categorie_profil = (row.get("categorie_profil") or "").strip() or None
    title = (row.get("title") or "").strip() or None
    disponibilite = (row.get("disponibilite") or "").strip() or None
    salary_min = row.get("salary_min")
    salary_max = row.get("salary_max")
    if salary_min is not None and hasattr(salary_min, "__float__"):
        try:
            salary_min = float(salary_min)
        except (TypeError, ValueError):
            salary_min = None
    if salary_max is not None and hasattr(salary_max, "__float__"):
        try:
            salary_max = float(salary_max)
        except (TypeError, ValueError):
            salary_max = None
    location_type = _parse_json_field(row.get("location_type"), [])
    if isinstance(location_type, list):
        job_villes = [str(x).strip() for x in location_type if x]
    else:
        job_villes = []
    languages_raw = _parse_json_field(row.get("languages"), [])
    job_langues = []
    for lang in languages_raw:
        if isinstance(lang, dict):
            name = (lang.get("name") or "").strip()
            if name:
                job_langues.append({"name": name, "importance": (lang.get("importance") or "").strip()})
        elif isinstance(lang, str) and lang.strip():
            job_langues.append({"name": lang.strip(), "importance": ""})
    contrat = (row.get("contrat") or "").strip() or None
    # Champs bruts (table jobs)
    presence_sur_site = (row.get("presence_sur_site") or "").strip() or None
    reason = (row.get("reason") or "").strip() or None
    main_mission = (row.get("main_mission") or "").strip() or None
    tasks_other = (row.get("tasks_other") or "").strip() or None
    urgent = row.get("urgent")
    if urgent is not None and not isinstance(urgent, (int, float, bool)):
        try:
            urgent = int(urgent)
        except (TypeError, ValueError):
            urgent = None
    tasks_raw = row.get("tasks")
    soft_skills_raw = row.get("soft_skills")
    niveau_seniorite = (row.get("niveau_seniorite") or "").strip() or None
    return {
        "id": row.get("id"),
        "skills_obligatoires": skills_obligatoires,
        "skills_optionnelles": skills_optionnelles,
        "experience_min": row.get("experience_min"),
        "niveau_attendu": row.get("niveau_attendu"),
        "niveau_seniorite": niveau_seniorite,
        "domaine_activite": domaine,
        "categorie_profil": categorie_profil,
        "title": title,
        "disponibilite": disponibilite,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "location_type": job_villes,
        "languages": job_langues,
        "contrat": contrat,
        "presence_sur_site": presence_sur_site,
        "reason": reason,
        "main_mission": main_mission,
        "tasks_other": tasks_other,
        "urgent": urgent,
        "tasks": tasks_raw,
        "soft_skills": soft_skills_raw,
    }


def build_skill_similarity_matrix(
    job_skill_names: List[str],
    all_candidate_skills: List[str],
    threshold: float = SIMILARITY_THRESHOLD,
) -> Tuple[Optional[Any], Optional[Any], Optional[Any]]:
    """
    Construit le vectorizer TF-IDF et les matrices pour la similarité cosine.
    Retourne (vectorizer, matrix_job, matrix_candidates) ou (None, None, None) si sklearn absent.
    """
    TfidfVectorizer, cosine_similarity = _get_tfidf()
    if TfidfVectorizer is None or cosine_similarity is None:
        return None, None, None
    # Vocabulaire = tous les skills (job + candidats), sans doublons
    all_skills = list(dict.fromkeys(job_skill_names + all_candidate_skills))
    if not all_skills:
        return None, None, None
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", lowercase=True)
    matrix_all = vectorizer.fit_transform(all_skills)
    # Indices des skills job dans all_skills
    job_indices = [all_skills.index(s) for s in job_skill_names if s in all_skills]
    if not job_indices:
        job_matrix = vectorizer.transform(job_skill_names) if job_skill_names else None
    else:
        job_matrix = matrix_all[job_indices]
    # Matrice candidats : une ligne par skill candidat
    candidate_skill_list = list(dict.fromkeys(all_candidate_skills))
    if candidate_skill_list:
        candidate_matrix = vectorizer.transform(candidate_skill_list)
    else:
        candidate_matrix = None
    return vectorizer, job_matrix, candidate_matrix


def best_similarity(
    job_skill: str,
    candidate_skills: List[str],
    vectorizer,
    job_vec_index: int,
    job_matrix,
    candidate_skill_to_index: Dict[str, int],
    candidate_matrix,
    threshold: float = SIMILARITY_THRESHOLD,
) -> float:
    """
    Retourne la meilleure similarité cosine entre job_skill et les skills du candidat.
    job_vec_index : indice de job_skill dans la matrice job (si on a une matrice job par skill).
    """
    from sklearn.metrics.pairwise import cosine_similarity

    if not candidate_skills:
        return 0.0
    # Match exact (après normalisation)
    j_lower = job_skill.lower().strip()
    for cs in candidate_skills:
        if (cs or "").lower().strip() == j_lower:
            return 1.0


    
    if vectorizer is None or job_matrix is None or candidate_matrix is None:
        return 0.0
    try:
        j_vec = job_matrix[job_vec_index : job_vec_index + 1]
        
        indices = [candidate_skill_to_index.get(s) for s in candidate_skills if s in candidate_skill_to_index]
        if not indices:
            return 0.0
        c_vec = candidate_matrix[indices]
        sim = cosine_similarity(j_vec, c_vec)
        return float(sim.max())
    except Exception:
        return 0.0


def score_experience(
    candidate_years: Optional[int],
    candidate_seniority: Optional[str],
    job_experience_min: Optional[int],
    job_niveau_attendu: Optional[str],
) -> float:
    """
    Score d'expérience entre 0 et 1 (poids variable appliqué côté appelant).
    - Années : 1.0 si candidat >= demandé, sinon proportion.
    - Niveau : bonus si niveau candidat >= niveau demandé.
    """
    score_years = 1.0
    if job_experience_min is not None and job_experience_min > 0:
        c_years = 0 if candidate_years is None else int(candidate_years)
        if c_years >= job_experience_min:
            score_years = 1.0
        else:
            score_years = max(0.0, c_years / job_experience_min) if job_experience_min else 1.0
    score_level = 1.0
    if job_niveau_attendu:
        j_level = _seniority_level(job_niveau_attendu)
        c_idx = _seniority_level(candidate_seniority or "")
        if j_level >= 0:
            if c_idx >= 0 and c_idx >= j_level:
                score_level = 1.0
            elif c_idx >= 0:
                score_level = max(0.0, 0.5 + 0.5 * (c_idx / max(1, len(SENIORITY_ORDER))))
            else:
                score_level = 0.5
    return 0.6 * score_years + 0.4 * score_level


def score_titre_profil(
    job_title: Optional[str],
    candidate_titre: Optional[str],
    vectorizer=None,
    text_matrix=None,
    text_to_index: Optional[Dict[str, int]] = None,
) -> float:
    """Score 0–1 : similarité entre le titre du poste et le titre de profil du candidat (TF-IDF si dispo)."""
    if not job_title or not candidate_titre:
        return 0.5 if (job_title or candidate_titre) else 0.0
    j = job_title.lower().strip()
    c = candidate_titre.lower().strip()
    if j == c:
        return 1.0
    if j in c or c in j:
        return 0.85
    if vectorizer is not None and text_matrix is not None and text_to_index is not None:
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            idx_j = text_to_index.get(job_title)
            idx_c = text_to_index.get(candidate_titre)
            if idx_j is not None and idx_c is not None:
                v_j = text_matrix[idx_j : idx_j + 1]
                v_c = text_matrix[idx_c : idx_c + 1]
                sim = cosine_similarity(v_j, v_c)
                return float(max(0.0, min(1.0, sim[0, 0])))
        except Exception:
            pass
    return 0.3


def score_disponibilite(job_dispo: Optional[str], candidate_dispo: Optional[str]) -> float:
    """Score 0–1 : match disponibilité (exact ou proche)."""
    if not job_dispo and not candidate_dispo:
        return 0.5
    if not job_dispo or not candidate_dispo:
        return 0.0
    j = job_dispo.lower().strip()
    c = candidate_dispo.lower().strip()
    if j == c:
        return 1.0
    if j in c or c in j:
        return 0.9
    return 0.0


def score_contrat(job_contrat: Optional[str], candidate_contract_types: Optional[List[str]]) -> float:
    """Score 0–1 : le type de contrat de l'offre est accepté par le candidat."""
    if not job_contrat:
        return 0.5
    if not candidate_contract_types:
        return 0.0
    job_c = job_contrat.lower().strip()
    for ct in (candidate_contract_types or []):
        if (ct or "").lower().strip() == job_c:
            return 1.0
        if job_c in (ct or "").lower() or (ct or "").lower() in job_c:
            return 0.9
    return 0.0


def score_langues(
    job_languages: List[Dict[str, str]],
    candidate_languages: Optional[List[str]],
) -> float:
    """Score 0–1 : proportion des langues demandées par l'offre que le candidat parle (Indispensable = plus fort)."""
    if not job_languages:
        return 0.5
    cand_lang = [ (x or "").strip().lower() for x in (candidate_languages or []) if x ]
    if not cand_lang:
        return 0.0
    score = 0.0
    total_weight = 0.0
    for lang in job_languages:
        name = (lang.get("name") or "").strip()
        if not name:
            continue
        importance = (lang.get("importance") or "").strip()
        weight = 2.0 if importance == "Indispensable" else 1.0
        total_weight += weight
        if name.lower() in cand_lang or any(name.lower() in c for c in cand_lang):
            score += weight
    return score / total_weight if total_weight else 0.0


def score_localisation(
    job_villes: List[str],
    candidate_ville: Optional[str],
    pret_a_relocater: Optional[str],
) -> float:
    """Score 0–1 : même ville = 1, prêt à recoler = 0.7, à discuter = 0.4, non = 0."""
    if not job_villes:
        return 0.5
    job_v = [ v.strip().lower() for v in job_villes if v ]
    if not job_v:
        return 0.5
    cand_ville = (candidate_ville or "").strip().lower()
    if cand_ville and cand_ville in job_v:
        return 1.0
    reloc = (pret_a_relocater or "").strip().lower()
    if "oui" in reloc:
        return 0.7
    if "discuter" in reloc or "discut" in reloc:
        return 0.4
    return 0.0


def score_candidate(
    candidate: Dict[str, Any],
    job_criteria: Dict[str, Any],
    vectorizer,
    job_matrix,
    candidate_skill_to_index: Dict[str, int],
    candidate_matrix,
    job_skill_list: List[str],
    threshold: float = SIMILARITY_THRESHOLD,
    titre_matrix=None,
    titre_to_index: Optional[Dict[str, int]] = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    Calcule le score total et un détail : skills, expérience, titre, disponibilité, contrat, langues, localisation.
    """
    skills_obligatoires = job_criteria.get("skills_obligatoires") or []
    skills_optionnelles = job_criteria.get("skills_optionnelles") or []
    candidate_skills = candidate.get("skills") or []
    detail = {
        "skills_matched_obligatoires": [],
        "skills_matched_optionnelles": [],
        "score_experience": 0.0,
        "score_titre": 0.0,
        "score_disponibilite": 0.0,
        "score_contrat": 0.0,
        "score_langues": 0.0,
        "score_localisation": 0.0,
    }

    score_skills = 0.0
    for i, skill in enumerate(skills_obligatoires):
        sim = best_similarity(
            skill,
            candidate_skills,
            vectorizer,
            i,
            job_matrix,
            candidate_skill_to_index,
            candidate_matrix,
            threshold,
        )
        if sim >= threshold:
            score_skills += WEIGHT_REQUIRED_SKILL * sim
            detail["skills_matched_obligatoires"].append({"skill": skill, "similarity": round(sim, 3)})
    for i, skill in enumerate(skills_optionnelles):
        idx = len(skills_obligatoires) + i
        sim = best_similarity(
            skill,
            candidate_skills,
            vectorizer,
            idx,
            job_matrix,
            candidate_skill_to_index,
            candidate_matrix,
            threshold,
        )
        if sim >= threshold:
            score_skills += WEIGHT_OPTIONAL_SKILL * sim
            detail["skills_matched_optionnelles"].append({"skill": skill, "similarity": round(sim, 3)})

    exp_score = score_experience(
        candidate.get("annees_experience"),
        candidate.get("niveau_seniorite"),
        _parse_experience_min(job_criteria.get("experience_min")),
        job_criteria.get("niveau_attendu"),
    )
    detail["score_experience"] = round(exp_score, 3)

    # Titre de l'offre vs titre de profil candidat
    job_title = (job_criteria.get("title") or "").strip() or None
    candidate_titre = (candidate.get("titre_profil") or "").strip() or None
    st = score_titre_profil(
        job_title,
        candidate_titre,
        vectorizer=None,
        text_matrix=titre_matrix,
        text_to_index=titre_to_index or {},
    )
    detail["score_titre"] = round(st, 3)

    # Disponibilité
    sd = score_disponibilite(
        job_criteria.get("disponibilite"),
        candidate.get("disponibilite"),
    )
    detail["score_disponibilite"] = round(sd, 3)

    # Type de contrat
    sc = score_contrat(
        job_criteria.get("contrat"),
        candidate.get("contract_types"),
    )
    detail["score_contrat"] = round(sc, 3)

    # Langues
    sl = score_langues(
        job_criteria.get("languages") or [],
        candidate.get("languages"),
    )
    detail["score_langues"] = round(sl, 3)

    # Localisation (ville / prêt à recoller)
    sloc = score_localisation(
        job_criteria.get("location_type") or [],
        candidate.get("ville"),
        candidate.get("pret_a_relocater"),
    )
    detail["score_localisation"] = round(sloc, 3)

    score_total = (
        score_skills
        + WEIGHT_EXPERIENCE_MAX * exp_score
        + WEIGHT_TITRE * st
        + WEIGHT_DISPONIBILITE * sd
        + WEIGHT_CONTRAT * sc
        + WEIGHT_LANGUES * sl
        + WEIGHT_LOCALISATION * sloc
    )
    detail["score_skills"] = round(score_skills, 2)
    detail["score_total"] = round(score_total, 2)
    return score_total, detail


def weighted_match(
    domaine_activite: Optional[str] = None,
    job_id: Optional[int] = None,
    job_criteria: Optional[Dict[str, Any]] = None,
    top_n: int = 20,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Matching pondéré intelligent.

    - domaine_activite: filtre candidats par domaine (DATA, DEV, DESIGN, VIDEO, AUTRE). Optionnel.
    - job_id: charger les critères depuis la table jobs. Optionnel si job_criteria fourni.
    - job_criteria: dict avec skills_obligatoires, skills_optionnelles, experience_min, niveau_attendu. Ignoré si job_id fourni.
    - top_n: nombre de candidats à retourner (tri par score décroissant).
    - similarity_threshold: seuil cosine pour accepter un match de skill.

    Retourne une liste de dicts: { "candidate": {...}, "score": float, "detail": {...} }.
    """
    if job_id is not None:
        criteria = load_job_criteria(job_id)
        if not criteria:
            return []
        # Matching sur le domaine exact : utiliser categorie_profil (dev, data, design, etc.) en priorité, sinon domaine_activite (DATA, DEV, DESIGN)
        job_categorie = (criteria.get("categorie_profil") or "").strip() or None
        job_domaine = (criteria.get("domaine_activite") or "").strip() or None
        if job_categorie:
            domaine_activite = job_categorie
        elif job_domaine:
            domaine_activite = job_domaine
    else:
        criteria = job_criteria or {}
    if not criteria and not (criteria.get("skills_obligatoires") or criteria.get("skills_optionnelles")):
        # Au moins un critère skill ou on score uniquement l'expérience
        pass

    candidates = load_candidates_for_domaine(domaine_activite)
    if not candidates:
        return []

    job_skill_names = (criteria.get("skills_obligatoires") or []) + (criteria.get("skills_optionnelles") or [])
    all_candidate_skills = []
    for c in candidates:
        all_candidate_skills.extend(c.get("skills") or [])
    all_candidate_skills = list(dict.fromkeys(all_candidate_skills))

    vectorizer, job_matrix, candidate_matrix = build_skill_similarity_matrix(
        job_skill_names, all_candidate_skills, similarity_threshold
    )
    candidate_skill_to_index = {}
    if all_candidate_skills:
        uniq = list(dict.fromkeys(all_candidate_skills))
        candidate_skill_to_index = {s: i for i, s in enumerate(uniq)}

    # Matrice TF-IDF pour similarité titre offre / titre profil candidat
    titre_matrix = None
    titre_to_index = {}
    titles = [(criteria.get("title") or "").strip()]
    titles += [(c.get("titre_profil") or "").strip() for c in candidates]
    titles = list(dict.fromkeys(t for t in titles if t))
    if titles:
        TfidfV, _ = _get_tfidf()
        if TfidfV is not None:
            try:
                vec_titre = TfidfV(ngram_range=(1, 2), strip_accents="unicode", lowercase=True)
                titre_matrix = vec_titre.fit_transform(titles)
                titre_to_index = {t: i for i, t in enumerate(titles)}
            except Exception:
                pass

    results = []
    for c in candidates:
        total, detail = score_candidate(
            c,
            criteria,
            vectorizer,
            job_matrix,
            candidate_skill_to_index,
            candidate_matrix,
            job_skill_names,
            similarity_threshold,
            titre_matrix=titre_matrix,
            titre_to_index=titre_to_index,
        )
        results.append({"candidate": c, "score": total, "detail": detail})
    results.sort(key=lambda x: -x["score"])
    return results[:top_n]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Matching pondéré (Niveau 2)")
    parser.add_argument("--domaine", default="DEV", help="Domaine (DATA, DEV, DESIGN, VIDEO, AUTRE)")
    parser.add_argument("--job-id", type=int, default=None, help="ID de l'offre en base")
    parser.add_argument("--top", type=int, default=5, help="Nombre de candidats à afficher")
    args = parser.parse_args()
    if args.job_id:
        out = weighted_match(domaine_activite=args.domaine, job_id=args.job_id, top_n=args.top)
    else:
        out = weighted_match(
            domaine_activite=args.domaine,
            job_criteria={
                "skills_obligatoires": ["Python", "Data Analysis"],
                "skills_optionnelles": ["SQL", "Machine Learning"],
                "experience_min": "3",
                "niveau_attendu": "Senior",
            },
            top_n=args.top,
        )
    if not out:
        print(
            "Aucun résultat. Causes possibles :\n"
            "  - L'offre (job_id={}) n'existe pas dans la table jobs.\n"
            "  - Aucun candidat avec le domaine '{}' (categorie_profil={}).".format(
                args.job_id or "?", args.domaine, normalize_categorie_profil(args.domaine)
            )
        )
    else:
        for i, r in enumerate(out, 1):
            c = r["candidate"]
            print(f"{i}. {c.get('prenom')} {c.get('nom')} — score: {r['score']:.2f} — {r['detail']}")
