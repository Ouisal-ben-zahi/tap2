#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
from copy import deepcopy
import google.generativeai as genai
import io
import zipfile
import xml.etree.ElementTree as ET

# Import robuste: fonctionne en mode module (python -m B1.generate_corrected_cv)
# Import depuis B1.test (fonctionne dans Docker et en exécution directe)
try:
    from B1.test import generer_cv  # type: ignore
except ImportError:
    # Fallback si B1.test n'est pas trouvé (exécution depuis le dossier B1)
    import sys
    import os
    # Ajouter le répertoire parent au path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from B1.test import generer_cv  # type: ignore

# Template HTML (Jinja2)
try:
    from jinja2 import Template
    JINJA2_AVAILABLE = True
except Exception:
    JINJA2_AVAILABLE = False

# Legacy docx (optionnel)
try:
    from docxtpl import DocxTemplate, RichText
    DOCXTPL_AVAILABLE = True
except Exception:
    DOCXTPL_AVAILABLE = False
try:
    from docx import Document
    PYDOCX_AVAILABLE = True
except Exception:
    PYDOCX_AVAILABLE = False

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"[0-9+\s().-]{6,}")

# ---------- Helpers ----------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def validate_email(email):
    return bool(email and EMAIL_RE.match(email.strip()))

def validate_phone(phone):
    if not phone:
        return False
    return bool(PHONE_RE.search(str(phone)))

def ensure_int_years(x):
    try:
        if x is None or x == "":
            return None
        if isinstance(x, int):
            return x
        if isinstance(x, float):
            return int(x)
        m = re.search(r"\d+", str(x))
        if m:
            return int(m.group(0))
    except Exception:
        pass
    return None

def _formation_sort_key(period_str):
    """Extrait une année pour tri (plus récent = plus grand). Période 'En cours' / 'présent' = année actuelle."""
    if not period_str or not isinstance(period_str, str):
        return 0
    s = period_str.strip().lower()
    if "cours" in s or "présent" in s or "present" in s or "actuel" in s:
        return 9999  # en cours = plus récent
    numbers = re.findall(r"\d{4}", s)
    return int(numbers[-1]) if numbers else 0


def truncate_one_line(text, max_chars=240):
    if not text:
        return ""
    s = str(text).strip().replace("\n", " ").replace("\r", " ")
    if len(s) <= max_chars:
        return s
    cut = s[:max_chars].rsplit(" ", 1)[0]
    return cut + "..."

def extract_json_from_text(text):
    text = text.strip()
    start = None
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            start = i
            break
    if start is None:
        raise ValueError("No JSON object found in model output")
    stack = []
    pairs = {"{": "}", "[": "]"}
    for i in range(start, len(text)):
        ch = text[i]
        if ch in ("{", "["):
            stack.append(pairs[ch])
        elif stack and ch == stack[-1]:
            stack.pop()
            if not stack:
                candidate_json = text[start:i+1]
                candidate_json = re.sub(r"^```(?:json)?\s*", "", candidate_json)
                candidate_json = re.sub(r"\s*```$", "", candidate_json)
                return candidate_json
    last_close = text.rfind("}")
    if start is not None and last_close != -1:
        candidate_json = text[start:last_close+1]
        candidate_json = re.sub(r"^```(?:json)?\s*", "", candidate_json)
        candidate_json = re.sub(r"\s*```$", "", candidate_json)
        return candidate_json
    raise ValueError("Could not parse JSON from model output")

# ---------- LLM interaction (Gemini) ----------

