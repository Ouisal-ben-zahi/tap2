# ======================================================
# Entretien écrit IA – Ingénieur IA
# Gemini pour générer les questions et traiter les réponses écrites
# Workflow intégré avec récupération des données des agents précédents
# ======================================================

import os
import json
import warnings
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Supprimer le FutureWarning pour google.generativeai (déprécié mais toujours fonctionnel)
warnings.filterwarnings("ignore", category=FutureWarning, message=".*google.generativeai.*")
import google.generativeai as genai

load_dotenv()

# =========================
# GEMINI (modèle depuis .env : GOOGLE_MODEL)
# =========================
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
GEMINI_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
gemini_model = genai.GenerativeModel(GEMINI_MODEL)

# =========================
# RÉCUPÉRATION DES DONNÉES DES AGENTS PRÉCÉDENTS
# =========================

def get_talent_card_from_minio(candidate_id: int):
    
    try:
        from minio_storage import get_minio_storage
        
        minio_storage = get_minio_storage()
        if not minio_storage or not minio_storage.client:
            return False, None, "Client MinIO non initialisé"
        
        try:
            from minio.error import S3Error
            from candidate_minio_path import get_candidate_minio_prefix
            prefix = get_candidate_minio_prefix(candidate_id) + "talentcard_"
            objects = minio_storage.client.list_objects(
                minio_storage.bucket_name,
                prefix=prefix,
                recursive=True
            )
            talentcard_object = None
            for obj in objects:
                if obj.object_name.endswith('.json'):
                    talentcard_object = obj.object_name
                    break
            
            if not talentcard_object:
                return False, None, "Talent Card introuvable dans MinIO"
            
            success, file_bytes, error = minio_storage.download_file(talentcard_object)
            if not success:
                return False, None, error or "Erreur téléchargement Talent Card"
            
            talent_card_data = json.loads(file_bytes.decode('utf-8'))
            return True, talent_card_data, None
            
        except Exception as e:
            return False, None, f"Erreur lors de la recherche de la Talent Card: {str(e)}"
            
    except Exception as e:
        return False, None, f"Erreur lors de la récupération de la Talent Card: {str(e)}"


def get_corrected_cv_from_minio(candidate_id: int):
    """Récupère le CV corrigé (B1) depuis MinIO. Cherche corrected_cv/corrected_data.json puis corrected_data_*.json."""
    try:
        from minio_storage import get_minio_storage
        
        minio_storage = get_minio_storage()
        if not minio_storage or not minio_storage.client:
            return False, None, "Client MinIO non initialisé"
        
        from candidate_minio_path import get_candidate_minio_prefix
        minio_pre = get_candidate_minio_prefix(candidate_id)
        object_name_legacy = f"{minio_pre}corrected_cv/corrected_data.json"
        success, file_bytes, error = minio_storage.download_file(object_name_legacy)
        if success and file_bytes:
            corrected_cv_data = json.loads(file_bytes.decode('utf-8'))
            return True, corrected_cv_data, None
        
        try:
            objects = list(minio_storage.client.list_objects(
                minio_storage.bucket_name,
                prefix=minio_pre + "corrected_data_",
                recursive=True
            ))
            json_objects = [obj for obj in objects if obj.object_name.endswith('.json')]
            if json_objects:
                latest = sorted(json_objects, key=lambda o: getattr(o, 'last_modified', None) or 0, reverse=True)[0]
                success, file_bytes, error = minio_storage.download_file(latest.object_name)
                if success and file_bytes:
                    corrected_cv_data = json.loads(file_bytes.decode('utf-8'))
                    return True, corrected_cv_data, None
        except Exception:
            pass
        return False, None, None
    except Exception as e:
        return False, None, None


def get_chat_responses_from_minio(candidate_id: int):
    """Récupère les réponses du chatbot (B2) depuis MinIO."""
    try:
        from B2.chat.save_responses import get_chat_responses_from_minio as get_chat
        return get_chat(candidate_id)
    except Exception as e:
        return False, None, None


