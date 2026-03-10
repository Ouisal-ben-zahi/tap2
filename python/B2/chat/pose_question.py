import google.generativeai as genai
import os
import json
import re
import time
from dotenv import load_dotenv

load_dotenv()

# =============================
# CONFIG GEMINI (modèle depuis .env : GOOGLE_MODEL)
# =============================
GEMINI_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")


def _get_model(api_key=None):
    """Retourne un modèle Gemini configuré avec la clé donnée (ou GOOGLE_API_KEY par défaut)."""
    key = (api_key or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not key:
        return None
    genai.configure(api_key=key)
    return genai.GenerativeModel(GEMINI_MODEL)


# Modèle par défaut (clé principale)
model = _get_model()


# =============================
# FONCTION POUR GÉNÉRER LES QUESTIONS
# =============================
def generate_questions_with_gemini(profile_data, talentcard_data=None):
    """
    Génère les questions nécessaires pour collecter les informations d'un portfolio
    professionnel type "portfolio long" à partir du profil du candidat.
    
    Le portfolio utilise uniquement une image de profil (pas d'images/vidéos par projet).
    Génère :
    - EXACTEMENT 2 questions pour chaque projet identifié (détails + liens).
    - EXACTEMENT 1 question pour les soft skills : demander 8 soft skills avec un exemple concret pour chacune.
    
    Si N projets sont identifiés : 2*N questions projets + 1 question soft skills au total.
    
    Args:
        profile_data: dict - Données du profil (expérience, éducation, projets, etc.)
            Peut contenir: experience, education, projects, realisations, etc.
        talentcard_data: dict (optionnel) - Données de la talent card (nom, prénom, etc.)
    
    Returns:
        dict: {
            "success": bool,
            "questions": list,  # Liste de {"id": str, "text": str} - 2 questions par projet
            "error": str (si success=False)
        }
    """
    try:
        # Construire le prompt avec les données du profil
        prompt = f"""
            Tu es un assistant qui prépare des portfolios professionnels type "portfolio long" pour des candidats.
            Le portfolio utilise UNIQUEMENT une image de profil (pas d'images ni de vidéos par projet).
            À partir du profil candidat ci-dessous, génère :
            A) EXACTEMENT 2 QUESTIONS pour CHAQUE projet identifié (Proof of Work du portfolio long).
            B) EXACTEMENT 1 QUESTION pour les soft skills : demander 8 soft skills avec un exemple concret pour chacune.

            RÈGLES IMPORTANTES :
            1. **RÈGLE STRICTE** :
               - GÉNÈRE EXACTEMENT 2 QUESTIONS PAR PROJET (pas plus, pas moins).
               - GÉNÈRE EN PLUS EXACTEMENT 1 QUESTION pour les soft skills (8 soft skills + exemples concrets).
               - Si tu identifies N projets, tu dois retourner 2*N questions projets + 1 question soft skills au total.
               - NE PAS demander d'images, de captures d'écran ni de vidéos pour les projets (seule l'image de profil est utilisée pour tout le portfolio).

            2. **IDENTIFICATION DES PROJETS** :
               - Si le profil contient des "projects" ou "realisations", identifie CHAQUE projet/réalisation comme un projet distinct.
               - Si aucun projet n'est listé mais qu'il y a des "experiences" avec descriptions détaillées,
                 identifie les projets mentionnés dans ces expériences et génère 2 questions pour chacun.
               - Si une expérience décrit un projet spécifique (ex: "Développement d'une plateforme e-commerce"),
                 considère cela comme un projet à part entière.
               - Compte précisément le nombre de projets et génère 2 questions pour chacun.

            3. **CONTENU DES 2 QUESTIONS PAR PROJET** (aligné sur la structure Proof of Work du portfolio long) :

               Question 1 (détails du projet) :
               - Demander les détails complets pour remplir la carte projet : titre, Contexte, Problème, Solution, Stack (technologies),
                 Rôle exact du candidat, Résultat obtenu, Apprentissages, Soft skills mobilisées sur ce projet,
                 Niveau d'autonomie, Qualité de collaboration.
               - Formuler une seule question claire qui invite le candidat à décrire tout cela pour le projet concerné.

               Question 2 (liens de publication) :
               - Demander explicitement les liens où le candidat a publié ou hébergé le projet : GitHub, GitLab, Behance,
                 site de démo, déploiement en ligne, Figma, Dribbble, ou tout autre URL (repository, maquette, démo live).
               - NE PAS demander d'images ni de vidéos, uniquement les liens (URLs).

               Les 2 questions doivent être complémentaires : une pour le contenu détaillé du projet, une pour les liens.

            4. **QUESTION SOFT SKILLS** (obligatoire, en plus des questions projets) :
               - Ajoute EXACTEMENT 1 question avec l'ID "soft_skills_8_examples".
               - Cette question doit demander au candidat de lister 8 soft skills qu'il maîtrise et de donner pour chacune un exemple concret (situation vécue, action, résultat ou preuve).
               - Exemple de formulation : "Pour la section Soft Skills de ton portfolio, liste 8 soft skills que tu maîtrises et pour chacune donne un exemple concret (situation, action, résultat ou preuve)."

            5. **STRUCTURE** :
               - Une question = une information précise.
               - IDs projets : "proj{{N}}_{{type}}" (ex. proj1_details, proj1_links). ID soft skills : "soft_skills_8_examples".
               - Ne pas poser de questions sur les évaluations ou la performance du candidat.
               - Retourne UNIQUEMENT un JSON valide, aucun texte hors JSON.
               - Ordre : d'abord toutes les questions projets (2 par projet), puis la question soft_skills_8_examples en dernier.

            FORMAT ATTENDU :
            {{
            "questions": [
                {{ "id": "proj1_details", "text": "Pour le projet [nom du projet], peux-tu fournir les détails : titre, contexte, problème adressé, solution mise en place, stack technique, ton rôle exact, résultats obtenus, apprentissages et soft skills mobilisées (niveau d'autonomie, qualité de collaboration) ?" }},
                {{ "id": "proj1_links", "text": "Quels sont les liens de ce projet (GitHub, Behance, démo en ligne, GitLab, Figma, etc.) où tu as publié ou hébergé le projet [nom du projet] ?" }},
                {{ "id": "proj2_details", "text": "..." }},
                {{ "id": "proj2_links", "text": "..." }},
                {{ "id": "soft_skills_8_examples", "text": "Pour la section Soft Skills de ton portfolio, liste 8 soft skills que tu maîtrises et pour chacune donne un exemple concret (situation vécue, action, résultat ou preuve)." }}
            ]
            }}

            PROFIL DU CANDIDAT :
            {json.dumps(profile_data, indent=2, ensure_ascii=False)}
        """
        
        
        if talentcard_data:
            prompt += f"\n\nDONNÉES TALENT CARD :\n{json.dumps(talentcard_data, indent=2, ensure_ascii=False)}"
        
        
        max_retries = 4  # 3 tentatives + 1 avec clé secondaire si configurée
        retry_delay = 2
        key_2_tried = False
        model_to_use = model or _get_model()

        for attempt in range(max_retries):
            if not model_to_use:
                return {
                    "success": False,
                    "error": "GOOGLE_API_KEY manquante dans .env",
                    "error_type": "config_error",
                    "questions": []
                }
            try:
                response = model_to_use.generate_content(prompt)
                raw_text = response.text.strip()
                break  # Succès, sortir de la boucle
            except Exception as api_error:
                error_str = str(api_error)

                # Détecter les erreurs de quota (429)
                if "429" in error_str or "quota" in error_str.lower() or "Quota exceeded" in error_str:
                    # Essayer la clé secondaire (autre compte = quota séparé) si pas encore utilisée
                    key_2 = (os.getenv("GOOGLE_API_KEY_2") or "").strip()
                    if key_2 and not key_2_tried:
                        key_2_tried = True
                        model_to_use = _get_model(key_2)
                        print("⚠️  Quota dépassé sur clé principale. Essai avec GOOGLE_API_KEY_2...")
                        continue
                    # Délai de retry : celui indiqué par l'API ou 60 s par défaut
                    retry_after = None
                    if "retry in" in error_str.lower():
                        try:
                            match = re.search(r"retry in ([\d.]+)s", error_str.lower())
                            if match:
                                retry_after = float(match.group(1))
                        except Exception:
                            pass
                    wait_time = (retry_after + 1) if retry_after else 60.0

                    if attempt < max_retries - 1:
                        print(f"⚠️  Quota dépassé. Attente de {wait_time:.1f} secondes avant réessai...")
                        time.sleep(wait_time)
                        continue
                    # Dernière tentative échouée
                    return {
                        "success": False,
                        "error": f"Quota API Gemini dépassé. Ajoutez GOOGLE_API_KEY_2 (autre compte Google) dans .env ou attendez. Détails: {error_str[:200]}",
                        "error_type": "quota_exceeded",
                        "questions": []
                    }
                
                # Détecter les erreurs temporaires (500, 503, etc.)
                elif "500" in error_str or "503" in error_str or "temporarily unavailable" in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Backoff exponentiel
                        print(f"⚠️  Erreur temporaire. Réessai dans {wait_time} secondes...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return {
                            "success": False,
                            "error": f"Erreur temporaire de l'API Gemini après {max_retries} tentatives: {error_str[:200]}",
                            "error_type": "temporary_error",
                            "questions": []
                        }
                
                # Autres erreurs - ne pas retry
                else:
                    raise  # Relancer l'exception pour qu'elle soit gérée par le bloc except externe
        
        # Extraire le JSON de façon robuste
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            json_text = match.group()
            try:
                questions_data = json.loads(json_text)
                questions = questions_data.get("questions", [])
                
                if not questions:
                    return {
                        "success": False,
                        "error": "Aucune question générée",
                        "questions": []
                    }
                
                return {
                    "success": True,
                    "questions": questions,
                    "error": None
                }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Erreur de parsing JSON : {str(e)}",
                    "questions": []
                }
        else:
            return {
                "success": False,
                "error": "Impossible de trouver un JSON dans la réponse de Gemini",
                "questions": []
            }
            
    except Exception as e:
        error_str = str(e)
        
        # Messages d'erreur plus clairs selon le type
        if "429" in error_str or "quota" in error_str.lower():
            error_msg = (
                "Quota API Gemini dépassé. "
                "Limite free tier: 20 requêtes/jour par modèle. "
                "Solutions: attendre le reset quotidien, utiliser un autre modèle, ou passer à un plan payant."
            )
            error_type = "quota_exceeded"
        elif "401" in error_str or "403" in error_str or "invalid api key" in error_str.lower():
            error_msg = "Clé API Gemini invalide ou expirée. Vérifiez GOOGLE_API_KEY dans .env"
            error_type = "auth_error"
        elif "timeout" in error_str.lower():
            error_msg = f"Timeout lors de l'appel à l'API Gemini: {error_str[:200]}"
            error_type = "timeout"
        else:
            error_msg = f"Erreur lors de la génération des questions : {error_str[:300]}"
            error_type = "unknown_error"
        
        return {
            "success": False,
            "error": error_msg,
            "error_type": error_type,
            "questions": []
        }