def prepare_prompt(analysis, cv_text: str | None = None, feedback_comments: str | None = None):
    instr = """
        Vous êtes un expert senior en recrutement et optimisation de CV.

        Vous recevez :
        1) une fiche candidat (JSON) contenant des informations brutes
        2) le texte du CV original (non optimisé)
        3) des commentaires de feedback du client (si disponibles) pour améliorer le CV

        OBJECTIF :
        Analyser le CV de manière critique puis RECONSTRUIRE un CV professionnel,
        clair, cohérent et optimisé pour le recrutement.

        ⚠️ INTERDICTION ABSOLUE :
        - Ne pas copier-coller les phrases du CV original
        - Ne pas reproduire mot pour mot les descriptions existantes
        - Toute description doit être reformulée, améliorée et professionnalisée

        ÉTAPE 1 — ANALYSE (interne, ne pas afficher) :
        Analysez le CV et identifiez :
        - informations manquantes ou floues
        - incohérences (dates, titres, niveaux)
        - faiblesses de formulation
        - points forts du profil
        - améliorations possibles (clarté, impact, valeur métier)

        ÉTAPE 2 — CORRECTION & OPTIMISATION :
        À partir de cette analyse :
        - complétez les informations manquantes si possible
        - reformulez toutes les descriptions avec un langage professionnel
        - mettez en valeur l’impact, les compétences et la valeur ajoutée
        - utilisez des verbes d’action (développé, conçu, optimisé, automatisé…)
        - supprimez les répétitions et les formulations vagues
        - adaptez le contenu à un CV moderne et lisible

        FORMAT DE SORTIE :
        Vous devez retourner UNIQUEMENT un JSON valide
        en respectant STRICTEMENT la structure suivante :

        {
        "Name": "",
        "Titre": "",
        "Tele": "",
        "Email": "",
        "Linkedin": "",
        "Ville": "",
        "Pays": "",
        "resume": "",
        "Skill": "",
        "Experiences": [
            { "title": "", "company": "", "period": "", "description": "" }
        ],
        "Educations": [
            { "degree": "", "school": "", "period": "" },
            { "degree": "", "school": "", "period": "" }
        ],
        "Realisations": [
            { "nom": "", "contexte": "", "stack": "", "detail": "" }
        ],
        "Certificats": [
            { "titre": "", "date": "" }
        ],
        "Langues": [
            { "langue": "", "niveau": "" }
        ]
        }

        RÈGLES STRICTES :
        - Tous les champs doivent être présents
        - "" pour les chaînes vides, [] pour les listes vides
        - Maximum 12 compétences
        - EXPÉRIENCES / RÉALISATIONS (adapter selon le profil) :
          * Si le candidat n'a PAS d'expérience ou a au max 2 expériences : au max 4 réalisations (projets) ; Experiences peut être vide ou court.
          * Si le candidat a PLUS de 2 expériences : au max 4 expériences ET au max 2 réalisations (projets).
        - Pour chaque réalisation : remplir "contexte" (ex. projet académique, stage, mission client), "stack" (technologies utilisées, ex. Python, React, SQL) et "detail" (résultat / description).
        - Description d'expérience : 3 points maximum chacun 6 mots maximum
        - Résumé : max 280 caractères
        - Contenu professionnel, clair et orienté valeur
        - Aucune phrase copiée mot pour mot depuis le CV original
        - FORMATIONS (Educations) : extraire TOUTES les formations du CV et renseigner au moins les 2 plus RÉCENTES (degree = diplôme/intitulé, school = établissement, period = ex. 09/2024 – En cours ou 2020–2022). Si le CV n'en contient qu'une, ne remplir qu'un seul élément ; sinon toujours fournir les 2 dernières formations.

        IMPORTANT :
        Retournez UNIQUEMENT le JSON final.
        Aucune explication, aucun texte hors JSON.
        """

    
    # Structure JSON d'exemple pour référence
    example_structure = {
    "Name": "Jean Dupont",
    "Titre": "Développeur Python Fullstack",
    "Tele": "06 00 00 00 00",
    "Email": "jean.dupont@email.com",
    "Linkedin": "linkedin.com/in/jeandupont",
    "Ville": "Paris",
    "Pays": "France",
    "resume": "Développeur passionné avec 5 ans d'expérience dans la conception d'applications web et d'APIs performantes.",
    "Skill": "Python\nSQL\nDocker\nReact\nFastAPI\nPostgreSQL\nGit",
    "Experiences": [ 
         { "title": "Développeur Python Fullstack", "company": "TechCorp", "period": "2021–2024", "description": "Développement d’APIs REST et intégration front React \n" },
         { "title": "Développeur Backend Python", "company": "DataSolutions", "period": "2020–2021", "description": "Microservices et traitement de données \n" } ], 
    "Educations": [ 
        { "degree": "Master en Informatique \n", "school": "Université de Paris \n", "period": "2018–2020 \n" }, 
        { "degree": "Licence en Informatique \n", "school": "Université Paris Descartes \n", "period": "2015–2018 \n" } 
    ],
    "Realisations": [
        {
            "nom": "Plateforme E-commerce",
            "contexte": "Projet client e-commerce B2B",
            "stack": "FastAPI, Docker, PostgreSQL, React",
            "detail": "Développement d'une architecture microservices avec FastAPI et Docker."
        },
        {
            "nom": "Outil d'Automatisation",
            "contexte": "Amélioration CI/CD interne",
            "stack": "Python, GitLab CI, Bash",
            "detail": "Création d'un script de déploiement continu réduisant le temps de mise en production de 40%."
        }
    ],
    "Certificats": [
        { "titre": "AWS Certified Cloud Practitioner", "date": "2024" },
        { "titre": "Certification Python (PCEP)", "date": "2023" }
    ],
    "Langues": [
        { "langue": "Français", "niveau": "Courant" },
        { "langue": "Anglais", "niveau": "Intermédiaire" }
    ]
}
    
    # Dans ce projet: `analysis` correspond au JSON de l'agent A1 (Talent Card).
    # On l'utilise comme "fiche candidat".
    candidate = analysis or {}

    prompt = instr
    prompt += "\n\nExemple de structure JSON attendue :\n" + json.dumps(example_structure, ensure_ascii=False, indent=2)
    prompt += "\n\nFiche candidat à corriger :\n" + json.dumps(candidate, ensure_ascii=False, indent=2)
    # Pas d'analyse séparée ici (A1 output = fiche candidat). On garde un bloc vide pour compatibilité avec l'instruction.
    prompt += "\n\nAnalyse du premier agent :\n{}"
    # Mémoire des validations utilisateur : l'agent apprend des rejets/révisions passés
    try:
        from agent_memory import get_memory_for_prompt
        memory = get_memory_for_prompt("B1", max_items=10)
        if memory:
            prompt += memory
    except Exception:
        pass
    if cv_text:
        # Garder un prompt raisonnable (éviter d'exploser le contexte)
        cv_text_clean = str(cv_text).strip()
        max_chars = 12000
        if len(cv_text_clean) > max_chars:
            cv_text_clean = cv_text_clean[:max_chars] + "\n...[TRONQUÉ]..."
        prompt += "\n\nContenu du CV original (extrait texte, pour mieux corriger et compléter) :\n" + cv_text_clean
    if feedback_comments and feedback_comments.strip():
        prompt += "\n\n⚠️ COMMENTAIRES DU CLIENT POUR AMÉLIORATION :\n"
        prompt += "Le client a demandé les modifications suivantes sur la version précédente du CV :\n"
        prompt += feedback_comments.strip()
        prompt += "\n\nIMPORTANT : Vous devez tenir compte de ces commentaires et améliorer le CV en conséquence."
        prompt += "\nAssurez-vous de corriger tous les points mentionnés dans les commentaires."
    prompt += "\n\nRetournez UNIQUEMENT le JSON final en respectant EXACTEMENT la structure fournie ci-dessus.\n"
    return prompt