def get_portfolio_from_minio(candidate_id: int, candidate_uuid: str = None):
    """Récupère le portfolio (B2) depuis MinIO."""
    try:
        from minio_storage import get_minio_storage
        
        from candidate_minio_path import get_candidate_minio_prefix
        minio_pre = get_candidate_minio_prefix(candidate_id)
        if candidate_uuid:
            object_name = f"{minio_pre}portfolio_{candidate_uuid}.json"
        else:
            object_name = f"{minio_pre}portfolio_*.json"
        
        minio_storage = get_minio_storage()
        if not minio_storage or not minio_storage.client:
            return False, None, "Client MinIO non initialisé"
        
        if candidate_uuid:
            object_name = f"{minio_pre}portfolio_{candidate_uuid}.json"
            success, file_bytes, error = minio_storage.download_file(object_name)
            if not success:
                return False, None, None
        else:
            try:
                objects = minio_storage.client.list_objects(
                    minio_storage.bucket_name,
                    prefix=minio_pre + "portfolio_",
                    recursive=True
                )
                portfolio_object = None
                for obj in objects:
                    if obj.object_name.endswith('.json'):
                        portfolio_object = obj.object_name
                        break
                
                if not portfolio_object:
                    return False, None, None
                
                success, file_bytes, error = minio_storage.download_file(portfolio_object)
                if not success:
                    return False, None, error or "Erreur téléchargement Portfolio"
            except Exception as e:
                return False, None, f"Erreur lors de la recherche du Portfolio: {str(e)}"
        
        portfolio_data = json.loads(file_bytes.decode('utf-8'))
        return True, portfolio_data, None
        
    except Exception as e:
        return False, None, None


def get_candidate_data_from_db(candidate_id: int):
    """Récupère les données de base du candidat depuis la base de données."""
    try:
        from database.connection import DatabaseConnection
        
        DatabaseConnection.initialize()
        
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, prenom, nom, titre_profil, email, phone, 
                       annees_experience, ville, pays, linkedin
                FROM candidates 
                WHERE id = %s
                """,
                (candidate_id,)
            )
            row = cursor.fetchone()
            cursor.close()
        
        if not row:
            return False, None, f"Candidat {candidate_id} introuvable en base de données"
        
        return True, dict(row), None
        
    except Exception as e:
        return False, None, f"Erreur lors de la récupération des données candidat: {str(e)}"


def retrieve_all_agent_data(candidate_id: int, candidate_uuid: Optional[str] = None) -> Dict:
    """Récupère toutes les données des agents précédents pour un candidat (en parallèle)."""
    print(f"\n🔄 Récupération des données des agents précédents pour candidat {candidate_id} (parallèle)...")
    
    all_data = {
        "candidate_id": candidate_id,
        "candidate_uuid": candidate_uuid,
        "talent_card": None,
        "corrected_cv": None,
        "chat_responses": None,
        "portfolio": None,
        "candidate_db": None,
        "errors": []
    }
    
    def fetch_db():
        return ("candidate_db", get_candidate_data_from_db(candidate_id))
    def fetch_talent():
        return ("talent_card", get_talent_card_from_minio(candidate_id))
    def fetch_cv():
        return ("corrected_cv", get_corrected_cv_from_minio(candidate_id))
    def fetch_chat():
        return ("chat_responses", get_chat_responses_from_minio(candidate_id))
    def fetch_portfolio():
        return ("portfolio", get_portfolio_from_minio(candidate_id, candidate_uuid))
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_db): "candidate_db",
            executor.submit(fetch_talent): "talent_card",
            executor.submit(fetch_cv): "corrected_cv",
            executor.submit(fetch_chat): "chat_responses",
            executor.submit(fetch_portfolio): "portfolio",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                name, (success, data, error) = future.result()
                if success and data is not None:
                    all_data[name] = data
                elif error:
                    all_data["errors"].append(f"{key}: {error}")
            except Exception as e:
                all_data["errors"].append(f"{key}: {str(e)}")
    
    return all_data


def build_written_interview_prompt_from_data(agent_data: Dict) -> str:
    """
    Construit le prompt d'entretien écrit personnalisé à partir des données des agents précédents.
    
    Args:
        agent_data: Dictionnaire contenant toutes les données récupérées
    
    Returns:
        Prompt d'entretien écrit personnalisé
    """
    # Récupérer le poste visé depuis le portfolio
    job_title = "Ingénieur IA"  # Par défaut
    portfolio = agent_data.get("portfolio")
    if portfolio:
        portfolio_sections = portfolio.get("portfolio_sections", [])
        for section in portfolio_sections:
            if section.get("section_key") == "hero":
                content = section.get("content", {})
                job_title = content.get("job_title") or content.get("title") or job_title
                break
    
    # Si pas trouvé dans le portfolio, chercher dans le CV corrigé ou Talent Card
    if job_title == "Ingénieur IA":
        corrected_cv = agent_data.get("corrected_cv")
        if corrected_cv:
            job_title = corrected_cv.get("Titre", job_title)
        
        if job_title == "Ingénieur IA":
            talent_card = agent_data.get("talent_card")
            if talent_card:
                job_title = talent_card.get("Titre de profil", job_title)
    
    base_prompt = f"""
