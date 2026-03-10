"""
Agent Portfolio - Génération de contenu de portfolio à partir des réponses du chatbot et du CV
"""

import os
import json
import sys
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import google.generativeai as genai
from minio_storage import get_minio_storage
from A1.ocr import extract_text_from_pdf_bytes
from A1.generate_talent import calculate_years_experience_from_dates
import tempfile
import docx2txt

# Modèle Gemini (configurable via .env, une seule variable pour tout le backend)
GEMINI_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash-lite")

prompt_portfolio = """Tu es un agent IA spécialisé dans la GÉNÉRATION DE CONTENU DE PORTFOLIO PROFESSIONNEL
ORIENTÉ RECRUTEMENT & ENTREPRISE (MODÈLE TAP).

────────────────────────────────
🎯 OBJECTIF
────────────────────────────────
À partir de :
1) un CV du candidat (cv_text ou cv_json)
2) des projets structurés (projects_json)
3) des réponses QA structurées (qa_json)
4) un PDF de référence TAP (reference_portfolio_pdf)

Tu dois générer un CONTENU DE PORTFOLIO ORIGINAL,
lisible en moins de 30 secondes,
permettant à un recruteur de comprendre :
- comment le candidat travaille
- son niveau de maturité professionnelle
- sa fiabilité en environnement entreprise

⚠️ Le PDF TAP définit UNIQUEMENT :
- les TITRES des sections
- l’ORDRE des sections
- le TYPE de contenu attendu

⚠️ Tu ne copies AUCUN texte du PDF
⚠️ Tu ne copies PAS le CV
⚠️ Tout le contenu doit provenir du candidat

────────────────────────────────
📐 STRUCTURE OBLIGATOIRE (STRICTE)
────────────────────────────────

1. HERO / EXECUTIVE PROFILE
- name
- role
- location
- job_title (OBLIGATOIRE, précis, normalisé 3 mots max)
- years_experience (OBLIGATOIRE, calculer depuis les expériences professionnelles)
- executive_summary (5–7 lignes max)
- target_position
- availability
- links (linkedin, github, site)
- key_points_sentences (OBLIGATOIRE) : tableau d'exactement 3 phrases courtes pour la section "Points clés (lecture rapide)". Chaque phrase décrit les compétences et atouts du candidat en général (ex: "Solide maîtrise des fondamentaux professionnels", "Capacité à travailler en autonomie et en équipe", "Approche structurée et orientée entreprise"). Pas de liste de noms de compétences techniques.

2. PROFESSIONAL READINESS SCORE
- global_score (0–100)
- explanation (hard + soft + autonomie + learning)
- display_flag (true/false)

3. SKILLS MAP – HARD SKILLS (EXACTEMENT 6 GROUPES)
À partir des compétences techniques du CV, tu DOIS constituer exactement 6 groupes (catégories). Pas plus, pas moins.
Exemples de catégories : Programmation, Frameworks, Base de données, BI, Outils de dev, etc.
Pour chaque compétence extraite du CV :
- name : nom de l'outil ou de la technologie (ex. React, Java, MySQL, Power BI). Ce nom apparaîtra dans les "Tags" de la carte du groupe.
- category : un des 6 noms de groupe que tu as choisis. C'est ce nom qui sera le TITRE de la carte (ex. "Frameworks", "Programmation"). Répartis toutes les compétences du candidat dans ces 6 catégories.
- level (1–5)
- status : "validated" (utilisé en projet) | "declared" (étudié seulement)
- tags_ia [] : optionnel
Résultat : tu fournis une liste de compétences (autant qu'il y en a dans le CV), chacune avec une category parmi exactement 6 groupes. Le portfolio affichera 6 cartes maximum (une par catégorie), le titre de chaque carte = category, les tags = la liste des "name" de ce groupe (ex. carte "FRAMEWORKS" avec tags "React, Laravel, Django, Flask").

4. SOFT SKILLS MAP (SECTION CENTRALE)
Pour CHAQUE soft skill obligatoire :
- name
- score (1–5)
- proof_type (project | feedback | observation)
- concrete_example (1–2 lignes)
- related_projects []

Soft skills obligatoires :
Communication
Travail en équipe
Autonomie / ownership
Organisation / priorisation
Gestion du stress
Adaptabilité
Esprit critique
Feedback & amélioration
Respect des process
Leadership (optionnel)

5. PROOF OF WORK (PROJETS)
Pour chaque projet :
- title (3 mots max)
- context
- problem
- solution
- stack []
- exact_role
- results
- learnings
- links []
- soft_skills_used []
- autonomy_level (1–5)
- collaboration_quality (1–5)
- images []

⚠️ Tu DOIS associer les images trouvées dans qa_json
(selon proj1_visuals, proj2_visuals, etc.)

6. EXPERIENCE TIMELINE
- date_start
- date_end
- company
- role
- location (ville, pays ou lieu de l'expérience — ex: Paris, Lyon, France)
- impact
- ai_reformulation

7. LEARNING & GROWTH (OBLIGATOIRE pour afficher les formations et certifications)
- etudes [] : parcours scolaire / diplômes (OBLIGATOIRE). Pour chaque entrée : name = diplôme ou formation (ex: Master MIAGE, Licence Info), organization = établissement (ex: Université Paris), year = année d'obtention.
- certifications [] : certifications professionnelles. Pour chaque entrée : name = intitulé, organization = organisme, year = année.
- self_learning []
- skills_in_progress []
- objectives_3_months, objectives_6_months, objectives_12_months
Extrais TOUTES les formations et certifications du CV ; sans etudes et certifications le portfolio affiche des placeholders vides.

8. WORK STYLE & CULTURE FIT
- ideal_company_type
- work_style
- professional_values []
- preferred_conditions

9. RECOMMENDATIONS & BADGES (OPTIONNEL)
- mentors []
- badges []

10. RECRUITER VIEW (VUE CONDENSÉE)
- summary
- readiness_score
- top_hard_skills []
- top_soft_skills []
- key_projects []
- attention_points []
- onboarding_conditions

────────────────────────────────
📤 FORMAT DE SORTIE OBLIGATOIRE (JSON STRICT)
────────────────────────────────

{
  "talent_graph": {
    "hero": {},
    "readiness_score": {},
    "hard_skills": [],
    "soft_skills": [],
    "projects": [],
    "experiences": [],
    "learning_growth": {},
    "work_style": {},
    "recruiter_view": {}

  },
  "exports": {
    "public": true,
    "private": true,
    "recruiter_mode": true
  },
  "warnings": [
    {
      "issue": "",
      "severity": "low | medium | high"
    }
  ]
}

────────────────────────────────
🚫 INTERDICTIONS ABSOLUES
────────────────────────────────
- Pas de storytelling inutile
- Pas de soft skills sans preuve
- Pas de pavés de texte
- Pas de sections hors PDF TAP
- Pas de texte non structuré

────────────────────────────────
✅ AUTO-CHECK FINAL
────────────────────────────────
Avant de répondre, vérifie :
- Lisible en 30 secondes ?
- Exploitable par IA ?
- Chaque soft skill a une preuve ?
- Le recruteur comprend comment le candidat travaille ?
- La recruiter_view suffit à décider d’un entretien ?

Si NON → corrige jusqu’à conformité totale.
"""

# Prompt court pour la version one-page : sortie minimale = génération plus rapide
prompt_portfolio_one_page = """Tu génères un portfolio ONE-PAGE (vue condensée). Réponds UNIQUEMENT en JSON valide.

À partir du CV (cv_text) fourni, extrais et produis un JSON avec cette structure EXACTE. Contenu MINIMAL et CONCIS.

{
  "talent_graph": {
    "hero": {
      "first_name": "",
      "last_name": "",
      "job_title": "3 mots max",
      "executive_summary": "2-4 phrases max",
      "email": "",
      "phone": "",
      "years_experience": 0,
      "links": [{"url": "", "label": "linkedin"}, {"url": "", "label": "github"}],
      "languages": [{"name": "Français", "level": "Courant"}],
      "key_points_sentences": ["phrase 1 sur les compétences en général", "phrase 2", "phrase 3"]
    },
    "readiness_score": {"global_score": 80, "explanation": "", "display_flag": false},
    "hard_skills": [{"name": ""}, {"name": ""}],
    "skill_categories": ["", "", "", "", "", ""],
    "soft_skills": [],
    "projects": [{"title": "", "context": "", "description": ""}],
    "experiences": [{"role": "", "company": "", "date_start": "", "date_end": "", "description": ""}],
    "learning_growth": {
      "etudes": [{"name": "", "organization": "", "year": ""}],
      "certifications": [{"name": "", "organization": "", "year": ""}],
      "self_learning": []
    },
    "languages": [{"name": "", "level": ""}],
    "work_style": {},
    "recruiter_view": {}
  },
  "exports": {"public": true},
  "warnings": []
}

RÈGLES ONE-PAGE :
- LANGUE : Tu as reçu une instruction de langue de sortie (FR ou EN). Si la langue est l'anglais, TOUS les champs texte doivent être en anglais : executive_summary, key_points_sentences, skill_categories, etudes/certifications (name, organization), experiences (role, company, description), projects (title, context, description). Aucun libellé en français ne doit rester lorsque la sortie est en anglais.
- hero : extraire nom, job_title (3 mots max, obligatoire), email, phone, years_experience depuis le CV. executive_summary = 2-4 phrases. key_points_sentences : exactement 3 phrases qui décrivent les compétences et atouts du candidat en général (ex: maîtrise des fondamentaux, travail en équipe, approche structurée), pas une liste de compétences techniques. languages : liste des langues avec level (ex: Courant, B2, Natif).
- hard_skills : Liste des compétences techniques extraites du CV (pour référence interne).
- skill_categories : EXACTEMENT 6 catégories (domaines) de compétences pertinentes par rapport au poste. Chaque catégorie est un nom de domaine général. Tu DOIS retourner exactement 6 catégories, pas plus, pas moins. IMPORTANT : rédige les libellés dans la langue de sortie demandée (en français si langue FR, en anglais si langue EN). Exemples en français : "Analyse de données", "Machine Learning", "Frontend", "Backend", "Base de données", "Cloud". Exemples en anglais : "Data Analysis", "Machine Learning", "Frontend", "Backend", "Databases", "Cloud Computing".
- projects : MAXIMUM 4 projets. title (3 mots max) + context (ou description) en une ligne chacun pour le front.
- experiences : MAXIMUM 3 expériences. Pour chaque expérience : role = titre du POSTE uniquement (ex: Développeur Python, Data Analyst, Consultant), 3 à 5 mots max — PAS le titre du projet ni la mission ; company (entreprise), date_start, date_end ; description = sujet ou mission (maximum 10 mots). Ne jamais mettre dans role une phrase longue type titre de projet.
- learning_growth : OBLIGATOIRE — extraire du CV les ÉTUDES (4 plus récentes) dans "etudes" puis "certifications" : name = diplôme/formation, organization = établissement, year = année. Maximum 4 formations au total (études en premier).
  * Si la sortie est en ANGLAIS : name et organization DOIVENT être rédigés en anglais. Exemples de traduction obligatoire : "Développement Informatique (BAC+2)" → "Computer Development (2-year degree)" ou "IT Development (BAC+2)" ; "Ecole X" / "École X" → "X School" ; "Lycée Y" → "Y High School" ; "Baccalauréat Sciences de la Vie et de la Terre" → "High School Diploma in Life and Earth Sciences" ; "Master en ..." → "Master in ..." ; "Licence ..." → "Bachelor in ..." ; "Université Z" → "Z University". Ne jamais laisser "Développement Informatique", "Baccalauréat", "Ecole", "Lycée", "Université" ou tout autre libellé français dans la version anglaise.
- languages : extraire du CV (hero.languages ou talent_graph.languages). Au moins une langue si présente dans le CV.
- Pas de soft_skills détaillés.
Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""


def extract_text_from_cv_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Extrait le texte du CV (PDF/DOCX) depuis les bytes.
    """
    if not file_bytes:
        return ""

    ext = os.path.splitext(filename or "")[1].lower()

    # PDF
    if ext == ".pdf":
        try:
            extracted_text, warnings = extract_text_from_pdf_bytes(file_bytes)
            if warnings:
                print(f"⚠️  Extraction PDF warnings: {warnings}")
            return (extracted_text or "").strip()
        except Exception as e:
            print(f"⚠️  Extraction texte PDF échouée: {e}")
            return ""

    # DOCX
    if ext == ".docx":
        try:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=True) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                txt = docx2txt.process(tmp.name) or ""
                return str(txt).strip()
        except Exception as e:
            print(f"⚠️  Extraction texte DOCX échouée: {e}")
            return ""

    return ""