def call_gemini_chat(prompt, model=None, max_tokens=10000, temperature=0.2):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable is not set.")
    genai.configure(api_key=api_key)
    model_name = model or os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
    generation_config = genai.types.GenerationConfig(
        temperature=temperature,        
        max_output_tokens=max_tokens,
        response_mime_type="application/json",
    )
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction="You are a helpful assistant that outputs strict JSON when asked."
    )
    
    
    max_retries = 3
    retry_delay = 2
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            
            if not response.candidates:
                raise RuntimeError("No candidates returned in the response.")
            
            # Si on arrive ici, l'appel a réussi, sortir de la boucle
            break
            
        except Exception as e:
            last_error = e
            error_message = str(e)
            
            # Vérifier si c'est une erreur temporaire (500, rate limit, etc.)
            if "500" in error_message or "InternalServerError" in error_message or "overloaded" in error_message:
                if attempt < max_retries - 1:
                    print(f"⚠️  Erreur temporaire Gemini (tentative {attempt + 1}/{max_retries}): {error_message}")
                    print(f"🔄 Nouvelle tentative dans {retry_delay} secondes...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponentiel
                    continue
                else:
                    print(f"❌ Échec après {max_retries} tentatives: {error_message}")
                    raise
            else:
                # Pour les autres erreurs, ne pas réessayer
                raise
    
    if not response.candidates:
        raise RuntimeError("No candidates returned in the response.")
    candidate = response.candidates[0]
    finish_reason = getattr(candidate, "finish_reason", None)
    # Treat common cases
    if finish_reason == 1:  # STOP
        try:
            return response.text
        except Exception:
            if getattr(candidate, "content", None) and candidate.content.parts:
                return candidate.content.parts[0].text
            raise RuntimeError("Could not extract text from response.")
    elif finish_reason == 2:
        # MAX_TOKENS -> try to return partial
        if getattr(candidate, "content", None) and candidate.content.parts:
            partial_text = candidate.content.parts[0].text
            if partial_text:
                print("Warning: response truncated (max tokens). Returning partial.", file=sys.stderr)
                return partial_text
        raise RuntimeError("Response truncated (MAX_TOKENS). Increase max_tokens.")
    elif finish_reason == 3:
        raise RuntimeError("Response blocked by safety filters.")
    else:
        # If finish_reason is None or unknown, try to return text fields defensively
        try:
            return response.text
        except Exception:
            if getattr(candidate, "content", None) and candidate.content.parts:
                return candidate.content.parts[0].text
            raise RuntimeError(f"LLM finish_reason={finish_reason}")

def call_llm(prompt, provider="gemini", **kwargs):
    if provider == "gemini":
        return call_gemini_chat(prompt, **kwargs)
    else:
        raise ValueError("Provider non supporté.")


def safe_str(value, join_lists_with=", "):
    """Convert value to a safe string for templates:
       - lists become joined strings
       - None -> ""
       - dict -> JSON string
       - otherwise str(value).strip()
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        # flatten inner values to strings
        return join_lists_with.join([str(x).strip() for x in value if x is not None and str(x).strip()])
    if isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    return str(value).strip()


def _split_name(full_name):
    """
    Split full name into (prenom, nom): premier mot = prénom, le reste = nom.
    Ex: "HAJAR EL AOUNI" -> ("HAJAR", "EL AOUNI"), "Jean Dupont" -> ("Jean", "Dupont").
    """
    if not full_name or not isinstance(full_name, str):
        return "", ""
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def transform_corrected_json_to_cv_context(corrected):
    """
    Transforme le JSON corrigé (sortie LLM B1) en contexte pour le template Jinja2 CV_template_A4.html.
    """
    name = (corrected.get("Name") or "").strip()
    prenom, nom = _split_name(name)
    skill_raw = corrected.get("Skill") or ""
    skills = [
        s.strip()
        for s in (skill_raw.replace("\n", ",").split(","))
        if s.strip()
    ][:12]

    experiences = []
    for exp in corrected.get("Experiences") or []:
        if not isinstance(exp, dict):
            continue
        desc = (exp.get("description") or "").strip()
        points = [p.strip() for p in desc.split("\n") if p.strip()] if desc else []
        experiences.append({
            "role": (exp.get("title") or "").strip(),
            "Role": (exp.get("title") or "").strip(),
            "entreprise": (exp.get("company") or "").strip(),
            "periode": (exp.get("period") or "").strip(),
            "description": desc,
            "points": points[:5],
        })

    formations = []
    for edu in corrected.get("Educations") or []:
        if not isinstance(edu, dict):
            continue
        period = (edu.get("period") or "").strip()
        formations.append({
            "diplome": (edu.get("degree") or "").strip(),
            "diploma": (edu.get("degree") or "").strip(),
            "etablissement": (edu.get("school") or "").strip(),
            "ecole": (edu.get("school") or "").strip(),
            "annee": period,
            "year": period,
        })
    # Garder uniquement les 2 formations les plus récentes (tri par année de fin / période)
    formations.sort(key=lambda f: _formation_sort_key(f.get("annee") or f.get("year")))
    formations = formations[-2:]

    projets = []
    for r in corrected.get("Realisations") or []:
        if not isinstance(r, dict):
            continue
        projets.append({
            "nom": (r.get("nom") or "").strip(),
            "detail": (r.get("detail") or "").strip(),
            "resultat": (r.get("detail") or "").strip(),
            "contexte": (r.get("contexte") or "").strip(),
            "stack": (r.get("stack") or "").strip(),
        })

    langues = []
    for L in corrected.get("Langues") or []:
        if not isinstance(L, dict):
            continue
        langues.append({
            "nom": (L.get("langue") or "").strip(),
            "niveau": (L.get("niveau") or "").strip(),
        })

    # nom_complet = nom affiché tel quel (évite "AOUNI HAJAR EL" pour "HAJAR EL AOUNI")
    nom_complet = name

    candidate = {
        "nom": nom,
        "prenom": prenom,
        "nom_complet": nom_complet,
        "titre_profil": (corrected.get("Titre") or "").strip(),
        "Titre de profil": (corrected.get("Titre") or "").strip(),
        "ville": (corrected.get("Ville") or "").strip(),
        "pays": (corrected.get("Pays") or "").strip(),
        "email": (corrected.get("Email") or "").strip(),
        "phone": (corrected.get("Tele") or "").strip(),
        "profil": (corrected.get("resume") or "").strip(),
        "resume_bref": (corrected.get("resume") or "").strip(),
        "profile_image_url": "",
        "skills": skills,
        "langues_parlees": [f"{l.get('nom', '')}: {l.get('niveau', '')}" for l in langues],
    }

    return {
        "candidate": candidate,
        "experiences": experiences,
        "projets": projets,
        "skills": skills,
        "formations": formations,
        "langues": langues,
        "soft_skills": [],
    }


def render_cv_html(html_template_path: str, context: dict, out_html_path: str) -> None:
    """
    Charge le template Jinja2 CV (format A4 : 21 cm × 29,7 cm), rend avec context, enregistre le HTML.
    La conversion en PDF est faite côté app avec le même format A4.
    """
    if not JINJA2_AVAILABLE:
        raise RuntimeError("Jinja2 est requis pour le template CV HTML.")
    with open(html_template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
    jinja_template = Template(template_content)
    html_content = jinja_template.render(**context)
    os.makedirs(os.path.dirname(out_html_path) or ".", exist_ok=True)
    with open(out_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"CV HTML généré : {out_html_path}")


def generate_corrected_cv(
    *,
    candidate: dict,
    analysis: dict | None,
    cv_text: str | None = None,
    template_path: str,
    out_html_path: str,
    out_json_path: str,
    provider: str = "gemini",
    model: str | None = None,
    feedback_comments: str | None = None,
):
    """
    Agent 2: génère un JSON corrigé (structure "profile/contact/...") puis produit un CV HTML depuis le template Jinja2.

    Returns:
        dict: {
          "corrected_json": <dict>,
          "normalized_flat": <dict>,
          "template_data": <dict>,
          "out_json_path": <str>,
          "out_html_path": <str>
        }
    """
    # `analysis` est attendu comme output JSON de l'agent A1.
    a1_payload = analysis if analysis else (candidate or {})

    prompt = prepare_prompt(a1_payload, cv_text=cv_text, feedback_comments=feedback_comments)
    llm_output = call_llm(prompt, provider=provider, model=model)

    json_text = extract_json_from_text(llm_output)
    corrected_from_llm = json.loads(json_text)
    corrected = corrected_from_llm

    save_json(corrected, out_json_path)
    print(f"JSON corrigé sauvegardé: {out_json_path}")

    template_data = corrected

    # Rendu du template HTML (CV_template_A4.html)
    cv_context = transform_corrected_json_to_cv_context(corrected)
    # Réinjecter ville, pays et photo depuis la fiche candidat (talentcard) si vides
    orig = a1_payload or {}
    c = cv_context.get("candidate") or {}
    if not (c.get("ville") or "").strip():
        c["ville"] = (orig.get("ville") or "").strip()
    if not (c.get("pays") or "").strip():
        c["pays"] = (orig.get("pays") or "").strip()
    if not (c.get("profile_image_url") or "").strip():
        c["profile_image_url"] = (orig.get("profile_image_url") or orig.get("image_minio_url") or orig.get("image_url") or "").strip()
    cv_context["candidate"] = c
    render_cv_html(template_path, cv_context, out_html_path)

    # Générer une explication de ce que l'agent B1 a fait
    experiences_count = len(corrected.get("Experiences", []))
    realisations_count = len(corrected.get("Realisations", []))
    skills_count = len(corrected.get("Skill", "").split(",")) if corrected.get("Skill") else 0
    
    agent_explanation = f"""🤖 Agent B1 - Génération du CV Corrigé

    Voici ce que j'ai fait pour créer ton CV corrigé optimisé :

    1️⃣ Analyse critique du CV original : J'ai identifié les points à améliorer (formulations, clarté, impact)

    2️⃣ Correction et optimisation : J'ai reformulé toutes les descriptions avec un langage professionnel et orienté valeur :
   - {experiences_count} expérience(s) professionnelle(s) optimisée(s)
   - {realisations_count} réalisation(s) mise(s) en avant avec impact
   - {skills_count} compétence(s) structurée(s) et priorisée(s)

        3️⃣ Reformulation complète : Toutes les descriptions ont été réécrites (pas de copier-coller) pour maximiser ton impact auprès des recruteurs

        4️⃣ Génération du document : J'ai créé un CV professionnel au format HTML (A4) optimisé pour les recruteurs

        5️⃣ Sauvegarde : Ton CV corrigé est prêt à être téléchargé (HTML/PDF) et validé

        Ton CV est maintenant optimisé pour attirer l'attention des recruteurs et maximiser tes chances d'entretien."""

    return {
        "corrected_json": corrected_from_llm,
        "normalized_flat": corrected,
        "template_data": template_data,
        "out_json_path": out_json_path,
        "out_html_path": out_html_path,
        "agent_explanation": agent_explanation,
    }


def main():
    parser = argparse.ArgumentParser(description="Agent 2: génère un CV corrigé (HTML A4) en utilisant un LLM.")
    parser.add_argument("--candidate", required=True, help="chemin vers candidate.json")
    parser.add_argument("--analysis", required=False, help="chemin vers analysis.json (optionnel)")
    parser.add_argument("--template", required=True, help="chemin vers le template HTML (ex: frontend/src/CV templates/CV_template_A4.html)")
    parser.add_argument("--out", default="outputs/corrected_cv.html", help="chemin de sortie .html")
    parser.add_argument("--out-json", default="outputs/corrected_data.json", help="chemin JSON de sortie")
    parser.add_argument("--provider", default="gemini", help="LLM provider (default: gemini)")
    parser.add_argument("--model", default=None, help="modèle LLM (optionnel)")
    args = parser.parse_args()

    candidate = load_json(args.candidate)
    analysis = load_json(args.analysis) if args.analysis else {}
    print("Appel au LLM pour générer le JSON du CV corrigé...", file=sys.stderr)
    try:
        res = generate_corrected_cv(
            candidate=candidate,
            analysis=analysis,
            template_path=args.template,
            out_html_path=args.out,
            out_json_path=args.out_json,
            provider=args.provider,
            model=args.model,
        )
    except Exception as e:
        print("Erreur lors de la génération du CV corrigé:", e, file=sys.stderr)
        sys.exit(1)

    template_data = res["template_data"]
    print(f"JSON corrigé sauvegardé: {res['out_json_path']}", file=sys.stderr)
    print(f"  Name: '{template_data.get('Name', '')}'", file=sys.stderr)
    print(f"  Titre: '{template_data.get('Titre', '')}'", file=sys.stderr)
    print(f"CV HTML généré: {res['out_html_path']}", file=sys.stderr)
    print("Terminé.")

if __name__ == "__main__":
    main()