Tu es un VRAI recruteur senior : humain, à l'écoute, qui mène une CONVERSATION avec le candidat, pas un robot qui enchaîne des questions.

Tu mènes un entretien écrit pour un poste de {job_title}. Tu as lu son CV, sa Talent Card, son portfolio et ses réponses sur ses projets. Tu connais bien son profil.

DÉROULEMENT DE L'ENTRETIEN (comme tout recruteur) :
- PREMIÈRE QUESTION OBLIGATOIRE : demande au candidat de se PRÉSENTER, comme le font tous les recruteurs. Ex. : "Pour commencer, pouvez-vous vous présenter brièvement ? Parlez-moi de votre parcours et de ce qui vous amène vers ce poste." ou "Commençons par une présentation : qui êtes-vous, votre parcours en quelques mots ?" Le candidat n'a pas encore répondu : ne dis JAMAIS "merci pour votre réponse" à la première question.
- À partir de la 2e question : réagis brièvement à ce qu'il vient de dire (reprise, intérêt, lien) puis pose ta question. Montre que tu as LU sa réponse.
- Parle comme un recruteur : naturel, professionnel mais chaleureux. Pas de formules robotiques ni de questions isolées sans contexte.
- Comprends bien le profil : adapte ton vocabulaire et tes sujets au métier (IA, design, dev, édition, etc.) et aux expériences/projets du candidat. Fais référence à des éléments concrets de son parcours quand c'est pertinent.

THÈMES À COUVRIR (répartis sur les 10 questions – NE PAS rester sur un seul projet) :
1. Présentation du candidat (parcours, motivation) – première question.
2. Expériences professionnelles : pose des questions sur PLUSIEURS expériences ou postes, pas seulement une. Ex. : "Sur votre expérience chez X, comment… ?" puis plus tard "Et dans votre rôle chez Y, vous avez… ?"
3. Projets : si le candidat a plusieurs projets (CV, portfolio, chatbot), pose des questions sur PLUSIEURS projets au fil de l'entretien, pas uniquement sur un seul. Alterne ou rebondis sur différents projets/expériences.
4. Logiciels et outils en lien avec le poste : demande quels logiciels, frameworks, outils métier il a déjà utilisés (ex. : "Quels outils ou logiciels utilisez-vous au quotidien ?", "Avez-vous déjà travaillé avec [outils typiques du poste] ?").
Adapte ces thèmes au poste visé ({job_title}) et au profil du candidat.

