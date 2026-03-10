import ast
import os
import sys

import pandas as pd
from sentence_transformers import SentenceTransformer, util
# Accès aux modules backend (weighted_matching, database)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from A4.weighted_matching import load_candidates_for_domaine, load_job_criteria

# ─────────────────────────────────────────────────────────────
# 1. CHARGEMENT
# ─────────────────────────────────────────────────────────────
model = SentenceTransformer('bert-base-nli-mean-tokens')

# Domaine choisi par le recruteur : DATA, DEV, DESIGN, VIDEO, AUTRE. None = tous les candidats.
def load_candidates_df(domaine_activite=None):
    """
    Charge les candidats depuis la DB selon le domaine choisi par le recruteur.
    domaine_activite: "DATA" | "DEV" | "DESIGN" | "VIDEO" | "AUTRE" | None (tous)
    Retourne un DataFrame avec colonnes: candidate_id, name, skills, languages, experience.
    """
    raw = load_candidates_for_domaine((domaine_activite or "").strip().upper() or None)
    rows = []
    for r in raw:
        rows.append({
            "candidate_id": r["id"],
            "id_agent": r.get("id_agent") or "",
            "candidate_uuid": r.get("candidate_uuid") or r.get("id_agent") or "",
            "name": f"{r.get('prenom', '')} {r.get('nom', '')}".strip() or r.get("id_agent", ""),
            "prenom": r.get("prenom") or "",
            "nom": r.get("nom") or "",
            "categorie_profil": r.get("categorie_profil") or "",
            "skills": r.get("skills") or [],
            "languages": r.get("languages") or [],
            "experience": int(r["annees_experience"]) if r.get("annees_experience") is not None else 0,
            "seniority": r.get("seniority") or "",
            "pret_a_relocater": r.get("pret_a_relocater") or "",
            "disponibilite": r.get("disponibilite") or "",
            "pays_cible": r.get("pays_cible") or "",
            "titre_profil": r.get("titre_profil") or "",
            "realisations": r.get("realisations") or [],
            "contract_types": r.get("contract_types") or [],
            "niveau_seniorite": r.get("niveau_seniorite") or "",
            "annees_experience": r.get("annees_experience") or 0,
            "constraints": r.get("constraints") or "",
            "search_criteria": r.get("search_criteria") or "",
            "salaire_minimum": r.get("salaire_minimum") or "",
        })
    return pd.DataFrame(rows)


def _safe_str(v):
    if v is None:
        return ""
    return str(v).strip() if isinstance(v, str) else str(v)


def _parse_experience_min(value):
    """Parse experience_min (ex. '1', '1 an', '2 ans', '3-5 ans') en nombre d'années."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return 0
    if isinstance(value, (int, float)) and value >= 0:
        return int(value)
    s = str(value).strip()
    numbers = re.findall(r"\d+\.?\d*", s)
    if numbers:
        try:
            return int(float(numbers[0]))
        except (ValueError, TypeError):
            pass
    return 0


def _parse_salary_amount(value):
    """Parse un montant salaire (int/float/str) en nombre, sinon None."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else None
    nums = re.findall(r"\d+", str(value))
    if not nums:
        return None
    try:
        return float("".join(nums))
    except (ValueError, TypeError):
        return None