def get_cv_from_minio(candidate_id: int, use_original_only: bool = False) -> Tuple[bool, Optional[str], Optional[bytes]]:
    """
    Récupère le CV depuis MinIO.
    Si use_original_only=True (ex: portfolio long), utilise uniquement le CV original (candidates.cv_minio_url).
    Sinon privilégie le CV corrigé (PDF) s'il existe, puis le CV original.
    
    Returns:
        Tuple (success, filename, cv_bytes)
    """
    try:
        from database.connection import DatabaseConnection
        
        DatabaseConnection.initialize()
        minio_storage = get_minio_storage()
        bucket_name = minio_storage.bucket_name
        cv_url = None
        source = None
        
        # 1. Si use_original_only (portfolio long), ne pas utiliser le CV corrigé
        if not use_original_only:
            # Préférer le CV corrigé PDF (dernière version) s'il existe
            with DatabaseConnection.get_connection() as db:
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    """SELECT corrected_pdf_minio_url, corrected_cv_minio_url
                       FROM corrected_cv_versions
                       WHERE candidate_id = %s
                       ORDER BY version_number DESC
                       LIMIT 1""",
                    (candidate_id,)
                )
                row_corrected = cursor.fetchone()
                cursor.close()
            
            if row_corrected and row_corrected.get("corrected_pdf_minio_url"):
                cv_url = row_corrected.get("corrected_pdf_minio_url")
                source = "corrected PDF"
            elif row_corrected and row_corrected.get("corrected_cv_minio_url"):
                cv_url = row_corrected.get("corrected_cv_minio_url")
                source = "corrected DOCX"
        
        # 2. Utiliser le CV original (candidates.cv_minio_url) si pas de corrigé ou use_original_only
        if not cv_url:
            with DatabaseConnection.get_connection() as db:
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    "SELECT cv_minio_url FROM candidates WHERE id = %s",
                    (candidate_id,)
                )
                row = cursor.fetchone()
                cursor.close()
            if row and row.get("cv_minio_url"):
                cv_url = row.get("cv_minio_url")
                source = "original"
        
        if not cv_url:
            print(f"⚠️  Aucun CV trouvé en base pour candidate_id={candidate_id}")
            return False, None, None
        
        # Extraire le nom de l'objet depuis l'URL
        if f"/{bucket_name}/" in cv_url:
            object_name = cv_url.split(f"/{bucket_name}/")[-1]
        else:
            print(f"⚠️  Format URL inattendu pour le CV: {cv_url[:80]}...")
            return False, None, None
        
        # Télécharger depuis MinIO
        success, file_bytes, error = minio_storage.download_file(object_name)
        
        if not success:
            print(f"❌ Erreur téléchargement CV depuis MinIO: {error}")
            return False, None, None
        
        filename = os.path.basename(object_name)
        print(f"✅ CV récupéré depuis MinIO ({source}): {filename}")
        return True, filename, file_bytes
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du CV: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def call_gemini_for_portfolio(prompt: str, model: str | None = None, max_tokens: int = 32000) -> str:
    """
    Appelle Gemini pour générer le contenu du portfolio.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable is not set.")
    
    genai.configure(api_key=api_key)
    model_name = model or GEMINI_MODEL

    generation_config = genai.types.GenerationConfig(
        temperature=0.2,
        max_output_tokens=max_tokens,
        response_mime_type="application/json",
    )
    
    model_instance = genai.GenerativeModel(
        model_name=model_name,
        system_instruction="You are a helpful assistant that outputs strict JSON when asked."
    )
    
    # Système de retry pour gérer les erreurs temporaires de l'API Gemini
    max_retries = 3
    retry_delay = 2  # secondes
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = model_instance.generate_content(prompt, generation_config=generation_config)
            
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
    
    if finish_reason == 1:  # STOP
        try:
            return response.text
        except Exception:
            if getattr(candidate, "content", None) and candidate.content.parts:
                return candidate.content.parts[0].text
            raise RuntimeError("Could not extract text from response.")
    elif finish_reason == 2:  # MAX_TOKENS
        if getattr(candidate, "content", None) and candidate.content.parts:
            partial_text = candidate.content.parts[0].text
            if partial_text:
                print("⚠️  Réponse tronquée (max tokens). Retour partiel.")
                return partial_text
        raise RuntimeError("Response truncated (MAX_TOKENS). Increase max_tokens.")
    elif finish_reason == 3:
        raise RuntimeError("Response blocked by safety filters.")
    else:
        try:
            return response.text
        except Exception:
            if getattr(candidate, "content", None) and candidate.content.parts:
                return candidate.content.parts[0].text
            raise RuntimeError(f"LLM finish_reason={finish_reason}")


def extract_images_from_chat_responses(chat_data: Dict) -> Dict[str, List[str]]:
    """
    Extrait toutes les images des réponses du chatbot et les groupe par projet/expérience.
    
    Args:
        chat_data: Données des réponses du chatbot avec 'answers' et 'questions'
    
    Returns:
        Dictionnaire {project_key: [image_urls]} où project_key peut être 'proj1', 'proj2', 'exp1', etc.
    """
    from B2.chat.save_responses import extract_image_urls
    
    images_by_project = {}
    answers = chat_data.get("answers", {})
    questions = chat_data.get("questions", [])
    
    # Créer un mapping question_id -> projet pour mieux associer les images
    question_to_project = {}
    for question in questions:
        q_id = question.get("id", "")
        q_text = question.get("text", "")
        
        # Identifier le projet/expérience depuis l'ID de la question
        project_key = None
        if q_id.startswith("proj1_"):
            project_key = "proj1"
        elif q_id.startswith("proj2_"):
            project_key = "proj2"
        elif q_id.startswith("proj3_"):
            project_key = "proj3"
        elif q_id.startswith("proj4_"):
            project_key = "proj4"
        elif q_id.startswith("exp1_"):
            project_key = "exp1"
        elif q_id.startswith("exp2_"):
            project_key = "exp2"
        elif q_id.startswith("exp3_"):
            project_key = "exp3"
        
        if project_key:
            question_to_project[q_id] = project_key
    
    # Extraire les images de chaque réponse (TOUTES les réponses, pas seulement celles avec "visuals")
    for question_id, answer in answers.items():
        if not answer or not isinstance(answer, str):
            continue
        
        # Identifier le projet associé
        project_key = question_to_project.get(question_id)
        
        # Si pas de project_key, essayer de le deviner depuis l'ID de la question
        if not project_key:
            for prefix in ["proj1", "proj2", "proj3", "proj4", "exp1", "exp2", "exp3"]:
                if prefix in question_id:
                    project_key = prefix
                    question_to_project[question_id] = project_key
                    break
        
        # Extraire les URLs d'images de cette réponse (TOUJOURS vérifier, car une image peut être dans n'importe quelle réponse)
        image_urls = extract_image_urls(answer)
        
        if image_urls:
            if project_key:
                if project_key not in images_by_project:
                    images_by_project[project_key] = []
                images_by_project[project_key].extend(image_urls)
                print(f"✅ Images extraites pour {project_key} depuis {question_id}: {len(image_urls)} images")
            else:
                # Si pas de préfixe clair, essayer de deviner depuis le contenu ou l'ordre
                # En dernier recours, assigner au premier projet disponible
                if not images_by_project:
                    images_by_project["proj1"] = []
                first_key = list(images_by_project.keys())[0] if images_by_project else "proj1"
                if first_key not in images_by_project:
                    images_by_project[first_key] = []
                images_by_project[first_key].extend(image_urls)
                print(f"⚠️  Images extraites depuis {question_id} sans préfixe clair, assignées à {first_key}: {len(image_urls)} images")
    
    # Dédupliquer les URLs par projet
    for project_key in images_by_project:
        images_by_project[project_key] = list(dict.fromkeys(images_by_project[project_key]))  # Garde l'ordre
    
    print(f"📊 Images extraites par projet/expérience: {[(k, len(v)) for k, v in images_by_project.items()]}")
    return images_by_project


def enrich_portfolio_with_images(portfolio_data: Dict, images_by_project: Dict[str, List[str]], projects_list: List[str]) -> Dict:
    """
    Enrichit le portfolio généré avec les images extraites des réponses du chatbot.
    Associe les images aux projets et expériences en utilisant les noms réels pour un mapping précis.
    
    Args:
        portfolio_data: Données du portfolio générées par l'IA
        images_by_project: Dictionnaire {project_key: [image_urls]} où project_key peut être 'proj1', 'proj2', 'exp1', etc.
        projects_list: Liste des noms de projets dans l'ordre
    
    Returns:
        Portfolio enrichi avec toutes les images
    """
    sections = portfolio_data.get("portfolio_sections", [])
    
    # 1. Enrichir les PROJETS avec leurs images
    projects_section = next((s for s in sections if s.get("section_key") == "projects"), None)
    
    if projects_section:
        projects_content = projects_section.get("content", [])
        if isinstance(projects_content, list):
            # Mapper les images aux projets en utilisant les noms de projets pour un mapping précis
            for idx, project in enumerate(projects_content):
                if not isinstance(project, dict):
                    continue
                
                project_title = project.get("title", "").strip()
                project_key = None
                
                # Essayer d'abord de mapper par nom de projet (plus précis)
                if project_title and projects_list:
                    # Chercher le projet correspondant dans projects_list
                    for i, proj_name in enumerate(projects_list):
                        # Comparaison flexible (insensible à la casse, ignore les espaces)
                        if project_title.lower().strip() == proj_name.lower().strip() or \
                           project_title.lower().strip() in proj_name.lower().strip() or \
                           proj_name.lower().strip() in project_title.lower().strip():
                            # Mapper selon l'index dans projects_list
                            if i == 0:
                                project_key = "proj1"
                            elif i == 1:
                                project_key = "proj2"
                            elif i == 2:
                                project_key = "proj3"
                            elif i == 3:
                                project_key = "proj4"
                            break
                
                # Fallback : mapping par index si le nom ne correspond pas
                if not project_key:
                    if idx == 0:
                        project_key = "proj1"
                    elif idx == 1:
                        project_key = "proj2"
                    elif idx == 2:
                        project_key = "proj3"
                    elif idx == 3:
                        project_key = "proj4"
                
                # Récupérer les images pour ce projet
                project_images = images_by_project.get(project_key, [])
                
                # Enrichir le projet avec les images
                if project_images:
                    existing_images = project.get("images", [])
                    if isinstance(existing_images, list):
                        existing_urls = []
                        for img in existing_images:
                            if isinstance(img, str):
                                existing_urls.append(img)
                            elif isinstance(img, dict):
                                existing_urls.append(img.get("url", ""))
                        all_urls = list(dict.fromkeys(existing_urls + project_images))
                    else:
                        all_urls = project_images
                    
                    project["images"] = [
                        {"url": url} if isinstance(url, str) else url
                        for url in all_urls
                        if url
                    ]
                    
                    print(f"✅ Projet '{project_title or f'Projet {idx+1}'}' ({project_key}) enrichi avec {len(project_images)} nouvelles images (total: {len(all_urls)})")
    
    # 2. Enrichir les EXPÉRIENCES avec leurs images
    experiences_section = next((s for s in sections if s.get("section_key") == "experiences"), None)
    
    if experiences_section:
        experiences_content = experiences_section.get("content", [])
        if isinstance(experiences_content, list):
            for idx, experience in enumerate(experiences_content):
                if not isinstance(experience, dict):
                    continue
                
                # Mapping par index : première expérience = exp1, deuxième = exp2, etc.
                exp_key = None
                if idx == 0:
                    exp_key = "exp1"
                elif idx == 1:
                    exp_key = "exp2"
                elif idx == 2:
                    exp_key = "exp3"
                
                # Récupérer les images pour cette expérience
                exp_images = images_by_project.get(exp_key, [])
                
                # Enrichir l'expérience avec les images
                if exp_images:
                    existing_images = experience.get("images", [])
                    if isinstance(existing_images, list):
                        existing_urls = []
                        for img in existing_images:
                            if isinstance(img, str):
                                existing_urls.append(img)
                            elif isinstance(img, dict):
                                existing_urls.append(img.get("url", ""))
                        all_urls = list(dict.fromkeys(existing_urls + exp_images))
                    else:
                        all_urls = exp_images
                    
                    experience["images"] = [
                        {"url": url} if isinstance(url, str) else url
                        for url in all_urls
                        if url
                    ]
                    
                    role = experience.get("role", "") or experience.get("title", "")
                    company = experience.get("company", "")
                    print(f"✅ Expérience '{role} @ {company}' ({exp_key}) enrichie avec {len(exp_images)} nouvelles images (total: {len(all_urls)})")
    
    return portfolio_data


def extract_json_from_text(text: str) -> str:
    """
    Extrait le JSON du texte de réponse.
    """
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
                json_text = text[start:i+1]
                # Nettoyer les markdown code blocks
                json_text = json_text.replace("```json", "").replace("```", "").strip()
                return json_text
    
    raise ValueError("Incomplete JSON in model output")


def generate_portfolio_content(
    candidate_id: int,
    output_json_path: Optional[str] = None,
    require_chat_responses: bool = True,
    use_original_cv: bool = False,
    lang: str = "fr"
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Fonction principale : génère le contenu du portfolio à partir des réponses du chatbot et du CV.
    
    Args:
        candidate_id: ID du candidat en base de données
        output_json_path: Chemin optionnel pour sauvegarder le JSON généré
        require_chat_responses: Si False (ex: version one-page), continue sans les réponses chatbot (CV seul)
        use_original_cv: Si True (portfolio long), utilise uniquement le CV original (pas le CV corrigé)
        lang: Langue de sortie du contenu ("fr" ou "en")
    
    Returns:
        Tuple (success, portfolio_data, error_message)
    """
    lang = (lang or "fr").lower()
    if lang not in ("fr", "en"):
        lang = "fr"
    lang_instruction_fr = "LANGUE DE SORTIE : Tu dois écrire TOUT le contenu du portfolio (résumé, descriptions, compétences, projets, expériences, etc.) en FRANÇAIS. Tous les champs texte doivent être en français.\n\n"
    lang_instruction_en = "OUTPUT LANGUAGE: You must write ALL portfolio content in ENGLISH: summary, descriptions, skills, projects, experiences, EDUCATION (learning_growth: translate degrees and school names), and LANGUAGES (talent_graph.languages / hero.languages: use English names e.g. 'French', 'English', 'Arabic', and levels e.g. 'Fluent', 'Native', 'Intermediate'). No French text in the English output.\n\n"
    lang_instruction = lang_instruction_en if lang == "en" else lang_instruction_fr
    try:
        # 1 & 2. Récupérer en parallèle les réponses chatbot et le CV (réduit le temps total)
        from B2.chat.save_responses import get_chat_responses_from_minio

        print(f"🔄 Récupération des données (chat + CV) pour candidate_id={candidate_id}")
        chat_data = None
        cv_success, cv_filename, cv_bytes = False, None, None

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_chat = executor.submit(get_chat_responses_from_minio, candidate_id)
            future_cv = executor.submit(get_cv_from_minio, candidate_id, use_original_only=use_original_cv)
            success, chat_data, error = future_chat.result()
            cv_success, cv_filename, cv_bytes = future_cv.result()

        if not success:
            if require_chat_responses:
                return False, None, f"Erreur récupération réponses chatbot: {error}"
            chat_data = {"answers": {}, "questions": [], "projects_list": []}
            print(f"⚠️ Réponses chatbot absentes (one-page) — génération à partir du CV uniquement")
        else:
            print(f"✅ Réponses chatbot récupérées: {len(chat_data.get('answers', {}))} réponses")

        cv_text = ""
        if cv_success and cv_bytes:
            cv_text = extract_text_from_cv_bytes(cv_bytes, cv_filename or "cv.pdf")
            print(f"✅ CV extrait: {len(cv_text)} caractères")
        else:
            print(f"⚠️  CV non disponible, génération sans contexte CV")
        
        # 3. Préparer le prompt pour l'agent IA (one-page = prompt court + moins de tokens = plus rapide)
        # Pour la version long : limiter la taille des entrées pour accélérer (éviter ~2 min)
        MAX_QA_CHARS_LONG = 12000   # Réponses chatbot tronquées pour réduire temps de génération
        MAX_CV_CHARS_LONG = 4000   # CV tronqué
        MAX_OUTPUT_TOKENS_LONG = 20000  # Réduit vs 32k pour accélérer la génération

        if require_chat_responses:
            qa_json_str = json.dumps(chat_data, ensure_ascii=False, indent=2)
            if len(qa_json_str) > MAX_QA_CHARS_LONG:
                qa_json_str = qa_json_str[:MAX_QA_CHARS_LONG] + "\n\n[... réponses tronquées pour longueur ...]"
            cv_snippet = (cv_text[:MAX_CV_CHARS_LONG] if cv_text else "CV non disponible")
            if cv_text and len(cv_text) > MAX_CV_CHARS_LONG:
                cv_snippet += "\n[... CV tronqué ...]"
            full_prompt = f"""{lang_instruction}{prompt_portfolio}

---

## DONNÉES DU CANDIDAT

### Réponses du Chatbot (qa_json):
{qa_json_str}

### Contenu du CV (cv_text) - UNIQUEMENT POUR CONTEXTE:
{cv_snippet}

⚠️ IMPORTANT - EXTRACTION EMAIL ET TÉLÉPHONE :
- Tu DOIS extraire l'email et le téléphone depuis le CV (cv_text) ou les réponses du chatbot (qa_json)
- Ces informations sont OBLIGATOIRES dans la section "contact" du portfolio
- Si tu ne trouves pas ces informations, utilise des valeurs vides mais indique-le dans les warnings

---

Génère maintenant le contenu du portfolio au format JSON strict comme spécifié ci-dessus.
"""
            max_tokens = MAX_OUTPUT_TOKENS_LONG
            model = GEMINI_MODEL
        else:
            full_prompt = f"""{lang_instruction}{prompt_portfolio_one_page}

---

## CV DU CANDIDAT (cv_text)
{cv_text[:4000] if cv_text else "CV non disponible"}

---

Génère le JSON one-page maintenant."""
            max_tokens = 8192
            model = GEMINI_MODEL

        # 4. Appeler l'agent IA
        print("🔄 Appel de l'agent IA pour générer le contenu du portfolio...")
        llm_output = call_gemini_for_portfolio(full_prompt, model=model, max_tokens=max_tokens)
        
        # 5. Extraire et parser le JSON
        json_text = extract_json_from_text(llm_output)
        portfolio_data = json.loads(json_text)
        
        print("✅ Contenu du portfolio généré avec succès")
        
        # 6. Post-traitement : Extraire toutes les images des réponses du chatbot et enrichir le portfolio
        print("🔄 Extraction des images depuis les réponses du chatbot...")
        images_by_project = extract_images_from_chat_responses(chat_data)
        projects_list = chat_data.get("projects_list", [])
        portfolio_data = enrich_portfolio_with_images(portfolio_data, images_by_project, projects_list)
        print("✅ Portfolio enrichi avec toutes les images extraites")
        
        # 7. Sauvegarder le JSON si un chemin est fourni
        if output_json_path:
            os.makedirs(os.path.dirname(output_json_path) or ".", exist_ok=True)
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(portfolio_data, f, ensure_ascii=False, indent=2)
            print(f"✅ JSON sauvegardé: {output_json_path}")
        
        return True, portfolio_data, None
        
    except Exception as e:
        error_msg = f"Erreur lors de la génération du portfolio: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, None, error_msg