Règles techniques :
- Pose UNE seule question à la fois (éventuellement précédée d'une courte réaction à sa dernière réponse).
- Total : 10 questions. Niveau progressif, varié (présentation, expériences, projets, outils).
- Langue : français. Ton professionnel mais bienveillant.
- Chaque tour reste COURT : 2 à 3 phrases max (réaction + question). Pas de longs paragraphes.

Validation des réponses :
- Si la réponse est trop courte (moins de 20 mots), vague ou test, demande poliment de développer.
- Ne passe pas à une nouvelle question si la réponse n'est pas pertinente ; demande une précision.
"""
    
    # Construire le contexte du candidat (même logique que pour l'entretien oral)
    context_parts = []
    
    # Informations de base
    candidate_db = agent_data.get("candidate_db", {})
    if candidate_db:
        prenom = candidate_db.get("prenom", "")
        nom = candidate_db.get("nom", "")
        titre = candidate_db.get("titre_profil", "")
        annees_exp = candidate_db.get("annees_experience", 0)
        
        if prenom or nom:
            context_parts.append(f"**Candidat:** {prenom} {nom}")
        if titre:
            context_parts.append(f"**Titre professionnel:** {titre}")
        if annees_exp:
            context_parts.append(f"**Années d'expérience:** {annees_exp} ans")
    
    # Ajouter le poste visé
    context_parts.append(f"**Poste visé:** {job_title}")
    
    # Talent Card (A1)
    talent_card = agent_data.get("talent_card")
    if talent_card:
        context_parts.append("\n**PROFIL DU CANDIDAT (Talent Card):**")
        
        resume = talent_card.get("resume_bref", "")
        if resume:
            context_parts.append(f"- Résumé: {resume}")
        
        skills = talent_card.get("skills", [])
        if skills:
            skills_str = ", ".join(skills[:10]) if isinstance(skills, list) else str(skills)
            context_parts.append(f"- Compétences clés: {skills_str}")
        
        experiences = talent_card.get("experience", [])
        if experiences and isinstance(experiences, list):
            context_parts.append("- Expériences professionnelles:")
            for exp in experiences[:3]:
                if isinstance(exp, dict):
                    role = exp.get("Role", exp.get("role", ""))
                    entreprise = exp.get("entreprise", "")
                    if role or entreprise:
                        context_parts.append(f"  • {role} chez {entreprise}")
        
        realisations = talent_card.get("realisations", [])
        if realisations:
            context_parts.append("- Réalisations clés:")
            for real in realisations[:3]:
                if isinstance(real, dict):
                    desc = real.get("description", real.get("titre", str(real)))
                else:
                    desc = str(real)
                context_parts.append(f"  • {desc}")
    
    # CV Corrigé (B1)
    corrected_cv = agent_data.get("corrected_cv")
    if corrected_cv:
        context_parts.append("\n**CV CORRIGÉ:**")
        
        name = corrected_cv.get("Name", "")
        titre_cv = corrected_cv.get("Titre", "")
        if name:
            context_parts.append(f"- Nom: {name}")
        if titre_cv:
            context_parts.append(f"- Titre: {titre_cv}")
        
        experiences_cv = corrected_cv.get("Experiences", [])
        if experiences_cv:
            context_parts.append("- Expériences détaillées:")
            for exp in experiences_cv[:3]:
                if isinstance(exp, dict):
                    title = exp.get("title", "")
                    company = exp.get("company", "")
                    desc = exp.get("description", "")
                    if title or company:
                        context_parts.append(f"  • {title} @ {company}")
                        if desc:
                            context_parts.append(f"    {desc[:150]}...")
        
        realisations_cv = corrected_cv.get("Realisations", [])
        if realisations_cv:
            context_parts.append("- Réalisations:")
            for real in realisations_cv[:3]:
                if isinstance(real, dict):
                    nom_real = real.get("nom", "")
                    detail = real.get("detail", "")
                    if nom_real:
                        context_parts.append(f"  • {nom_real}: {detail[:100]}...")
    
    # Réponses du Chatbot (B2) - Projets
    chat_responses = agent_data.get("chat_responses")
    if chat_responses:
        context_parts.append("\n**PROJETS RÉALISÉS (réponses du chatbot):**")
        
        answers = chat_responses.get("answers", {})
        projects_list = chat_responses.get("projects_list", [])
        
        if projects_list:
            context_parts.append(f"- Projets identifiés: {', '.join(projects_list)}")
        
        # Extraire quelques réponses clés sur les projets
        project_answers = []
        for q_id, answer in list(answers.items())[:5]:
            if "proj" in q_id.lower() and answer:
                project_answers.append(f"  • {answer[:200]}...")
        
        if project_answers:
            context_parts.extend(project_answers[:3])
    
    # Portfolio (B2)
    portfolio = agent_data.get("portfolio")
    if portfolio:
        context_parts.append("\n**PORTFOLIO:**")
        
        portfolio_sections = portfolio.get("portfolio_sections", [])
        for section in portfolio_sections[:3]:
            section_key = section.get("section_key", "")
            content = section.get("content", {})
            
            if section_key == "hero":
                portfolio_job_title = content.get("job_title", content.get("title", ""))
                if portfolio_job_title:
                    context_parts.append(f"- Poste visé dans le portfolio: {portfolio_job_title}")
            
            elif section_key == "projects":
                projects = content if isinstance(content, list) else []
                if projects:
                    context_parts.append(f"- {len(projects)} projets détaillés dans le portfolio")
                    # Ajouter quelques détails sur les projets principaux
                    for proj in projects[:2]:
                        if isinstance(proj, dict):
                            proj_name = proj.get("name", proj.get("title", ""))
                            proj_desc = proj.get("description", "")[:150]
                            if proj_name:
                                context_parts.append(f"  • {proj_name}: {proj_desc}...")
    
    # Construire le prompt final
    context_str = "\n".join(context_parts) if context_parts else "Aucune information contextuelle disponible."
    
    full_prompt = f"""{base_prompt}

---
**CONTEXTE DU CANDIDAT:**
{context_str}

---
**INSTRUCTIONS POUR L'ENTRETIEN ÉCRIT:**
- PREMIER MESSAGE (le candidat n'a pas encore répondu) : demande au candidat de se PRÉSENTER (comme tout recruteur). Ex. : "Pour commencer, pouvez-vous vous présenter brièvement ? Parlez-moi de votre parcours et de ce qui vous amène vers ce poste." Ne dis pas "merci pour votre réponse" au premier message.
- À partir du 2e message : réagis brièvement à sa réponse puis pose ta question. Varie les sujets : présentation, puis expériences (plusieurs), projets (plusieurs), logiciels/outils métier. NE PAS enchaîner toutes les questions sur un seul projet.
- Utilise le contexte ci-dessus : prénom, poste visé, expériences, projets, compétences. Fais référence à plusieurs expériences ou projets au fil de l'entretien.
- Pose des questions qui s'enchaînent naturellement : creuse un point qu'il a évoqué, ou rebondis sur une autre expérience/projet. Demande aussi quels logiciels ou outils il utilise en lien avec le poste.
- Adapte le niveau et les thèmes au métier (design, dev, IA, édition, etc.) et aux années d'expérience.
- Reste court : 2 à 3 phrases par tour (réaction + question). Pas de long texte.
"""
    
    return full_prompt


# =========================
# PROMPT ENTRETIEN ÉCRIT (par défaut, sans données)
# =========================
INTERVIEW_WRITTEN_PROMPT_DEFAULT = """
Tu es un VRAI recruteur : tu mènes une CONVERSATION avec le candidat, pas un questionnaire.
- PREMIÈRE QUESTION : demande au candidat de se PRÉSENTER (comme tout recruteur). Ex. : "Pour commencer, pouvez-vous vous présenter brièvement ? Parlez-moi de votre parcours."
- À partir du 2e tour : réagis brièvement à ce qu'il vient de dire, puis pose ta question. Varie les sujets : expériences (plusieurs), projets (plusieurs), logiciels/outils en lien avec le poste. Ne reste pas sur un seul projet.
- Poste et métier sont dans le contexte (IA, Designer, Dev, Éditeur, etc.) : adapte tes questions en conséquence. Demande aussi quels outils/logiciels il utilise.
- Total : 10 questions. Une seule question par tour (éventuellement précédée d'une courte réaction). Reste court : 2 à 3 phrases.
- Ton naturel, professionnel, pas robotique.
"""


def ask_gemini_written(user_text: str, conversation_history: str) -> tuple:
    """
    Pose une question à Gemini avec l'historique de conversation pour l'entretien écrit.
    
    Args:
        user_text: Texte de l'utilisateur
        conversation_history: Historique de la conversation
    
    Returns:
        Tuple (réponse, nouvel historique)
    """
    # Vérifier si la réponse semble être un test ou non pertinente
    user_text_lower = user_text.lower().strip()
    test_keywords = ["test", "testing", "test test", "essai", "check"]
    is_test = any(keyword in user_text_lower for keyword in test_keywords) and len(user_text_lower.split()) <= 3
    
    if is_test or len(user_text.strip()) < 20:
        # Si c'est un test ou trop court, demander poliment de développer
        prompt_addition = "\n\nIMPORTANT: La réponse du candidat semble être un test ou trop courte. Demande-lui poliment de développer sa réponse de manière plus complète et détaillée. Sois bref et professionnel."
    else:
        prompt_addition = ""
    
    new_history = conversation_history + f"\nCandidat: {user_text}{prompt_addition}"
    response = gemini_model.generate_content(new_history)
    response_text = (response.text or "").strip()
    updated_history = new_history + f"\nRecruteur: {response_text}"
    return response_text, updated_history