def _candidate_salary_reference(candidate: dict):
    """
    Retourne la meilleure valeur salaire candidat disponible :
    1) colonne salaire_minimum
    2) extraction depuis constraints/search_criteria
    """
    direct = candidate.get("salaire_minimum")
    if _parse_salary_amount(direct) is not None:
        return direct

    text = " ".join(
        [
            str(candidate.get("constraints") or ""),
            str(candidate.get("search_criteria") or ""),
        ]
    ).strip()
    if not text:
        return None

    # Priorité aux formulations explicites "salaire minimum 8000"
    m = re.search(r"salaire\s*minimum[^\d]{0,20}(\d[\d\s\.,]*)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1)

    # Fallback: accepter seulement des montants plausibles proches de "salaire/remuneration"
    m2 = re.search(
        r"(?:salaire|r[eé]mun[eé]ration|pretention|pr[eé]tention)[^\d]{0,30}(\d{4,6})",
        text,
        flags=re.IGNORECASE,
    )
    if m2:
        return m2.group(1)
    return None


def get_job_offer_from_job_id(job_id):
    """
    Construit un job_offer à partir de la table jobs : clés pour le matching
    (mandatory_skills, required_*) + colonnes brutes (title, presence_sur_site, reason, etc.).
    """
    criteria = load_job_criteria(job_id)
    if not criteria:
        return None
    exp = _parse_experience_min(criteria.get("experience_min"))
    lang_list = criteria.get("languages") or []
    required_languages = [x.get("name", x) if isinstance(x, dict) else str(x) for x in lang_list if x]
    # Séniorité : utiliser UNIQUEMENT niveau_seniorite (Junior/Senior/Lead...). niveau_attendu = études (Bac+5), pas la séniorité.
    # Si vide → pas de contrainte → score 1.0 pour tous.
    required_seniority = _safe_str(criteria.get("niveau_seniorite"))
    required_disponibilite = _safe_str(criteria.get("disponibilite"))
    required_pret_a_relocater = _safe_str(criteria.get("presence_sur_site"))  # ou dédiée si ajoutée plus tard

    return {
        # — Clés utilisées par le matching —
        "mandatory_skills": criteria.get("skills_obligatoires") or [],
        "required_experience": exp,
        "required_languages": required_languages,
        "required_seniority": required_seniority,
        "required_title": _safe_str(criteria.get("title")),
        "required_disponibilite": required_disponibilite,
        "required_contrat": _safe_str(criteria.get("contrat")),
        "required_pret_a_relocater": required_pret_a_relocater,
        "required_pays_cible": _safe_str(criteria.get("pays_cible")),
        "required_salary_min": criteria.get("salary_min"),
        "required_salary_max": criteria.get("salary_max"),
        "required_resume_bref": _safe_str(criteria.get("reason") or criteria.get("main_mission")),
        # — Colonnes brutes table jobs (types respectés) —
        "id": criteria.get("id"),
        "title": _safe_str(criteria.get("title")),
        "niveau_attendu": _safe_str(criteria.get("niveau_attendu")),
        "niveau_seniorite": _safe_str(criteria.get("niveau_seniorite")),
        "experience_min": criteria.get("experience_min"),
        "presence_sur_site": _safe_str(criteria.get("presence_sur_site")),
        "reason": _safe_str(criteria.get("reason")),
        "main_mission": _safe_str(criteria.get("main_mission")),
        "tasks_other": _safe_str(criteria.get("tasks_other")),
        "disponibilite": required_disponibilite,
        "salary_min": criteria.get("salary_min"),
        "salary_max": criteria.get("salary_max"),
        "urgent": criteria.get("urgent"),
        "location_type": criteria.get("location_type"),
        "tasks": criteria.get("tasks"),
        "soft_skills": criteria.get("soft_skills"),
        "skills": criteria.get("skills_obligatoires"),  # liste déjà parsée ; raw JSON = row dans weighted_matching
        "languages": criteria.get("languages"),
        "contrat": _safe_str(criteria.get("contrat")),
        "domaine_activite": _safe_str(criteria.get("domaine_activite")),
        "categorie_profil": _safe_str(criteria.get("categorie_profil")),
    }



def semantic_skill_match_score(candidate_skills: list, job_skills: list) -> float:
    if not job_skills or not candidate_skills:
        return 1.0 if not job_skills else 0.0
    c_emb = model.encode(candidate_skills)
    j_emb = model.encode(job_skills)
    matched = sum(1 for je in j_emb if max(util.pytorch_cos_sim(je, c_emb)[0]).item() >= 0.7)
    return matched / len(job_skills)


def get_missing_skills(candidate_skills: list, job_skills: list) -> list:
    if not job_skills or not candidate_skills:
        return job_skills
    c_emb = model.encode(candidate_skills)
    j_emb = model.encode(job_skills)
    return [skill for skill, je in zip(job_skills, j_emb)
            if max(util.pytorch_cos_sim(je, c_emb)[0]).item() < 0.7]



def experience_score(candidate_exp: int, required_exp: int) -> float:
    if required_exp == 0:
        return 1.0
    return min(candidate_exp / required_exp, 1.0)




def language_score(candidate_languages: list, required_languages: list) -> float:
    if not required_languages:
        return 1.0
    c = {l.lower() for l in candidate_languages}
    r = [l.lower() for l in required_languages]
    return sum(1 for l in r if l in c) / len(r)


# Ordre séniorité (plus l'indice est grand, plus c'est senior)
SENIORITY_ORDER = ["Junior", "Débutant", "Mid", "Intermédiaire", "Senior", "Avancé", "Lead", "Expert"]


def _seniority_level(name: str) -> int:
    if not name or not isinstance(name, str):
        return -1
    n = (name or "").strip().lower()
    for i, level in enumerate(SENIORITY_ORDER):
        if level.lower() == n or level.lower() in n or n in level.lower():
            return i
    return -1


def seniority_score(candidate_seniority: str, required_seniority: str) -> float:
    """Score 0–1 : niveau candidat >= niveau demandé."""
    if not required_seniority:
        return 1.0
    j_level = _seniority_level(required_seniority)
    c_level = _seniority_level(candidate_seniority or "")
    if j_level < 0:
        return 0.5
    if c_level < 0:
        return 0.3
    return 1.0 if c_level >= j_level else max(0.0, 0.4 + 0.6 * (c_level / max(1, len(SENIORITY_ORDER))))


def _presence_mode(text: str) -> str:
    t = (text or "").strip().lower()
    if not t:
        return "unknown"
    # Remote
    if "distance" in t or "remote" in t or "télétravail" in t or "teletravail" in t:
        return "remote"
    # Hybride
    if "hybr" in t:
        return "hybrid"
    # Présentiel / présence obligatoire
    if "présence" in t or "presence" in t or "sur site" in t or "site" in t or "obligatoire" in t:
        return "onsite"
    return "unknown"


def pret_a_relocater_score(candidate: str, job_presence_sur_site: str, candidate_constraints: str = "") -> float:
    """
    Score 0–1 : compatibilité job `presence_sur_site` vs candidat `pret_a_relocater` (Oui/Non).

    Règle métier demandée :
    - Si le job est "à distance" => OK même si le candidat n'est pas prêt à relocaliser.
    - Si le job est "hybride" ou "présence obligatoire" => si candidat pas prêt à relocaliser => pas de match.
    """
    mode = _presence_mode(job_presence_sur_site)
    c = (candidate or "").strip().lower()
    constraints = (candidate_constraints or "").strip().lower()

    # Si l'offre ne précise rien, score neutre
    if mode == "unknown":
        return 0.5

    # Remote => compatible
    if mode == "remote":
        return 1.0

    # Hybride/présentiel : il faut être prêt (oui / à discuter)
    willing = ("oui" in c) or ("discut" in c)
    if willing:
        return 1.0

    # Candidat non prêt à relocaliser => pas de match sur hybride/présentiel
    # (si en plus ses contraintes demandent explicitement le remote, on reste à 0.0)
    if "distance" in constraints or "remote" in constraints or "télétravail" in constraints or "teletravail" in constraints:
        return 0.0
    return 0.0


def disponibilite_score(candidate: str, required: str) -> float:
    """Score 0–1 : match disponibilité (exact ou contient)."""
    if not required:
        return 1.0
    if not candidate:
        return 0.0
    c = (candidate or "").strip().lower()
    r = (required or "").strip().lower()
    if c == r:
        return 1.0
    if r in c or c in r:
        return 0.9
    return 0.0


def pays_cible_score(candidate: str, required: str) -> float:
    """Score 0–1 : match pays cible (exact ou contient)."""
    if not required:
        return 1.0
    if not candidate:
        return 0.0
    c = (candidate or "").strip().lower()
    r = (required or "").strip().lower()
    if c == r:
        return 1.0
    if r in c or c in r:
        return 0.9
    return 0.0


def _titre_has_shared_word(job_title: str, candidate_titre: str) -> bool:
    """True si les deux titres partagent au moins un mot significatif (hors stopwords)."""
    stop = {"le", "la", "les", "de", "du", "des", "et", "en", "au", "aux", "un", "une", "the", "a", "an"}
    j_words = {w.lower() for w in re.findall(r"\w+", job_title or "") if len(w) > 1 and w.lower() not in stop}
    c_words = {w.lower() for w in re.findall(r"\w+", candidate_titre or "") if len(w) > 1 and w.lower() not in stop}
    return bool(j_words & c_words)


def titre_profil_score(candidate_titre: str, job_title: str) -> float:
    """
    Score 0–1 : similarité titre profil candidat vs titre du poste.
    Piloté par BERT (flexible, s’adapte à tous les profils). Pénalité légère uniquement
    quand aucun mot n’est en commun, pour limiter les faux positifs évidents.
    """
    if not job_title or not candidate_titre:
        return 0.5 if (job_title or candidate_titre) else 0.0
    j = (job_title or "").strip().lower()
    c = (candidate_titre or "").strip().lower()
    if j == c:
        return 1.0
    if j in c or c in j:
        return 0.9
    try:
        emb_j = model.encode([(job_title or "").strip()])
        emb_c = model.encode([(candidate_titre or "").strip()])
        sim = util.pytorch_cos_sim(emb_j, emb_c)[0].item()
        semantic = float(max(0.0, min(1.0, (sim + 1) / 2)))
        # Pas de liste statique : on fait confiance au modèle. Légère pénalité (15 %) seulement si aucun mot en commun.
        if not _titre_has_shared_word(job_title, candidate_titre):
            semantic = semantic * 0.85
        return semantic
    except Exception:
        return 0.3


def contract_score(candidate_contract_types: list, required_contrat: str) -> float:
    """Score 0–1 : le type de contrat demandé est dans les types acceptés par le candidat."""
    if not required_contrat:
        return 1.0
    if not candidate_contract_types:
        return 0.0
    r = (required_contrat or "").strip().lower()
    for ct in (candidate_contract_types or []):
        c = (ct or "").strip().lower()
        if c == r or r in c or c in r:
            return 1.0
    return 0.0


def realisations_score(candidate_realisations: list, job_title: str, job_resume: str) -> float:
    """Score 0–1 : similarité sémantique des réalisations avec le titre/résumé du poste (BERT)."""
    if not candidate_realisations:
        return 0.5
    job_text = " ".join(filter(None, [(job_title or "").strip(), (job_resume or "").strip()]))
    if not job_text:
        return 0.5
    realisations_text = " ".join(str(r) for r in candidate_realisations if r)[:2000]
    if not realisations_text:
        return 0.5
    try:
        emb_j = model.encode([job_text])
        emb_r = model.encode([realisations_text])
        sim = util.pytorch_cos_sim(emb_j, emb_r)[0].item()
        return float(max(0.0, min(1.0, (sim + 1) / 2)))
    except Exception:
        return 0.3


def salaire_minimum_score(candidate_salary_min, job_salary_min, job_salary_max=None) -> float:
    """
    Score 0–1 : compatibilité entre salaire minimum candidat et budget de l'offre.
    - Match parfait si le salaire mini du candidat est couvert.
    - Sinon score proportionnel.
    - Donnée manquante d'un côté => score neutre.
    """
    c_min = _parse_salary_amount(candidate_salary_min)
    j_min = _parse_salary_amount(job_salary_min)
    j_max = _parse_salary_amount(job_salary_max)

    if c_min is None or (j_min is None and j_max is None):
        return 0.5

    ref_budget = j_max if j_max is not None else j_min
    if ref_budget is None or c_min <= 0:
        return 0.5

    if c_min <= ref_budget:
        return 1.0
    return max(0.0, min(ref_budget / c_min, 1.0))


# Poids par défaut pour le matching multi-critères (somme = 1.0)
DEFAULT_WEIGHTS = {
    "skills": 0.24,
    "experience": 0.15,
    "languages": 0.12,
    "seniority": 0.10,
    "titre_profil": 0.10,
    "disponibilite": 0.07,
    "contract_types": 0.06,
    "pret_a_relocater": 0.06,
    "pays_cible": 0.03,
    "realisations": 0.03,
    "salaire_minimum": 0.04,
}


def calculate_global_score(candidate: dict, job_offer: dict, weights: dict = None):
    """
    Score global basé sur tous les critères candidat :
    skills, languages, experience, seniority, pret_a_relocater, disponibilite,
    pays_cible, titre_profil, realisations, contract_types, salaire_minimum.
    """
    w = weights or DEFAULT_WEIGHTS
    skills = candidate.get("skills") or []
    languages = candidate.get("languages") or []
    exp = int(candidate.get("experience") or candidate.get("annees_experience") or 0)
    seniority = (candidate.get("niveau_seniorite") or candidate.get("seniority") or "").strip() or ""
    pret_a_relocater = (candidate.get("pret_a_relocater") or "").strip() or ""
    disponibilite = (candidate.get("disponibilite") or "").strip() or ""
    pays_cible = (candidate.get("pays_cible") or "").strip() or ""
    titre_profil = (candidate.get("titre_profil") or "").strip() or ""
    realisations = candidate.get("realisations") or []
    contract_types = candidate.get("contract_types") or []
    salaire_minimum = _candidate_salary_reference(candidate)

    s_skills = semantic_skill_match_score(skills, job_offer.get("mandatory_skills") or [])
    s_exp = experience_score(exp, job_offer.get("required_experience") or 0)
    s_lang = language_score(languages, job_offer.get("required_languages") or [])
    s_seniority = seniority_score(seniority, (job_offer.get("required_seniority") or "").strip())
    s_pret = pret_a_relocater_score(
        pret_a_relocater,
        (job_offer.get("presence_sur_site") or job_offer.get("required_pret_a_relocater") or "").strip(),
        candidate.get("constraints") or "",
    )
    s_disp = disponibilite_score(disponibilite, (job_offer.get("required_disponibilite") or "").strip())
    s_pays = pays_cible_score(pays_cible, (job_offer.get("required_pays_cible") or "").strip())
    s_titre = titre_profil_score(titre_profil, (job_offer.get("required_title") or "").strip())
    s_contract = contract_score(contract_types, (job_offer.get("required_contrat") or "").strip())
    s_real = realisations_score(
        realisations,
        (job_offer.get("required_title") or "").strip(),
        (job_offer.get("required_resume_bref") or "").strip(),
    )
    s_salary = salaire_minimum_score(
        salaire_minimum,
        job_offer.get("required_salary_min"),
        job_offer.get("required_salary_max"),
    )

    total = (
        w.get("skills", 0) * s_skills
        + w.get("experience", 0) * s_exp
        + w.get("languages", 0) * s_lang
        + w.get("seniority", 0) * s_seniority
        + w.get("titre_profil", 0) * s_titre
        + w.get("disponibilite", 0) * s_disp
        + w.get("contract_types", 0) * s_contract
        + w.get("pret_a_relocater", 0) * s_pret
        + w.get("pays_cible", 0) * s_pays
        + w.get("realisations", 0) * s_real
        + w.get("salaire_minimum", 0) * s_salary
    )
    return {
        "skill_score": round(s_skills * 100, 1),
        "experience_score": round(s_exp * 100, 1),
        "language_score": round(s_lang * 100, 1),
        "seniority_score": round(s_seniority * 100, 1),
        "titre_profil_score": round(s_titre * 100, 1),
        "disponibilite_score": round(s_disp * 100, 1),
        "contract_score": round(s_contract * 100, 1),
        "pret_a_relocater_score": round(s_pret * 100, 1),
        "pays_cible_score": round(s_pays * 100, 1),
        "realisations_score": round(s_real * 100, 1),
        "salaire_minimum_score": round(s_salary * 100, 1),
        "global_score": round(total * 100, 1),
    }


# ─────────────────────────────────────────────────────────────
# 3. MOTEUR DE MATCHING
# ─────────────────────────────────────────────────────────────

def _row_to_candidate(row) -> dict:
    """Convertit une ligne DataFrame en dict candidat pour le scoring."""
    def parse_list(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return []
        if isinstance(v, str):
            try:
                return ast.literal_eval(v) if v.strip().startswith("[") else [x.strip() for x in v.split(",") if x.strip()]
            except (ValueError, SyntaxError):
                return [v] if v.strip() else []
        return list(v) if hasattr(v, "__iter__") and not isinstance(v, str) else []

    return {
        "candidate_id": row.get("candidate_id"),
        "name": row.get("name", ""),
        "skills": parse_list(row.get("skills")),
        "languages": parse_list(row.get("languages")),
        "experience": int(row["experience"]) if pd.notna(row.get("experience")) else int(row.get("annees_experience") or 0),
        "annees_experience": row.get("annees_experience") or row.get("experience") or 0,
        "seniority": (row.get("seniority") or "").strip() or "",
        "niveau_seniorite": (row.get("niveau_seniorite") or row.get("seniority") or "").strip() or "",
        "pret_a_relocater": (row.get("pret_a_relocater") or "").strip() or "",
        "disponibilite": (row.get("disponibilite") or "").strip() or "",
        "pays_cible": (row.get("pays_cible") or "").strip() or "",
        "titre_profil": (row.get("titre_profil") or "").strip() or "",
        "realisations": parse_list(row.get("realisations")),
        "contract_types": parse_list(row.get("contract_types")),
        "constraints": (row.get("constraints") or "").strip() if isinstance(row.get("constraints"), str) else str(row.get("constraints") or ""),
        "search_criteria": (row.get("search_criteria") or "").strip() if isinstance(row.get("search_criteria"), str) else str(row.get("search_criteria") or ""),
        "salaire_minimum": row.get("salaire_minimum"),
    }


def find_matching_candidates(job_offer, df, top_n=5, weights=None):
    """
    Matching basé sur tous les critères : skills, languages, experience, seniority,
    pret_a_relocater, disponibilite, pays_cible, titre_profil, realisations, contract_types, salaire_minimum.
    """
    results = []
    for _, row in df.iterrows():
        candidate = _row_to_candidate(row)
        scores = calculate_global_score(candidate, job_offer, weights)
        missing = get_missing_skills(candidate["skills"], job_offer.get("mandatory_skills") or [])
        results.append({
            "candidate_id": candidate["candidate_id"],
            "name": candidate["name"],
            "global_score": scores["global_score"],
            "skill_score": scores["skill_score"],
            "experience_score": scores["experience_score"],
            "language_score": scores["language_score"],
            "seniority_score": scores["seniority_score"],
            "titre_profil_score": scores["titre_profil_score"],
            "disponibilite_score": scores["disponibilite_score"],
            "contract_score": scores["contract_score"],
            "pret_a_relocater_score": scores["pret_a_relocater_score"],
            "pays_cible_score": scores["pays_cible_score"],
            "realisations_score": scores["realisations_score"],
            "salaire_minimum_score": scores["salaire_minimum_score"],
            "missing_skills": ", ".join(missing) if missing else "Aucune",
        })
    return (
        pd.DataFrame(results)
        .sort_values("global_score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test matching candidats par domaine (DB)")
    parser.add_argument("--domaine", default="DEV", help="Domaine: DATA, DEV, DESIGN, VIDEO, AUTRE (ou vide = tous)")
    parser.add_argument("--job-id", type=int, default=None, help="ID de l'offre en base (table jobs). Si absent, offre factice utilisée.")
    parser.add_argument("--top", type=int, default=5, help="Nombre de candidats à retourner (défaut: 5)")
    args = parser.parse_args()
    domaine = (args.domaine or "").strip().upper() or None

    print("Chargement des candidats (domaine = %r)..." % (domaine or "tous"))
    df = load_candidates_df(domaine)
    print("  -> %d candidat(s) chargé(s)" % len(df))
    if df.empty:
        print("Aucun candidat. Vérifiez la DB et categorie_profil des candidats.")
        sys.exit(1)

    if args.job_id:
        print("Chargement de l'offre job_id=%d..." % args.job_id)
        job_offer = get_job_offer_from_job_id(args.job_id)
        if not job_offer:
            print("  -> Offre introuvable, utilisation d'une offre factice.")
            job_offer = {"mandatory_skills": ["Python"], "required_experience": 0, "required_languages": []}
        else:
            print("  -> mandatory_skills=%s, required_experience=%s, required_seniority=%r" % (job_offer["mandatory_skills"], job_offer["required_experience"], job_offer.get("required_seniority", "")))
    else:
        job_offer = {
            "mandatory_skills": ["Python", "SQL"],
            "required_experience": 2,
            "required_languages": ["Français"],
        }
        print("Offre factice: mandatory_skills=%s, required_experience=%s" % (job_offer["mandatory_skills"], job_offer["required_experience"]))

    print("Calcul des scores (modèle BERT, peut prendre quelques secondes)...")
    results = find_matching_candidates(job_offer, df, top_n=args.top)
    print("\nTop %d candidats:\n" % len(results))
    print(results.to_string())