def generate_portfolio_content_with_feedback(
    candidate_id: int,
    feedback_modifications: str,
    output_json_path: Optional[str] = None,
    lang: str = "fr"
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Régénère le contenu du portfolio avec des modifications demandées par le candidat.
    
    Args:
        candidate_id: ID du candidat en base de données
        feedback_modifications: Modifications demandées par le candidat
        output_json_path: Chemin optionnel pour sauvegarder le JSON généré
        lang: Langue de sortie du contenu ("fr" ou "en")
    
    Returns:
        Tuple (success, portfolio_data, error_message)
    """
    lang = (lang or "fr").lower()
    if lang not in ("fr", "en"):
        lang = "fr"
    lang_instruction_fr = "LANGUE DE SORTIE : Tu dois écrire TOUT le contenu du portfolio en FRANÇAIS.\n\n"
    lang_instruction_en = "OUTPUT LANGUAGE: You must write ALL portfolio content in ENGLISH.\n\n"
    lang_instruction = lang_instruction_en if lang == "en" else lang_instruction_fr
    try:
        # 1. Récupérer les réponses du chatbot depuis MinIO
        from B2.chat.save_responses import get_chat_responses_from_minio
        
        print(f"🔄 Récupération des réponses du chatbot pour candidate_id={candidate_id}")
        success, chat_data, error = get_chat_responses_from_minio(candidate_id)
        
        if not success:
            return False, None, f"Erreur récupération réponses chatbot: {error}"
        
        print(f"✅ Réponses chatbot récupérées: {len(chat_data.get('answers', {}))} réponses")
        
        # 2. Récupérer le CV depuis MinIO
        print(f"🔄 Récupération du CV pour candidate_id={candidate_id}")
        cv_success, cv_filename, cv_bytes = get_cv_from_minio(candidate_id)
        
        cv_text = ""
        if cv_success and cv_bytes:
            cv_text = extract_text_from_cv_bytes(cv_bytes, cv_filename or "cv.pdf")
            print(f"✅ CV extrait: {len(cv_text)} caractères")
        else:
            print(f"⚠️  CV non disponible, génération sans contexte CV")
        
        # 3. Préparer le prompt avec les modifications demandées
        qa_json_str = json.dumps(chat_data, ensure_ascii=False, indent=2)
        
        full_prompt = f"""{lang_instruction}{prompt_portfolio}

---

## MODIFICATIONS DEMANDÉES PAR LE CANDIDAT

Le candidat a demandé les modifications suivantes pour son portfolio:

```
{feedback_modifications}
```

⚠️ IMPORTANT: Tu dois prendre en compte ces modifications et les intégrer dans le portfolio tout en conservant la structure et le format JSON requis.

---

## DONNÉES DU CANDIDAT

### Réponses du Chatbot (qa_json):
{qa_json_str}

### Contenu du CV (cv_text) - UNIQUEMENT POUR CONTEXTE:
{cv_text[:5000] if cv_text else "CV non disponible"}

⚠️ IMPORTANT - EXTRACTION EMAIL ET TÉLÉPHONE :
- Tu DOIS extraire l'email et le téléphone depuis le CV (cv_text) ou les réponses du chatbot (qa_json)
- Ces informations sont OBLIGATOIRES dans la section "contact" du portfolio
- Si tu ne trouves pas ces informations, utilise des valeurs vides mais indique-le dans les warnings

---

Génère maintenant le contenu du portfolio au format JSON strict comme spécifié ci-dessus, en tenant compte des modifications demandées.
"""
        
        # 4. Appeler l'agent IA
        print("🔄 Appel de l'agent IA pour régénérer le contenu du portfolio avec modifications...")
        llm_output = call_gemini_for_portfolio(full_prompt)
        
        # 5. Extraire et parser le JSON
        json_text = extract_json_from_text(llm_output)
        portfolio_data = json.loads(json_text)
        
        print("✅ Contenu du portfolio régénéré avec succès")
        
        # 6. Post-traitement : Extraire toutes les images des réponses du chatbot et enrichir le portfolio
        print("🔄 Extraction des images depuis les réponses du chatbot...")
        images_by_project = extract_images_from_chat_responses(chat_data)
        projects_list = chat_data.get("projects_list", [])
        portfolio_data = enrich_portfolio_with_images(portfolio_data, images_by_project, projects_list)
        print("✅ Portfolio enrichi avec toutes les images extraites")
        
        # 7. Sauvegarder le JSON si un chemin est fourni
        if output_json_path:
            os.makedirs(os.path.dirname(output_json_path) or ".", exist_ok=True)
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(portfolio_data, f, ensure_ascii=False, indent=2)
            print(f"✅ JSON sauvegardé: {output_json_path}")
        
        return True, portfolio_data, None
        
    except Exception as e:
        error_msg = f"Erreur lors de la régénération du portfolio: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, None, error_msg


def _job_title_max_3_words(s: Optional[str]) -> str:
    """Limite le job_title à 3 mots maximum, sans couper ni laisser un connecteur seul (ex: pas "3D ARTIST &")."""
    if not s or not isinstance(s, str):
        return (s or "").strip() if s is not None else ""
    words = s.strip().split()
    # Connecteurs qu'on ne doit pas garder en dernier (mot manquant après)
    connectors = {"&", "and", "et", "-", "/", "|", "or", "ou", "and/or"}
    # Prendre au plus 3 mots
    taken = words[:3]
    # Retirer le dernier mot tant que c'est un connecteur (éviter "3D ARTIST &")
    while len(taken) > 1 and taken[-1].strip().lower() in connectors:
        taken = taken[:-1]
    return " ".join(taken)


def transform_portfolio_data_for_template(
    portfolio_data: Dict, 
    candidate_image_url: Optional[str] = None,
    candidate_job_title: Optional[str] = None,
    candidate_years_experience: Optional[int] = None,
    candidate_email: Optional[str] = None,
    candidate_phone: Optional[str] = None
) -> Dict:
    """
    Transforme le JSON généré par l'IA (nouveau format TAP) en format attendu par le template Jinja2.
    
    Args:
        portfolio_data: Données du portfolio générées par l'agent IA (format TAP avec talent_graph)
        candidate_image_url: URL de l'image du candidat (optionnel)
    
    Returns:
        Dictionnaire au format attendu par portfolio_template.html
    """
    
    # Nouveau format TAP avec talent_graph
    talent_graph = portfolio_data.get("talent_graph", {})
    
    # ========== GESTION DU NOUVEAU FORMAT TAP ==========
    if talent_graph:
        print("✅ Utilisation du nouveau format TAP (talent_graph)")
        
        # Extraire les données du nouveau format
        hero_tap = talent_graph.get("hero", {})
        readiness = talent_graph.get("readiness_score", {})
        hard_skills_tap = talent_graph.get("hard_skills", [])
        skill_categories_tap = talent_graph.get("skill_categories", [])
        soft_skills_tap = talent_graph.get("soft_skills", [])
        projects_tap = talent_graph.get("projects", [])
        experiences_tap = talent_graph.get("experiences", [])
        learning_tap = talent_graph.get("learning_growth", {})
        work_style_tap = talent_graph.get("work_style", {})
        
        # Extraire nom depuis hero (name ou first_name/last_name pour one-page)
        if hero_tap.get("first_name") or hero_tap.get("last_name"):
            first_name = hero_tap.get("first_name") or "Candidat"
            last_name = hero_tap.get("last_name") or ""
        else:
            name_parts = (hero_tap.get("name") or "").split(" ", 1)
            first_name = name_parts[0] if name_parts else "Candidat"
            last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Transformer les projets TAP
        transformed_projects = []
        for project in projects_tap:
            if not isinstance(project, dict):
                continue
            
            # Extraire les images
            images_raw = project.get("images", [])
            main_image_url = ""
            preview_images = []
            
            if images_raw and isinstance(images_raw, list):
                if len(images_raw) > 0:
                    main_image_url = images_raw[0] if isinstance(images_raw[0], str) else images_raw[0].get("url", "")
                preview_images = [
                    {"url": img if isinstance(img, str) else img.get("url", "")}
                    for img in images_raw[1:5]
                    if (isinstance(img, str) and img) or (isinstance(img, dict) and img.get("url"))
                ]
            
            # Extraire les liens
            links_raw = project.get("links", [])
            links = []
            if links_raw and isinstance(links_raw, list):
                for link in links_raw:
                    if isinstance(link, dict):
                        links.append({
                            "url": link.get("url", ""),
                            "label": link.get("label", "Voir le projet")
                        })
                    elif isinstance(link, str):
                        links.append({"url": link, "label": "Voir le projet"})
            
            transformed_projects.append({
                "title": project.get("title", ""),
                "subtitle": "",
                "context": project.get("context", ""),
                "problem": project.get("problem", ""),
                "solution": project.get("solution", ""),
                "stack": project.get("stack", []),
                "tools": project.get("stack", []),  # Alias pour compatibilité
                "exact_role": project.get("exact_role", ""),
                "results": project.get("results", ""),
                "learnings": project.get("learnings", ""),
                "links": links,
                "soft_skills_used": project.get("soft_skills_used", []),
                "autonomy_level": project.get("autonomy_level", 3),
                "collaboration_quality": project.get("collaboration_quality", 4),
                "main_image_url": main_image_url,
                "preview_images": preview_images,
                "images": images_raw,  # Format original pour compatibilité
                "client_or_context": project.get("context", ""),
                "description": (project.get("description") or project.get("context") or project.get("solution") or "").strip(),
                "responsibilities": [project.get("exact_role", "")]
            })
        
        # Transformer les expériences TAP : titre, entreprise – année début - année fin, sujet/contexte
        # Exclure les formations/études (ne garder que les expériences professionnelles)
        def _is_education_experience(exp):
            if not isinstance(exp, dict):
                return True
            if exp.get("type") == "education" or exp.get("category") == "education":
                return True
            role = (exp.get("role") or exp.get("title") or "").lower()
            company = (exp.get("company") or exp.get("organization") or "").lower()
            education_keywords = ("étudiant", "student", "stagiaire étudiant", "bac+", "licence ", "master ", "diplôme")
            if any(k in role for k in education_keywords):
                return True
            if any(k in company for k in ("école", "school", "université", "university", "campus")) and ("étudiant" in role or "student" in role):
                return True
            return False

        def _education_to_formation(exp):
            """Convertit une entrée expérience de type éducation en item formation (name, organization, year)."""
            date_start = (exp.get("date_start") or "").strip()
            date_end = (exp.get("date_end") or "").strip()
            if date_end.lower() in ("présent", "present", "now", "actuel", ""):
                date_end = "Présent"
            year_str = f"{date_start} - {date_end}" if date_start else (date_end or exp.get("year") or exp.get("period") or exp.get("periode") or "")
            return {
                "name": exp.get("role") or exp.get("title") or "Formation",
                "title": exp.get("role") or exp.get("title") or "Formation",
                "organization": exp.get("company") or exp.get("organization") or exp.get("institution") or "",
                "organism": exp.get("company") or exp.get("organization") or exp.get("institution") or "",
                "year": year_str,
            }

        transformed_experiences = []
        education_from_experiences = []
        for exp in experiences_tap:
            if not isinstance(exp, dict):
                continue
            if _is_education_experience(exp):
                education_from_experiences.append(_education_to_formation(exp))
                continue
            date_start = (exp.get("date_start") or "").strip()
            date_end = (exp.get("date_end") or "").strip()
            if date_end.lower() in ("présent", "present", "now", "actuel", ""):
                date_end = "Présent"
            year_str = f"{date_start} - {date_end}" if date_start else date_end
            if not year_str:
                year_str = (exp.get("year") or exp.get("period") or exp.get("periode") or "").strip()
            desc = (exp.get("description") or exp.get("impact") or "").strip()
            loc = (
                exp.get("location")
                or exp.get("ville")
                or exp.get("city")
                or exp.get("place")
                or exp.get("lieu")
                or ""
            )
            # poste = titre du poste (rôle métier), pas le titre de projet ni le sujet ; title = mission/sujet
            poste = (exp.get("poste") or exp.get("job_title") or exp.get("position") or exp.get("role") or "").strip()
            title_mission = (exp.get("title") or "").strip()
            # Ne jamais utiliser le sujet (title_mission) ou un libellé trop long comme poste (comportement FR = EN)
            def _looks_like_job_title(s):
                if not s or len(s) > 45:
                    return False
                s = s.strip()
                # Rejeter les titres tronqués (ex: "3D Artist &", "Designer -")
                if s.endswith(("&", ",", " -", "-", "/", "\\", "...", "…")):
                    return False
                # Rejeter si trop court (fragment) ou trop de mots (phrase)
                words = s.split()
                if len(words) <= 0 or len(words) > 6:
                    return False
                # Au moins 2 caractères par "mot" en moyenne pour éviter "3D &" etc.
                if len(s) < 6:
                    return False
                return True
            if not _looks_like_job_title(poste) and poste:
                poste = ""  # role/poste contient un sujet long, on ne l'utilise pas
            if not poste and _looks_like_job_title(title_mission):
                poste = title_mission
            elif not poste and _looks_like_job_title(exp.get("role", "")):
                poste = exp.get("role", "").strip()
            transformed_experiences.append({
                "date_start": date_start,
                "date_end": date_end,
                "company": exp.get("company", ""),
                "organization": exp.get("company", ""),
                "location": loc,
                "poste": poste,
                "role": exp.get("role", ""),
                "title": title_mission or exp.get("role", ""),
                "year": year_str,
                "impact": desc,
                "description": desc,
                "value_brought": desc,
                "period": year_str,
                "periode": year_str,
                "tools": [],
                "responsibilities": []
            })
        
        # Extraire les liens de manière sécurisée (peuvent être strings ou dicts)
        links_raw = hero_tap.get("links", [])
        linkedin_url = ""
        github_url = ""
        
        if isinstance(links_raw, list):
            for link in links_raw:
                # Si c'est un dict
                if isinstance(link, dict):
                    url = link.get("url") or ""
                    if isinstance(url, str) and "linkedin" in url.lower() and not linkedin_url:
                        linkedin_url = url
                    elif isinstance(url, str) and "github" in url.lower() and not github_url:
                        github_url = url
                # Si c'est un string
                elif isinstance(link, str):
                    link_str = link.lower()
                    if "linkedin" in link_str and not linkedin_url:
                        linkedin_url = link
                    elif "github" in link_str and not github_url:
                        github_url = link
        
        def _ensure_key_points_sentences(raw):
            """Retourne au plus 3 phrases (strings) pour la section Points clés."""
            if not raw or not isinstance(raw, list):
                return []
            out = []
            for i, x in enumerate(raw):
                if i >= 3:
                    break
                s = (x if isinstance(x, str) else str(x)).strip()
                if s:
                    out.append(s)
            return out
        
        def _normalize_and_sort_hard_skills_for_groups(skills):
            """Assure une catégorie par compétence et trie par catégorie pour le regroupement (Programmation, Base de données, BI, Frameworks, etc.)."""
            if not skills or not isinstance(skills, list):
                return []
            out = []
            for s in skills:
                if not isinstance(s, dict):
                    continue
                rec = dict(s)
                rec.setdefault("category", rec.get("category") or "Compétences")
                rec.setdefault("status", rec.get("status") or "declared")
                rec.setdefault("tags_ia", rec.get("tags_ia") or [])
                out.append(rec)
            return sorted(out, key=lambda x: (x.get("category") or "").lower())

        # Normaliser learning_growth pour le template : ÉTUDES (en premier) + certifications + self_learning
        def _normalize_formation_item(item):
            if isinstance(item, dict):
                org = item.get("organization", item.get("institution", item.get("organism", "")))
                return {
                    "name": item.get("name", item.get("title", "")),
                    "organization": org,
                    "organism": org,
                    "year": item.get("year", item.get("date", "")),
                }
            return {"name": str(item), "organization": "", "organism": "", "year": ""}
        etudes = (
            learning_tap.get("etudes")
            or learning_tap.get("education")
            or learning_tap.get("degrees")
            or learning_tap.get("studies")
            or learning_tap.get("formations")
            or []
        )
        if not isinstance(etudes, list):
            etudes = [etudes] if etudes else []
        # Ajouter les études extraites des expériences (ex. "Étudiant en dev" à École X)
        etudes = etudes + education_from_experiences
        certs = (
            learning_tap.get("certifications")
            or learning_tap.get("formations")
            or learning_tap.get("certifications_pro")
            or []
        )
        self_learn = learning_tap.get("self_learning") or learning_tap.get("courses") or []
        if not isinstance(certs, list):
            certs = [certs] if certs else []
        if not isinstance(self_learn, list):
            self_learn = [self_learn] if self_learn else []
        # Section Formation du template = études d'abord, puis certifications
        formations_merged = [_normalize_formation_item(x) for x in etudes] + [_normalize_formation_item(x) for x in certs]
        learning_growth_normalized = {
            "etudes": [_normalize_formation_item(x) for x in etudes],
            "certifications": formations_merged,
            "self_learning": [_normalize_formation_item(x) for x in self_learn],
        }
        
        # Langues : talent_graph ou hero
        languages_list = talent_graph.get("languages") or hero_tap.get("languages") or []
        if not isinstance(languages_list, list):
            languages_list = [languages_list] if languages_list else []
        languages_list = [
            {"name": x.get("name", x.get("language", str(x))), "level": x.get("level", "")}
            if isinstance(x, dict) else {"name": str(x), "level": ""}
            for x in languages_list
        ]
        
        # Années d'expérience : priorité au calcul depuis les dates (éviter les erreurs de l'agent)
        years_experience_val = None
        if experiences_tap and isinstance(experiences_tap, list):
            exp_for_calc = [
                {
                    "date_start": e.get("date_start", ""),
                    "date_end": e.get("date_end", ""),
                    "periode": (e.get("date_start") or "") + "-" + (e.get("date_end") or ""),
                }
                for e in experiences_tap
                if isinstance(e, dict)
            ]
            computed = calculate_years_experience_from_dates(exp_for_calc)
            if computed > 0:
                years_experience_val = f"{computed}+"
        if not years_experience_val and candidate_years_experience is not None:
            years_experience_val = f"{candidate_years_experience}+"
        if not years_experience_val:
            agent_y = hero_tap.get("years_experience")
            if agent_y is not None and agent_y != "":
                if isinstance(agent_y, int):
                    years_experience_val = f"{max(0, agent_y)}+"
                else:
                    m = re.search(r"\d+", str(agent_y).strip())
                    years_experience_val = f"{int(m.group(0))}+" if m else "5+"
            else:
                years_experience_val = "5+"

        # Retourner les données transformées au format TAP
        return {
            "candidate": {
                "first_name": first_name,
                "last_name": last_name,
                "job_title": _job_title_max_3_words(hero_tap.get("job_title", candidate_job_title or "Professional")),
                "role": hero_tap.get("role", ""),
                "location": hero_tap.get("location", ""),
                "executive_summary": hero_tap.get("executive_summary", ""),
                "target_position": hero_tap.get("target_position", ""),
                "availability": hero_tap.get("availability", ""),
                "disponibilite": hero_tap.get("availability", ""),
                "linkedin_url": linkedin_url,
                "github_url": github_url,
                "years_experience": years_experience_val,
                "email": candidate_email or hero_tap.get("email", ""),
                "phone": candidate_phone or hero_tap.get("phone", ""),
                "profile_image_url": candidate_image_url,
                "about_text": hero_tap.get("executive_summary", ""),
                "specialties": hero_tap.get("specialties", []),
                "key_points_sentences": _ensure_key_points_sentences(hero_tap.get("key_points_sentences")),
                "tagline": "Professional Profile",
                "brand_tagline": "TAP Certified",
                
                # Readiness Score (nouveau)
                "readiness_score": {
                    "global_score": readiness.get("global_score", 85),
                    "explanation": readiness.get("explanation", ""),
                    "hard_skills_score": readiness.get("hard_skills_score", 85),
                    "soft_skills_score": readiness.get("soft_skills_score", 80),
                    "autonomy_score": readiness.get("autonomy_score", 90),
                    "learning_score": readiness.get("learning_score", 88),
                    "display_flag": readiness.get("display_flag", True)
                },
                
                # Hard Skills (nouveau) : normaliser category + tri pour regroupement template (Programmation, Base de données, BI, Frameworks, etc.)
                "hard_skills": _normalize_and_sort_hard_skills_for_groups(hard_skills_tap),
                
                # Skill Categories : exactement 6 catégories pour template one-page
                "skill_categories": skill_categories_tap[:6] if skill_categories_tap else [],
                
                # Soft Skills Map (nouveau - SECTION CENTRALE)
                "soft_skills_map": soft_skills_tap,
                
                # Projets (nouveau format TAP)
                "projects": transformed_projects,
                
                # Expériences (nouveau format TAP)
                "experiences": transformed_experiences,
                
                # Learning & Growth (normalisé pour template : certifications + self_learning)
                "learning_growth": learning_growth_normalized,
                # Pour portfolio_long_template.html (page 8) : formations = études, certifications = certifications seules
                "formations": learning_growth_normalized.get("etudes", []),
                "certifications": [_normalize_formation_item(x) for x in certs],
                "trainings": learning_growth_normalized.get("etudes", []),

                # Pour portfolio_long_template.html (page 9) : score global et détails par dimension
                "global_score": readiness.get("global_score"),
                "score_global": readiness.get("global_score"),
                "score_details": {
                    "hard_skills": readiness.get("hard_skills_score"),
                    "soft_skills": readiness.get("soft_skills_score"),
                    "autonomy": readiness.get("autonomy_score"),
                    "autonomie": readiness.get("autonomy_score"),
                    "learning_ability": readiness.get("learning_score"),
                    "professional_behavior": readiness.get("professional_behavior_score"),
                },

                # Work Style (nouveau)
                "work_style": work_style_tap,
                
                # Anciennes données pour compatibilité
                "technical_skills": [skill.get("name") for skill in hard_skills_tap if isinstance(skill, dict)] if hard_skills_tap else [],
                "soft_skills": [skill.get("name") for skill in soft_skills_tap if isinstance(skill, dict)] if soft_skills_tap else [],
                "services": [],  # Obsolète dans le nouveau format
                "skill_levels": [],  # Obsolète dans le nouveau format
                "languages": languages_list,
                "career_summary": "",  # À extraire depuis experiences
            },
            "portfolio": {
                "year": datetime.now().year,
                "show_social_gallery": False
            }
        }
    
    # ========== FALLBACK: ANCIEN FORMAT (portfolio_sections) ==========
    print("⚠️  Utilisation de l'ancien format (portfolio_sections)")
    sections = portfolio_data.get("portfolio_sections", [])
    
    # Extraire les sections
    hero = next((s for s in sections if s.get("section_key") == "hero"), {})
    about = next((s for s in sections if s.get("section_key") == "about"), {})
    services_skills = next((s for s in sections if s.get("section_key") == "services_skills"), {})
    skills_section = next((s for s in sections if s.get("section_key") == "skills"), {})
    experiences_section = next((s for s in sections if s.get("section_key") == "experiences"), {})
    projects = next((s for s in sections if s.get("section_key") == "projects"), {})
    contact = next((s for s in sections if s.get("section_key") == "contact"), {})
    languages_section = next((s for s in sections if s.get("section_key") == "languages"), {})
    
    hero_content = hero.get("content", {})
    about_content = about.get("content", {})
    services_content = services_skills.get("content", {})
    skills_content = skills_section.get("content", {})
    experiences_content = experiences_section.get("content", [])
    projects_content = projects.get("content", [])
    contact_content = contact.get("content", {})
    languages_content = languages_section.get("content", [])
    
    # Extraire le nom (peut être dans hero ou dans le nom de la section)
    name_parts = (hero_content.get("name") or hero_content.get("nom") or "").split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    # Si pas de nom dans hero, essayer de l'extraire d'ailleurs ou utiliser des valeurs par défaut
    if not first_name and not last_name:
        print(f"⚠️  Nom non trouvé dans hero_content: {hero_content}")
        # Essayer depuis contact ou autres sections
        if contact_content.get("name"):
            name_parts = contact_content.get("name", "").split(" ", 1)
            first_name = name_parts[0] if name_parts else "Candidat"
            last_name = name_parts[1] if len(name_parts) > 1 else ""
        else:
            first_name = "Candidat"
            last_name = ""
    
    # Transformer les expériences depuis la section dédiée "experiences"
    experiences = []
    if experiences_content and isinstance(experiences_content, list):
        for exp in experiences_content:
            if isinstance(exp, dict):
                # Extraire les images de l'expérience si présentes
                exp_images = []
                if exp.get("images"):
                    exp_images_raw = exp.get("images", [])
                    if isinstance(exp_images_raw, list):
                        for img in exp_images_raw:
                            if isinstance(img, str):
                                exp_images.append(img)
                            elif isinstance(img, dict):
                                exp_images.append(img.get("url", ""))
                
                date_start = (exp.get("date_start") or exp.get("start_date") or "").strip()
                date_end = (exp.get("date_end") or exp.get("end_date") or "").strip()
                if date_end.lower() in ("présent", "present", "now", "actuel", ""):
                    date_end = "Présent"
                year_str = f"{date_start} - {date_end}" if date_start else date_end
                if not year_str:
                    year_str = (exp.get("year") or exp.get("period") or exp.get("periode") or "").strip()
                desc = (exp.get("description") or exp.get("impact") or exp.get("value_brought") or "").strip()
                loc = exp.get("location") or exp.get("ville") or exp.get("city") or exp.get("place") or exp.get("lieu") or ""
                experiences.append({
                    "company": exp.get("company", ""),
                    "organization": exp.get("company", ""),
                    "role": exp.get("role", ""),
                    "title": exp.get("role", exp.get("title", "")),
                    "year": year_str,
                    "description": desc,
                    "value_brought": desc,
                    "location": loc,
                    "responsibilities": exp.get("responsibilities", []) if isinstance(exp.get("responsibilities"), list) else [],
                    "tools": exp.get("tools", []) if isinstance(exp.get("tools"), list) else [],
                    "images": exp_images if exp_images else []
                })
    # Fallback : chercher dans services_content si la section experiences n'existe pas
    elif services_content.get("experiences"):
        for exp in services_content.get("experiences", []):
            if isinstance(exp, dict):
                date_start = (exp.get("date_start") or exp.get("start_date") or "").strip()
                date_end = (exp.get("date_end") or exp.get("end_date") or "").strip()
                if date_end.lower() in ("présent", "present", "now", "actuel", ""):
                    date_end = "Présent"
                year_str = f"{date_start} - {date_end}" if date_start else date_end
                if not year_str:
                    year_str = (exp.get("year") or exp.get("period") or exp.get("periode") or "").strip()
                desc = (exp.get("description") or exp.get("impact") or exp.get("value_brought") or "").strip()
                loc = exp.get("location") or exp.get("ville") or exp.get("city") or exp.get("place") or exp.get("lieu") or ""
                experiences.append({
                    "company": exp.get("company", ""),
                    "organization": exp.get("company", ""),
                    "role": exp.get("role", ""),
                    "title": exp.get("role", exp.get("title", "")),
                    "year": year_str,
                    "description": desc,
                    "value_brought": desc,
                    "location": loc,
                    "responsibilities": exp.get("responsibilities", []) if isinstance(exp.get("responsibilities"), list) else [],
                    "tools": exp.get("tools", []) if isinstance(exp.get("tools"), list) else []
                })
    
    # Transformer les projets
    transformed_projects = []
    print(f"🔍 [Transform Portfolio] Nombre de projets dans projects_content: {len(projects_content) if isinstance(projects_content, list) else 'N/A (pas une liste)'}")
    print(f"🔍 [Transform Portfolio] Type de projects_content: {type(projects_content)}")
    if isinstance(projects_content, list) and len(projects_content) > 0:
        print(f"🔍 [Transform Portfolio] Premier projet (aperçu): {projects_content[0] if isinstance(projects_content[0], dict) else 'N/A'}")
    
    for project in projects_content:
        # S'assurer que project est un dictionnaire
        if not isinstance(project, dict):
            print(f"⚠️  Project n'est pas un dict: {type(project)}, valeur: {project}")
            continue
        
        # Extraire les liens de manière sécurisée
        links = project.get("links", [])
        link_url = ""
        link_text = "Voir le projet"
        
        if links and isinstance(links, list) and len(links) > 0:
            first_link = links[0]
            if isinstance(first_link, dict):
                link_url = first_link.get("url", "")
                # Support à la fois "text" et "name" pour le texte du lien
                link_text = first_link.get("text") or first_link.get("name") or "Voir le projet"
            elif isinstance(first_link, str):
                # Si c'est une chaîne, utiliser directement comme URL
                link_url = first_link
                link_text = "Voir le projet"
        
        # Extraire les images de manière sécurisée
        images = project.get("images", [])
        main_image_url = ""
        preview_images = []
        
        if images and isinstance(images, list):
            # Fonction helper pour extraire l'URL d'une image
            def extract_image_url(img):
                """Extrait l'URL d'une image, qu'elle soit une chaîne ou un dictionnaire"""
                if isinstance(img, str):
                    return img
                elif isinstance(img, dict):
                    # Si c'est un dictionnaire, chercher la clé 'url'
                    url = img.get("url", "")
                    # Si url est encore un dictionnaire (erreur de sérialisation), extraire à nouveau
                    if isinstance(url, dict):
                        url = url.get("url", "")
                    # Si url est une chaîne qui ressemble à un dict Python (problème de sérialisation)
                    if isinstance(url, str) and url.startswith("{") and "'url'" in url:
                        # Essayer d'extraire l'URL depuis la chaîne
                        import re
                        match = re.search(r"'url':\s*'([^']+)'", url)
                        if match:
                            url = match.group(1)
                    return url if url else ""
                else:
                    # Si c'est autre chose, essayer de convertir en chaîne proprement
                    return str(img) if img else ""
            
            # Image principale
            if len(images) > 0:
                main_image_url = extract_image_url(images[0])
            
            # Images de prévisualisation
            preview_images = [
                {"url": extract_image_url(img)}
                for img in images[1:5]
                if extract_image_url(img)  # Ne garder que les images avec une URL valide
            ]
        
        transformed_projects.append({
            "title": project.get("title", ""),
            "subtitle": project.get("category", ""),
            "client": project.get("client_or_context", ""),
            "description": (project.get("description") or project.get("context") or project.get("solution") or "").strip(),
            "responsibilities": project.get("responsibilities", []) if isinstance(project.get("responsibilities"), list) else [],
            "skills": project.get("tools", []) if isinstance(project.get("tools"), list) else [],
            "link_url": link_url,
            "link_text": link_text,
            "main_image_url": main_image_url,
            "main_image_overlay": project.get("title", ""),
            "preview_images": preview_images
        })
    
    # Transformer les services
    services = []
    services_raw = services_content.get("services")
    print(f"🔍 Debug services: type={type(services_raw)}, valeur={services_raw}")
    
    if services_raw:
        # Si services_raw est un dict, essayer d'extraire les services
        if isinstance(services_raw, dict):
            # Peut-être que les services sont dans une clé spécifique
            services_raw = services_raw.get("list", []) or list(services_raw.values()) if services_raw else []
        
        for idx, service in enumerate(services_raw if isinstance(services_raw, list) else []):
            print(f"🔍 Debug service[{idx}]: type={type(service)}, valeur={service}")
            
            # S'assurer que service est un dictionnaire
            if not isinstance(service, dict):
                print(f"⚠️  Service[{idx}] n'est pas un dict: {type(service)}, valeur: {service}")
                continue
            
            # Extraire les items - utiliser une clé différente si "items" n'existe pas
            service_items = service.get("items") or service.get("list") or service.get("services") or []
            
            # Si pas d'items mais une description, créer des items depuis la description
            if not service_items and service.get("description"):
                # Diviser la description par des points ou des virgules pour créer des items
                description = service.get("description", "")
                # Essayer de diviser par des points-virgules, puis par des points
                if ";" in description:
                    service_items = [item.strip() for item in description.split(";") if item.strip()]
                elif "." in description:
                    # Diviser par points mais garder les phrases complètes
                    sentences = [s.strip() + "." for s in description.split(".") if s.strip()]
                    service_items = sentences[:5]  # Limiter à 5 items
                else:
                    # Si pas de séparateur, utiliser la description complète
                    service_items = [description]
            
            # Vérifier que items n'est pas une méthode
            if callable(service_items):
                print(f"⚠️  service.items est une méthode (callable), utilisation d'une liste vide")
                service_items = []
            elif not isinstance(service_items, list):
                # Si ce n'est ni une liste ni une méthode, essayer de convertir
                if service_items:
                    service_items = [service_items] if not isinstance(service_items, (str, int, float)) else [str(service_items)]
                else:
                    service_items = []
            
            print(f"🔍 Debug service[{idx}].items_list: type={type(service_items)}, valeur={service_items}")
            
            services.append({
                "title": service.get("title", service.get("name", service.get("service_name", ""))),
                "style": service.get("style", service.get("color", "light")),
                "items_list": service_items  # Renommé pour éviter le conflit avec .items() du dict
            })
    
    # Fallback intelligent et flexible : générer des services à partir des données disponibles
    if not services:
        print("⚠️  Aucun service fourni par l'IA, génération automatique de services à partir des données disponibles...")
        
        # Collecter toutes les sources possibles pour générer des services
        service_sources = []
        
        # 1. Source: Spécialités (hero_content)
        specialties = hero_content.get("specialties", [])
        if specialties and isinstance(specialties, list):
            for specialty in specialties:
                if specialty and str(specialty).strip():
                    service_sources.append({
                        "type": "specialty",
                        "title": str(specialty).strip(),
                        "source": specialty
                    })
        
        # 2. Source: Rôles dans les expériences (identifier des domaines d'expertise)
        seen_roles = set()
        if experiences:
            for exp in experiences:
                role = exp.get("role", "").strip()
                if role and role.lower() not in seen_roles:
                    seen_roles.add(role.lower())
                    # Extraire le domaine principal du rôle (ex: "Data Analyst" -> "Data Analysis")
                    # Simplification : utiliser le rôle comme titre ou extraire les mots-clés principaux
                    role_words = [w.capitalize() for w in role.split() if len(w) > 2 and w.lower() not in ["de", "du", "et", "en", "le", "la", "les"]]
                    if role_words:
                        service_title = " ".join(role_words[:3])  # Prendre les 3 premiers mots significatifs
                        service_sources.append({
                            "type": "experience_role",
                            "title": service_title,
                            "source": exp
                        })
        
        # 3. Source: Catégories/domaines des projets
        seen_project_categories = set()
        if projects_content:
            for project in projects_content:
                if isinstance(project, dict):
                    category = project.get("category", "").strip() or project.get("subtitle", "").strip()
                    if category and category.lower() not in seen_project_categories:
                        seen_project_categories.add(category.lower())
                        service_sources.append({
                            "type": "project_category",
                            "title": category,
                            "source": project
                        })
        
        # 4. Source: Compétences techniques principales (si disponibles)
        if technical_skills and len(technical_skills) > 0:
            # Regrouper les compétences techniques par domaine
            tech_keywords = {
                "web": ["react", "angular", "vue", "javascript", "typescript", "html", "css", "frontend", "backend"],
                "data": ["python", "sql", "tableau", "power bi", "analytics", "etl", "data science"],
                "ai": ["machine learning", "deep learning", "llm", "ai", "tensorflow", "pytorch", "bert"],
                "cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "cloud"],
                "mobile": ["android", "ios", "react native", "flutter", "mobile"]
            }
            
            tech_domains = set()
            for skill in technical_skills[:10]:  # Limiter à 10 compétences
                skill_lower = str(skill).lower()
                for domain, keywords in tech_keywords.items():
                    if any(kw in skill_lower for kw in keywords):
                        tech_domains.add(domain.capitalize())
                        break
            
            for domain in tech_domains:
                if domain not in [s["title"].lower() for s in service_sources]:
                    service_sources.append({
                        "type": "tech_domain",
                        "title": domain,
                        "source": None
                    })
        
        # Générer les services à partir des sources collectées
        styles = ["light", "dark", "accent"]
        max_services = 6
        
        for idx, source in enumerate(service_sources[:max_services]):
            service_title = source["title"]
            items = []
            
            # Extraire les items selon le type de source
            if source["type"] == "experience_role":
                exp = source["source"]
                if exp.get("responsibilities"):
                    items.extend([r for r in exp.get("responsibilities", []) if r][:3])
                if exp.get("tools"):
                    tools = exp.get("tools", [])
                    if isinstance(tools, list):
                        items.extend([f"Maîtrise de {tool}" for tool in tools[:2]])
            
            elif source["type"] == "project_category":
                project = source["source"]
                if project.get("responsibilities"):
                    items.extend([r for r in project.get("responsibilities", []) if r][:2])
                if project.get("description"):
                    desc = project.get("description", "")
                    # Extraire les premières phrases significatives
                    sentences = [s.strip() + "." for s in desc.split(".") if len(s.strip()) > 20][:2]
                    items.extend(sentences)
            
            elif source["type"] == "specialty" or source["type"] == "tech_domain":
                # Chercher des items dans les expériences correspondantes
                specialty_lower = service_title.lower()
                for exp in experiences[:3]:
                    role = str(exp.get("role", "")).lower()
                    description = str(exp.get("description", "")).lower()
                    
                    if specialty_lower in role or specialty_lower in description:
                        if exp.get("responsibilities"):
                            items.extend([r for r in exp.get("responsibilities", []) if r][:2])
                        break
                
                # Chercher aussi dans les projets
                if len(items) < 3:
                    for project in projects_content[:2]:
                        if isinstance(project, dict):
                            category = str(project.get("category", "")).lower()
                            subtitle = str(project.get("subtitle", "")).lower()
                            
                            if specialty_lower in category or specialty_lower in subtitle:
                                if project.get("responsibilities"):
                                    items.extend([r for r in project.get("responsibilities", []) if r][:2])
                                break
            
            # Si pas assez d'items, ajouter des items génériques mais pertinents
            if len(items) < 3:
                # Générer des items génériques basés sur le titre du service
                generic_items = [
                    f"Expertise approfondie en {service_title}",
                    "Solutions personnalisées et adaptées",
                    "Livraison de qualité professionnelle"
                ]
                items.extend(generic_items[:3 - len(items)])
            
            # Ajouter le service
            services.append({
                "title": service_title,
                "style": styles[idx % len(styles)],
                "items_list": items[:5]  # Maximum 5 items par service
            })
        
        # Si toujours aucun service, créer au moins un service générique basé sur le job_title
        if not services:
            print("⚠️  Aucune source trouvée, création d'un service générique...")
            job_title = hero_content.get("job_title") or hero_content.get("title") or ""
            service_title = job_title if job_title else "Expertise Professionnelle"
            
            items = []
            # Essayer d'extraire des items depuis l'about_text ou les expériences
            about_text = about_content.get("text", "") or about_content.get("description", "")
            if about_text:
                sentences = [s.strip() + "." for s in about_text.split(".") if len(s.strip()) > 30][:3]
                items.extend(sentences)
            
            if not items and experiences:
                for exp in experiences[:2]:
                    if exp.get("description"):
                        desc = exp.get("description", "")
                        sentences = [s.strip() + "." for s in desc.split(".") if len(s.strip()) > 30][:1]
                        items.extend(sentences)
            
            if not items:
                items = [
                    "Expertise professionnelle éprouvée",
                    "Solutions adaptées aux besoins clients",
                    "Approche méthodique et rigoureuse",
                    "Livraison dans les délais"
                ]
            
            services.append({
                "title": service_title,
                "style": "light",
                "items_list": items[:4]
            })
        
        print(f"✅ Services générés automatiquement: {len(services)} services créés à partir de {len(service_sources)} sources")
    
    # Transformer les compétences - séparer technical_skills et soft_skills
    technical_skills = []
    soft_skills = []
    
    # Priorité à la section "skills" si elle existe
    if skills_content:
        if isinstance(skills_content, dict):
            # Extraire technical_skills
            tech_skills_raw = skills_content.get("technical_skills", [])
            if isinstance(tech_skills_raw, list):
                technical_skills = [str(skill) for skill in tech_skills_raw if skill]
            elif isinstance(tech_skills_raw, dict):
                # Si c'est un dict, essayer d'extraire une liste
                technical_skills = [str(v) for v in tech_skills_raw.values() if v] if tech_skills_raw else []
            
            # Extraire soft_skills
            soft_skills_raw = skills_content.get("soft_skills", [])
            if isinstance(soft_skills_raw, list):
                soft_skills = [str(skill) for skill in soft_skills_raw if skill]
            elif isinstance(soft_skills_raw, dict):
                # Si c'est un dict, essayer d'extraire une liste
                soft_skills = [str(v) for v in soft_skills_raw.values() if v] if soft_skills_raw else []
    
    # Fallback : utiliser services_content si la section skills n'existe pas
    if not technical_skills and not soft_skills:
        if services_content.get("skills"):
            # Si on a une liste simple, la traiter comme technical_skills
            skills_list = services_content.get("skills", [])
            if isinstance(skills_list, list):
                technical_skills = [str(skill) for skill in skills_list if skill]
    
    # Récupérer job_title : priorité à l'agent, sinon depuis la base de données (max 3 mots)
    job_title = hero_content.get("title") or hero_content.get("job_title") or ""
    if not job_title and candidate_job_title:
        job_title = candidate_job_title
        print(f"ℹ️  Job title récupéré depuis la base de données: {job_title}")
    job_title = _job_title_max_3_words(job_title)
    
    # Récupérer years_experience : priorité au calcul depuis les dates des expériences (éviter les erreurs de l'agent)
    def _normalize_years(val):
        """Extrait un entier depuis la valeur agent (ex: '5', '5+', '3 ans') pour affichage cohérent."""
        if val is None or val == "":
            return None
        if isinstance(val, int):
            return f"{max(0, val)}+" if val > 0 else "0"
        m = re.search(r"\d+", str(val).strip())
        return f"{int(m.group(0))}+" if m else None

    years_experience = None
    # 1) Calculer depuis les dates des expériences (source fiable)
    if experiences_content and isinstance(experiences_content, list):
        exp_for_calc = []
        for e in experiences_content:
            if isinstance(e, dict):
                exp_for_calc.append({
                    **e,
                    "periode": e.get("periode") or e.get("period") or e.get("year") or "",
                    "date_start": e.get("date_start") or e.get("start_date", ""),
                    "date_end": e.get("date_end") or e.get("end_date", ""),
                })
        computed_years = calculate_years_experience_from_dates(exp_for_calc)
        if computed_years > 0:
            years_experience = f"{computed_years}+"
            print(f"ℹ️  Années d'expérience calculées depuis les dates des expériences: {years_experience}")
    # 2) Sinon base de données
    if not years_experience and candidate_years_experience is not None:
        years_experience = f"{candidate_years_experience}+"
        print(f"ℹ️  Années d'expérience récupérées depuis la base de données: {years_experience}")
    # 3) Sinon valeur agent (normalisée)
    if not years_experience:
        agent_val = services_content.get("years_experience") or hero_content.get("years_experience")
        years_experience = _normalize_years(agent_val) if agent_val else None
    if not years_experience:
        years_experience = "5+"

    # Transformer les langues
    languages = []
    if languages_content and isinstance(languages_content, list):
        for lang in languages_content:
            if isinstance(lang, dict):
                level = lang.get("level", "")
                # Si le niveau est une chaîne (ex: "A1", "B2", "Native", "Avancé"), convertir en pourcentage
                # Sinon, si c'est déjà un nombre, l'utiliser directement
                if isinstance(level, str):
                    level_str = level.strip().lower()
                    # Mapping des niveaux de langue courants vers des pourcentages
                    level_mapping = {
                        "a1": 20, "débutant": 20, "beginner": 20,
                        "a2": 40, "élémentaire": 40, "elementary": 40,
                        "b1": 60, "intermédiaire": 60, "intermediate": 60,
                        "b2": 75, "intermédiaire supérieur": 75, "upper intermediate": 75,
                        "c1": 90, "avancé": 90, "advanced": 90,
                        "c2": 95, "maîtrise": 95, "proficiency": 95,
                        "native": 100, "natif": 100, "courant": 100, "fluent": 100
                    }
                    # Chercher une correspondance dans le mapping
                    level_percentage = None
                    for key, value in level_mapping.items():
                        if key in level_str:
                            level_percentage = value
                            break
                    
                    # Si pas de correspondance et que c'est un nombre dans la chaîne, l'extraire
                    if level_percentage is None:
                        try:
                            # Essayer d'extraire un nombre de la chaîne
                            numbers = re.findall(r'\d+', level_str)
                            if numbers:
                                level_percentage = int(numbers[0])
                                if level_percentage > 100:
                                    level_percentage = 100
                            else:
                                level_percentage = 80  # Valeur par défaut
                        except:
                            level_percentage = 80
                    
                    level = level_percentage
                elif isinstance(level, (int, float)):
                    # S'assurer que le niveau est entre 0 et 100
                    level = max(0, min(100, int(level)))
                else:
                    level = 80  # Valeur par défaut
                
                languages.append({
                    "name": lang.get("name", ""),
                    "level": level
                })
    
    # Utiliser l'email et le téléphone depuis la base de données comme fallback si non présents dans contact_content
    email = contact_content.get("email", "") or candidate_email or ""
    phone = contact_content.get("phone", "") or candidate_phone or ""
    
    result = {
        "candidate": {
            "first_name": first_name,
            "last_name": last_name,
            "tagline": hero_content.get("tagline", "Be in"),
            "job_title": job_title,
            "email": email,
            "phone": phone,
            "linkedin_url": contact_content.get("linkedin", ""),
            "profile_image_url": candidate_image_url or "",
            "years_experience": years_experience,
            "specialties": hero_content.get("specialties", [])[:3],
            "technical_skills": technical_skills,
            "soft_skills": soft_skills,
            "about_text": about_content.get("text", about_content.get("description", "")),
            "experiences": experiences,
            "services": services,
            "projects": transformed_projects,
            "languages": languages,
            "brand_name": f"{first_name} {last_name}",
            "brand_tagline": hero_content.get("tagline", "")
        },
        "portfolio": {
            "year": "2025",
            "show_social_gallery": False
        }
    }
    
    # Log final pour vérifier que les projets sont bien présents
    print(f"✅ [Transform Portfolio] Résultat final:")
    print(f"   - Nombre de projets: {len(transformed_projects)}")
    print(f"   - Projets dans candidate.projects: {len(result['candidate']['projects'])}")
    if len(transformed_projects) > 0:
        print(f"   - Premier projet: {transformed_projects[0].get('title', 'N/A')}")
    
    return result


def convert_html_to_pdf(
    html_content: str,
    candidate_id: int,
    candidate_uuid: str,
    base_url: Optional[str] = None,
    pdf_page_format: Optional[str] = None,
    lang: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Convertit le HTML du portfolio en PDF en utilisant Playwright.
    
    Args:
        html_content: Contenu HTML complet avec données injectées
        candidate_id: ID du candidat en base de données
        candidate_uuid: UUID du candidat
        base_url: URL de base pour résoudre les ressources (images, CSS, etc.)
        pdf_page_format: "one-page" = une seule page 1920x1080 (contenu complet), sinon format long
        lang: "fr" ou "en" pour suffixer le nom du fichier (ex: portfolio_uuid_one-page_fr.pdf)
    
    Returns:
        Tuple (success, pdf_url, error_message)
    """
    try:
        from playwright.sync_api import sync_playwright
        import tempfile
        import os
        import http.server
        import socketserver
        import threading
        import time
        import base64
        import re
        
        print(f"🔄 Conversion HTML en PDF pour candidate_id={candidate_id}")
        
        # PDF one-page : injection des images de fond en base64 + règles d'impression (mise en page, couleurs, contact) depuis le backend.
        if pdf_page_format == "one-page":
            _exact = "-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important;"
            _print_rules_after_star_en = (
                " .page { padding: 240px 170px 240px !important; max-width: none !important; max-height: none !important; width: 67.733cm !important; height: 38.1cm !important; }"
                " .section-header { background: #C1121F !important; color: #fff !important; " + _exact + " }"
                " .content-box, .content-box.name-box { background: #fff !important; " + _exact + " }"
                " .block-profile-content { background: #fff !important; " + _exact + " }"
                " .profile-card-corner-long, .profile-card-corner-medium, .profile-card-corner-short { background: #C1121F !important; " + _exact + " }"
                " .profile-image-wrap { background: #C1121F !important; " + _exact + " }"
                " .block-profile-content-text { background: #C1121F !important; color: #fff !important; " + _exact + " }"
                " .content-box-footer, .footer-block .content-box { background: #fff !important; align-items: center !important; " + _exact + " }"
                " .footer-block.contact-box .content-box-footer.contact-box { flex: 1 !important; }"
                " .contact-box { width: 635px !important; max-width: 635px !important; }"
                " .col-section .content-box { border-left: 6px solid #C1121F !important; " + _exact + " }"
                " .content-box-about { color: #fff !important; }"
                " .btn-download { color: #C1121F !important; " + _exact + " }"
                " .portfolio-viewport .block-profile-content { gap: 10px !important; background: none !important; height: 345px !important; width: 290px !important; }"
                " .contact-icons { margin-top: -5px !important; display: flex !important; align-items: center !important; position: fixed !important; right: 57.8rem !important; }"
                " .contact-icons a { background: #C1121F !important; color: #fff !important; width: 70px !important; height: 70px !important; " + _exact + " }"
                " .contact-icons { height: 20px !important; }"
                " .portfolio-viewport .block-name-skills { margin-left: 30px !important; }"
                " .portfolio-viewport .section-header {font-size: 38px !important; padding: 11px 20px !important;}"
            )

            _print_rules_after_star_fr = (
                " .page { padding: 240px 170px 240px !important; max-width: none !important; max-height: none !important; width: 67.733cm !important; height: 38.1cm !important; }"
                " .section-header { background: #C1121F !important; color: #fff !important; " + _exact + " }"
                " .content-box, .content-box.name-box { background: #fff !important; " + _exact + " }"
                " .block-profile-content { background: #fff !important; " + _exact + " }"
                " .profile-card-corner-long, .profile-card-corner-medium, .profile-card-corner-short { background: #C1121F !important; " + _exact + " }"
                " .profile-image-wrap { background: #C1121F !important; " + _exact + " }"
                " .block-profile-content-text { background: #C1121F !important; color: #fff !important; " + _exact + " }"
                " .content-box-footer, .footer-block .content-box { background: #fff !important; align-items: center !important; " + _exact + " }"
                " .footer-block.contact-box .content-box-footer.contact-box { flex: 1 !important; }"
                " .contact-box { width: 635px !important; max-width: 635px !important; }"
                " .col-section .content-box { border-left: 6px solid #C1121F !important; " + _exact + " }"
                " .content-box-about { color: #fff !important; }"
                " .btn-download { color: #C1121F !important; " + _exact + " }"
                " .portfolio-viewport .block-profile-content { gap: 10px !important; background: none !important; height: 345px !important; width: 290px !important; }"
                " .contact-icons { margin-top: -5px !important; display: flex !important; align-items: center !important; position: fixed !important; right: 57.8rem !important; }"
                " .contact-icons a { background: #C1121F !important; color: #fff !important; width: 70px !important; height: 70px !important; " + _exact + " }"
                " .contact-icons { height: 20px !important; }"
                " .portfolio-viewport .block-name-skills { margin-left: 30px !important; }"
                " .portfolio-viewport .section-header {font-size: 38px !important; padding: 11px 20px !important; }"
            )

            print_rules = _print_rules_after_star_en if (lang and lang.strip().lower() == "en") else _print_rules_after_star_fr

            _here = os.path.dirname(os.path.abspath(__file__))
            _backend = os.path.dirname(_here)
            _root = os.path.dirname(_backend)
            portfolio_html_dir = None
            for base in [
                os.path.join(_root, "frontend", "src", "portfolio html"),
                os.path.join(_backend, "..", "frontend", "src", "portfolio html"),
                "/app/frontend/src/portfolio html",
                "/frontend/src/portfolio html",
                os.path.join(os.getcwd(), "frontend", "src", "portfolio html"),
                os.path.join(os.getcwd(), "..", "frontend", "src", "portfolio html"),
            ]:
                base = os.path.normpath(os.path.abspath(base))
                modif_path = os.path.join(base, "Modif-2.jpeg")
                bg3_path = os.path.join(base, "Background-3.png")
                if os.path.isfile(modif_path) and os.path.isfile(bg3_path):
                    portfolio_html_dir = base
                    break
            body_bg_css = ""
            if portfolio_html_dir:
                try:
                    with open(os.path.join(portfolio_html_dir, "Modif-2.jpeg"), "rb") as img1:
                        b64_modif = base64.b64encode(img1.read()).decode("ascii")
                    with open(os.path.join(portfolio_html_dir, "Background-3.png"), "rb") as img2:
                        b64_bg3 = base64.b64encode(img2.read()).decode("ascii")
                    data_modif = f"data:image/jpeg;base64,{b64_modif}"
                    data_bg3 = f"data:image/png;base64,{b64_bg3}"
                    html_content = re.sub(
                        r"url\s*\(\s*['\"][^'\"]*Modif-2\.jpeg['\"]\s*\)",
                        f"url('{data_modif}')",
                        html_content,
                    )
                    html_content = re.sub(
                        r"url\s*\(\s*['\"][^'\"]*Background-3\.png['\"]\s*\)",
                        f"url('{data_bg3}')",
                        html_content,
                    )
                    body_bg_css = (
                        " body { background: #0d0d0d !important; background-image: url('" + data_bg3 + "'), url('" + data_modif + "') !important; background-size: cover !important; background-position: center !important; background-repeat: no-repeat !important; " + _exact + " }"
                    )
                    print("✅ Images de fond intégrées en base64 pour le PDF")
                except Exception as e:
                    print(f"⚠️ Impossible d'intégrer les images de fond (PDF): {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"⚠️ Dossier portfolio html introuvable (Modif-2.jpeg / Background-3.png). Le PDF utilisera le @media print injecté sans fond image.")
            pdf_print_style = (
                " /* PDF one-page: règles d'impression injectées par le backend */"
                " @media print { * { " + _exact + " } " + body_bg_css + " " + print_rules + " }"
            )
            html_content = html_content.replace("</style>", pdf_print_style + "\n    </style>", 1)
        
        # Créer un fichier temporaire pour le HTML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_html_path = f.name
        
        # Créer un serveur HTTP local temporaire pour servir le HTML et les ressources
        temp_dir = os.path.dirname(temp_html_path)
        html_filename = os.path.basename(temp_html_path)
        
        # Port aléatoire pour éviter les conflits
        # Essayer de trouver un port disponible
        import random
        max_attempts = 10
        httpd = None
        
        class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=temp_dir, **kwargs)
            
            def log_message(self, format, *args):
                # Réduire les logs
                pass
        
        class ReusableTCPServer(socketserver.TCPServer):
            allow_reuse_address = True
        
        # Essayer plusieurs ports jusqu'à en trouver un disponible
        for attempt in range(max_attempts):
            try:
                port = random.randint(8000, 9000)
                httpd = ReusableTCPServer(("", port), CustomHTTPRequestHandler)
                print(f"✅ Serveur HTTP démarré sur le port {port}")
                break
            except OSError as e:
                if attempt == max_attempts - 1:
                    raise Exception(f"Impossible de trouver un port disponible après {max_attempts} tentatives")
                print(f"⚠️ Port {port} occupé, essai d'un autre port...")
                continue
        
        if httpd is None:
            raise Exception("Impossible de créer le serveur HTTP")
        
        # Démarrer le serveur dans un thread
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        
        try:
            # Utiliser Playwright pour convertir en PDF
            with sync_playwright() as p:
                # Lancer le navigateur
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Charger le HTML depuis le serveur local
                local_url = f"http://localhost:{port}/{html_filename}"
                print(f"🔄 Chargement de {local_url}")
                
                # Taille de la viewport : même format 67,733 cm × 38,1 cm (96 dpi) pour one-page et long
                # pour que le PDF respecte le format du template (--page-w, --page-h)
                cm_w, cm_h = 67.733, 38.1
                inch_w = cm_w / 2.54
                inch_h = cm_h / 2.54
                viewport_width = int(round(inch_w * 96))
                viewport_height = int(round(inch_h * 96))
                page.set_viewport_size({"width": viewport_width, "height": viewport_height})
                
                page.goto(local_url, wait_until='networkidle', timeout=30000)
                
                # Attendre que le JavaScript termine de remplir le template
                # Vérifier que les placeholders ont été remplacés
                try:
                    page.wait_for_function(
                        "document.body.innerHTML && !document.body.innerHTML.includes('{{') && !document.body.innerHTML.includes('{%')",
                        timeout=15000
                    )
                except Exception as e:
                    print(f"⚠️  Timeout attente remplissage template: {e}")
                    # Continuer quand même
                
                # Attendre que les images et polices (Montserrat, Material Symbols) se chargent
                page.wait_for_load_state('networkidle', timeout=10000)
                page.wait_for_timeout(5000 if pdf_page_format == "one-page" else 3000)
                
                # Créer un fichier temporaire pour le PDF
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
                    pdf_path = pdf_file.name
                
                # Générer le PDF : format 67,733 cm × 38,1 cm par page (template portfolio_long)
                pdf_margins = {'top': '0px', 'right': '0px', 'bottom': '0px', 'left': '0px'}
                pdf_width_in = f"{67.733 / 2.54:.3f}in"
                pdf_height_in = f"{38.1 / 2.54:.3f}in"
                if pdf_page_format == "one-page":
                    print(f"🔄 Génération du PDF (one-page 67,733 cm × 38,1 cm)...")
                    page.pdf(
                        path=pdf_path,
                        print_background=True,
                        width=pdf_width_in,
                        height=pdf_height_in,
                        margin=pdf_margins
                    )
                else:
                    # Portfolio long : même taille de page (respect de @page / --page-w, --page-h)
                    print(f"🔄 Génération du PDF (long 67,733 cm × 38,1 cm par page)...")
                    page.pdf(
                        path=pdf_path,
                        print_background=True,
                        width=pdf_width_in,
                        height=pdf_height_in,
                        margin=pdf_margins
                    )
                
                browser.close()
            
            # Arrêter le serveur HTTP
            httpd.shutdown()
            server_thread.join(timeout=2)
            
            # Lire le PDF généré
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            print(f"✅ PDF généré: {len(pdf_bytes)} bytes")
            
            # Sauvegarder dans MinIO (avec suffixe langue si fourni: portfolio_{uuid}_one-page_fr.pdf)
            from candidate_minio_path import get_candidate_minio_prefix
            minio_storage = get_minio_storage()
            minio_prefix = get_candidate_minio_prefix(candidate_id)
            lang_suffix = f"_{lang}" if lang and lang in ("fr", "en") else ""
            if pdf_page_format == "one-page":
                object_name = f"{minio_prefix}portfolio_{candidate_uuid}_one-page{lang_suffix}.pdf"
            else:
                object_name = f"{minio_prefix}portfolio_{candidate_uuid}{lang_suffix}.pdf"
            
            # Supprimer l'ancien PDF de MinIO pour que la prévisualisation affiche bien le nouveau après régénération
            del_ok, _ = minio_storage.delete_file(object_name)
            if del_ok:
                print(f"🗑️ Ancien PDF supprimé de MinIO: {object_name}")
            
            success, url, error = minio_storage.upload_file(
                pdf_bytes,
                object_name,
                content_type="application/pdf"
            )
            
            # Nettoyer les fichiers temporaires
            try:
                os.unlink(temp_html_path)
                os.unlink(pdf_path)
            except:
                pass
            
            if success:
                print(f"✅ PDF généré et uploadé vers MinIO: {url}")
                return True, url, None
            else:
                return False, None, f"Erreur upload PDF vers MinIO: {error}"
                
        except Exception as e:
            # Arrêter le serveur en cas d'erreur
            try:
                httpd.shutdown()
                server_thread.join(timeout=1)
            except:
                pass
            
            # Nettoyer les fichiers temporaires en cas d'erreur
            try:
                os.unlink(temp_html_path)
                if 'pdf_path' in locals():
                    os.unlink(pdf_path)
            except:
                pass
            raise e
            
    except Exception as e:
        error_msg = f"Erreur lors de la conversion HTML en PDF: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, None, error_msg

