# ======================================================
# Évaluation du candidat après l'entretien oral
# ======================================================

import os
import json
import time
from typing import Dict, Optional, Tuple
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configuration Gemini (modèle depuis .env : GOOGLE_MODEL)
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
GEMINI_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
gemini_model = genai.GenerativeModel(GEMINI_MODEL)


def evaluate_candidate_interview(
    conversation_history: str,
    candidate_data: Optional[Dict] = None
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Évalue le candidat en fonction de l'historique de conversation de l'entretien.
    
    Args:
        conversation_history: Historique complet de la conversation (questions + réponses)
        candidate_data: Données du candidat (optionnel)
    
    Returns:
        Tuple (success, evaluation_data, error_message)
    """
    try:
        # Récupérer les informations du candidat si disponibles
        prenom = ""
        nom = ""
        titre_poste = ""
        
        if candidate_data:
            prenom = candidate_data.get("prenom", "")
            nom = candidate_data.get("nom", "")
            titre_poste = candidate_data.get("titre_profil", "Ingénieur IA")
        
        candidat_nom_complet = f"{prenom} {nom}".strip() or "le candidat"
        
        # Construire le prompt d'évaluation
        evaluation_prompt = f"""
Tu es un expert en recrutement et évaluation de candidats en Intelligence Artificielle.
Tu dois analyser l'entretien ci-dessous et fournir une évaluation détaillée et constructive du candidat.

**INFORMATIONS DU CANDIDAT:**
- Nom: {candidat_nom_complet}
- Poste visé: {titre_poste}

**HISTORIQUE DE L'ENTRETIEN:**
{conversation_history}

═══════════════════════════════════════════════════════════════════

**CONSIGNES D'ÉVALUATION:**

Analyse l'entretien et évalue le candidat sur les critères suivants (note de 0 à 10 pour chaque):

1. **CONNAISSANCES TECHNIQUES** (0-10)
   - Profondeur des connaissances en IA/ML
   - Compréhension des concepts théoriques
   - Maîtrise des technologies mentionnées

2. **EXPÉRIENCE PRATIQUE** (0-10)
   - Qualité des exemples de projets donnés
   - Capacité à expliquer les défis rencontrés
   - Solutions techniques apportées

3. **COMMUNICATION** (0-10)
   - Clarté des explications
   - Structure des réponses
   - Capacité à vulgariser des concepts complexes

4. **GESTION DU STRESS** (0-10)
   - Confiance dans les réponses
   - Gestion des questions difficiles
   - Cohérence tout au long de l'entretien

5. **RÉFLEXION CRITIQUE** (0-10)
   - Capacité d'analyse
   - Remise en question
   - Conscience des limites et défis

6. **ADAPTATION AU POSTE** (0-10)
   - Alignement avec le poste visé
   - Pertinence des compétences
   - Potentiel d'évolution

**FORMAT DE RÉPONSE OBLIGATOIRE (JSON):**

Retourne UNIQUEMENT un objet JSON valide avec cette structure exacte:

{{
  "note_globale": <float entre 0 et 10>,
  "appreciation_generale": "<résumé en 2-3 phrases>",
  "criteres": {{
    "connaissances_techniques": {{
      "note": <float entre 0 et 10>,
      "commentaire": "<analyse détaillée>"
    }},
    "experience_pratique": {{
      "note": <float entre 0 et 10>,
      "commentaire": "<analyse détaillée>"
    }},
    "communication": {{
      "note": <float entre 0 et 10>,
      "commentaire": "<analyse détaillée>"
    }},
    "gestion_stress": {{
      "note": <float entre 0 et 10>,
      "commentaire": "<analyse détaillée>"
    }},
    "reflexion_critique": {{
      "note": <float entre 0 et 10>,
      "commentaire": "<analyse détaillée>"
    }},
    "adaptation_poste": {{
      "note": <float entre 0 et 10>,
      "commentaire": "<analyse détaillée>"
    }}
  }},
  "points_forts": [
    "<point fort 1>",
    "<point fort 2>",
    "<point fort 3>"
  ],
  "points_a_ameliorer": [
    "<point à améliorer 1>",
    "<point à améliorer 2>",
    "<point à améliorer 3>"
  ],
  "recommandations": [
    "<recommandation 1>",
    "<recommandation 2>",
    "<recommandation 3>"
  ],
  "niveau_preparation": "<EXCELLENT|TRÈS BON|BON|À AMÉLIORER|NÉCESSITE PLUS D'ENTRAÎNEMENT>",
  "message_encouragement": "<message positif et encourageant pour motiver le candidat>"
}}

IMPORTANT: 
- Retourne UNIQUEMENT le JSON, sans texte avant ou après
- Sois TOUJOURS constructif, bienveillant et ENCOURAGEANT dans tes commentaires
- Rappelle-toi que c'est une SIMULATION D'ENTRAÎNEMENT pour aider le candidat à progresser
- Évite les jugements négatifs ou décourageants - focus sur les axes d'amélioration
- Base-toi sur des éléments concrets de l'entretien
- Les notes doivent être cohérentes avec les commentaires
- Le message d'encouragement doit être motivant et spécifique aux efforts du candidat
"""
        
        print("🔄 Analyse de l'entretien en cours...")
        
        # Appeler Gemini pour l'évaluation
        response = gemini_model.generate_content(evaluation_prompt)
        response_text = response.text.strip()
        
        # Extraire le JSON de la réponse
        evaluation_data = extract_json_from_response(response_text)
        
        if not evaluation_data:
            return False, None, "Erreur lors de l'extraction du JSON d'évaluation"
        
        # Ajouter des métadonnées
        evaluation_data["candidate_name"] = candidat_nom_complet
        evaluation_data["poste_vise"] = titre_poste
        evaluation_data["timestamp"] = time.time()
        evaluation_data["date_evaluation"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        print("✅ Évaluation du candidat terminée")
        return True, evaluation_data, None
        
    except Exception as e:
        error_msg = f"Erreur lors de l'évaluation du candidat: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, None, error_msg


def extract_json_from_response(text: str) -> Optional[Dict]:
    """
    Extrait le JSON de la réponse de Gemini.
    
    Args:
        text: Texte de la réponse
    
    Returns:
        Dictionnaire JSON ou None
    """
    try:
        # Nettoyer le texte (enlever les markdown code blocks si présents)
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Parser le JSON
        json_data = json.loads(text)
        return json_data
        
    except json.JSONDecodeError as e:
        print(f"⚠️ Erreur parsing JSON: {e}")
        print(f"Texte reçu: {text[:500]}...")
        
        # Tentative de récupération: chercher un objet JSON dans le texte
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                json_data = json.loads(json_match.group())
                return json_data
            except:
                pass
        
        return None


def save_evaluation_to_minio(candidate_id: int, candidate_uuid: str, evaluation_data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Sauvegarde l'évaluation dans MinIO.
    
    Args:
        candidate_id: ID du candidat
        candidate_uuid: UUID du candidat
        evaluation_data: Données d'évaluation
    
    Returns:
        Tuple (success, error_message)
    """
    try:
        from minio_storage import get_minio_storage
        
        from candidate_minio_path import get_candidate_minio_prefix
        minio_storage = get_minio_storage()
        if not minio_storage or not minio_storage.client:
            return False, "Client MinIO non initialisé"
        
        # Préparer le nom du fichier
        object_name = f"{get_candidate_minio_prefix(candidate_id)}interview_evaluation_{candidate_uuid}.json"
        
        # Convertir en JSON
        json_data = json.dumps(evaluation_data, ensure_ascii=False, indent=2)
        json_bytes = json_data.encode('utf-8')
        
        # Uploader vers MinIO
        success, error, _ = minio_storage.upload_file(
            file_bytes=json_bytes,
            object_name=object_name,
            content_type="application/json"
        )
        
        if success:
            print(f"✅ Évaluation sauvegardée dans MinIO: {object_name}")
            return True, None
        else:
            return False, error or "Erreur lors de l'upload vers MinIO"
            
    except Exception as e:
        error_msg = f"Erreur lors de la sauvegarde de l'évaluation: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg


def format_evaluation_for_display(evaluation_data: Dict) -> str:
    """
    Formate l'évaluation pour un affichage lisible.
    
    Args:
        evaluation_data: Données d'évaluation
    
    Returns:
        Texte formaté
    """
    try:
        note_globale = evaluation_data.get("note_globale", 0)
        appreciation = evaluation_data.get("appreciation_generale", "")
        decision = evaluation_data.get("decision_recommandee", "")
        
        # Header
        output = f"\n{'='*70}\n"
        output += f"📊 ÉVALUATION DE L'ENTRETIEN\n"
        output += f"{'='*70}\n\n"
        
        # Note globale
        output += f"🎯 NOTE GLOBALE: {note_globale:.1f}/10\n\n"
        
        # Appréciation générale
        output += f"💬 APPRÉCIATION GÉNÉRALE:\n{appreciation}\n\n"
        
        # Critères détaillés
        output += f"{'─'*70}\n"
        output += f"📋 ÉVALUATION DÉTAILLÉE PAR CRITÈRE\n"
        output += f"{'─'*70}\n\n"
        
        criteres = evaluation_data.get("criteres", {})
        criteres_ordre = [
            ("connaissances_techniques", "📚 Connaissances Techniques"),
            ("experience_pratique", "🛠️ Expérience Pratique"),
            ("communication", "💬 Communication"),
            ("gestion_stress", "🧘 Gestion du Stress"),
            ("reflexion_critique", "🤔 Réflexion Critique"),
            ("adaptation_poste", "🎯 Adaptation au Poste")
        ]
        
        for key, label in criteres_ordre:
            if key in criteres:
                critere = criteres[key]
                note = critere.get("note", 0)
                commentaire = critere.get("commentaire", "")
                output += f"{label}: {note:.1f}/10\n"
                output += f"   {commentaire}\n\n"
        
        # Points forts
        output += f"{'─'*70}\n"
        output += f"✅ POINTS FORTS\n"
        output += f"{'─'*70}\n"
        for i, point in enumerate(evaluation_data.get("points_forts", []), 1):
            output += f"{i}. {point}\n"
        output += "\n"
        
        # Points à améliorer
        output += f"{'─'*70}\n"
        output += f"📈 POINTS À AMÉLIORER\n"
        output += f"{'─'*70}\n"
        for i, point in enumerate(evaluation_data.get("points_a_ameliorer", []), 1):
            output += f"{i}. {point}\n"
        output += "\n"
        
        # Recommandations
        output += f"{'─'*70}\n"
        output += f"💡 RECOMMANDATIONS\n"
        output += f"{'─'*70}\n"
        for i, reco in enumerate(evaluation_data.get("recommandations", []), 1):
            output += f"{i}. {reco}\n"
        output += "\n"
        
        # Niveau de préparation
        niveau_preparation = evaluation_data.get("niveau_preparation", "BON")
        message_encouragement = evaluation_data.get("message_encouragement", "Continuez vos efforts!")
        
        output += f"{'='*70}\n"
        output += f"🎯 NIVEAU DE PRÉPARATION: {niveau_preparation}\n\n"
        output += f"💪 MESSAGE D'ENCOURAGEMENT:\n{message_encouragement}\n"
        output += f"{'='*70}\n"
        
        return output
        
    except Exception as e:
        print(f"⚠️ Erreur formatage évaluation: {e}")
        return "Erreur lors du formatage de l'évaluation"


def generate_vocal_feedback(evaluation_data: Dict) -> str:
    """
    Génère un feedback vocal concis pour le candidat.
    
    Args:
        evaluation_data: Données d'évaluation
    
    Returns:
        Texte à lire vocalement
    """
    try:
        note_globale = evaluation_data.get("note_globale", 0)
        appreciation = evaluation_data.get("appreciation_generale", "")
        niveau_preparation = evaluation_data.get("niveau_preparation", "BON")
        message_encouragement = evaluation_data.get("message_encouragement", "")
        
        # Message d'introduction positif
        feedback = f"Félicitations ! Vous avez terminé votre simulation d'entretien. "
        
        # Note globale avec encouragement
        if note_globale >= 8:
            feedback += f"Excellent ! Vous avez obtenu une note de {note_globale:.1f} sur 10. "
        elif note_globale >= 6:
            feedback += f"Très bien ! Vous avez obtenu une note de {note_globale:.1f} sur 10. "
        elif note_globale >= 4:
            feedback += f"Vous avez obtenu une note de {note_globale:.1f} sur 10. Vous êtes sur la bonne voie ! "
        else:
            feedback += f"Vous avez obtenu une note de {note_globale:.1f} sur 10. Chaque entretien est une opportunité d'apprendre ! "
        
        # Appréciation
        feedback += f"{appreciation} "
        
        # Points forts (max 2)
        points_forts = evaluation_data.get("points_forts", [])[:2]
        if points_forts:
            feedback += f"Vos principaux points forts sont : {', et '.join(points_forts)}. "
        
        # Points à améliorer avec tournure positive (max 2)
        points_ameliorer = evaluation_data.get("points_a_ameliorer", [])[:2]
        if points_ameliorer:
            feedback += f"Pour progresser davantage, concentrez-vous sur : {', et '.join(points_ameliorer)}. "
        
        # Message d'encouragement personnalisé
        if message_encouragement:
            feedback += f"{message_encouragement} "
        
        # Conclusion positive
        feedback += f"Un rapport détaillé de votre évaluation vous sera envoyé par email. Continuez à vous entraîner, chaque entretien vous rend plus performant !"
        
        return feedback
        
    except Exception as e:
        print(f"⚠️ Erreur génération feedback vocal: {e}")
        return "Merci d'avoir participé à cet entretien. Votre évaluation détaillée vous sera envoyée par email."
