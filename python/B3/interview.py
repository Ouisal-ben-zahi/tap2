# ======================================================
# Entretien oral IA – Ingénieur IA
# Whisper + Gemini + Coqui TTS + VAD (STABLE)
# Workflow intégré avec récupération des données des agents précédents
# ======================================================

import os
import time
import json
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import whisper
import warnings
# Supprimer le FutureWarning pour google.generativeai (déprécié mais toujours fonctionnel)
warnings.filterwarnings("ignore", category=FutureWarning, message=".*google.generativeai.*")
import google.generativeai as genai
from TTS.api import TTS
import simpleaudio as sa
import webrtcvad
from dotenv import load_dotenv
from typing import Dict, Optional, Tuple
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
load_dotenv()
# =========================
# CONFIG AUDIO (CRUCIAL)
# =========================
AUDIO_INPUT = "input.wav"
AUDIO_OUTPUT = "response.wav"

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 20
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # 320 samples

# =========================
# GEMINI (modèle depuis .env : GOOGLE_MODEL)
# =========================
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
GEMINI_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
gemini_model = genai.GenerativeModel(GEMINI_MODEL)

# =========================
# WHISPER (small = rapide sur CPU, medium = plus précis mais lent)
# =========================
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
whisper_model = whisper.load_model(WHISPER_MODEL)

# =========================
# COQUI TTS – VOIX FR
# =========================
tts = TTS(
    model_name="tts_models/fr/css10/vits",
    progress_bar=False,
    gpu=False
)

# Sélectionner un speaker pour le modèle multi-speaker
if hasattr(tts, 'speakers') and tts.speakers:
    # Nettoyer les speakers (enlever les \n)
    clean_speakers = [s.strip() for s in tts.speakers if s.strip()]
    # Sélectionner le premier speaker disponible
    TTS_SPEAKER = clean_speakers[0] if clean_speakers else None
    print(f"🎤 Speaker TTS sélectionné: {TTS_SPEAKER}")
else:
    TTS_SPEAKER = None

# =========================
# TEXT TO SPEECH
# =========================
def speak(text):
    text = text.replace("'", "'")
    # Utiliser speaker et language pour le modèle multi-speaker
    if TTS_SPEAKER:
        tts.tts_to_file(text=text, file_path=AUDIO_OUTPUT, speaker=TTS_SPEAKER, language="fr-fr")
    else:
        tts.tts_to_file(text=text, file_path=AUDIO_OUTPUT)
    wave = sa.WaveObject.from_wave_file(AUDIO_OUTPUT)
    play = wave.play()
    play.wait_done()

# =========================
# SPEECH TO TEXT
# =========================
def speech_to_text():
    result = whisper_model.transcribe(AUDIO_INPUT, language="fr")
    return result["text"].strip()

# =========================
# RECORD AUDIO WITH VAD (FIX)
# =========================
def record_audio_vad(filename=AUDIO_INPUT):
    # Réinitialiser complètement à chaque appel
    vad = webrtcvad.Vad(1)  # Mode plus sensible (0-3, 0=le plus sensible)
    all_frames = []
    frames = []
    silence_frames = 0
    max_silence = 40  # ~800 ms de silence avant arrêt
    min_speech_frames = 3  # Minimum de frames avec parole détectée
    min_recording_time = 1.5  # Minimum 1.5 secondes d'enregistrement avant d'accepter l'arrêt
    stream_stopped = False

    print("🎙️ Parlez (pause = fin de réponse)...")

    def callback(indata, frame_count, time_info, status):
        nonlocal frames, all_frames, silence_frames, stream_stopped
        
        if stream_stopped:
            return
        
        if status:
            print(f"⚠️ Status audio: {status}")

        # Gérer mono/stereo
        if indata.ndim > 1:
            audio = indata[:, 0]  # mono depuis stéréo
        else:
            audio = indata  # déjà mono
        
        # Vérifier la taille du frame
        if len(audio) != FRAME_SIZE:
            return
        
        # Convertir en int16 si nécessaire et en bytes pour VAD
        if audio.dtype != np.int16:
            audio_int16 = (audio * 32767).astype(np.int16)
        else:
            audio_int16 = audio
        
        audio_bytes = audio_int16.tobytes()
        
        if len(audio_bytes) != FRAME_SIZE * 2:
            return

        # Détection de parole avec VAD
        is_speech = vad.is_speech(audio_bytes, SAMPLE_RATE)
        
        # Enregistrer TOUS les frames (même si VAD ne détecte pas)
        all_frames.append(audio_int16.copy())

        if is_speech:
            frames.append(audio_int16.copy())
            silence_frames = 0
            print(".", end="", flush=True)  # Feedback visuel
        else:
            silence_frames += 1

        # Calculer le temps d'enregistrement actuel
        current_recording_time = len(all_frames) * FRAME_DURATION_MS / 1000.0
        
        # Arrêter seulement si :
        # - On a eu de la parole ET
        # - On a au moins min_recording_time secondes ET
        # - Ensuite du silence suffisant
        if (len(frames) >= min_speech_frames and 
            current_recording_time >= min_recording_time and 
            silence_frames > max_silence):
            stream_stopped = True
            raise sd.CallbackStop

    # Fermer tout stream existant avant de commencer
    try:
        sd.stop()
        time.sleep(0.2)  # Petit délai pour libérer les ressources
    except:
        pass

    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SIZE,
            callback=callback
        )
        with stream:
            stream.start()
            # Attendre jusqu'à 30 secondes ou arrêt du callback
            start_time = time.time()
            while not stream_stopped and (time.time() - start_time) < 30:
                time.sleep(0.1)
                # Si on a assez de frames mais pas encore assez de temps, continuer
                if len(all_frames) > 0 and (time.time() - start_time) < 0.5:
                    continue  # Ne pas arrêter trop tôt
            if not stream_stopped:
                stream_stopped = True
    except sd.CallbackStop:
        pass  # Arrêt normal après silence
    except Exception as e:
        print(f"⚠️ Erreur lors de l'enregistrement: {e}")
    finally:
        # S'assurer que le stream est bien fermé
        try:
            sd.stop()
            time.sleep(0.1)  # Délai pour libérer les ressources
        except:
            pass
    
    print()  # Nouvelle ligne après les points

    # Vérifier qu'on a capturé du son
    if not all_frames:
        print("⚠️ Aucun son capturé")
        return False

    # Utiliser tous les frames si on a eu de la parole, sinon utiliser tout l'audio
    if frames and len(frames) >= min_speech_frames:
        audio = np.concatenate(frames, axis=0)
    else:
        audio = np.concatenate(all_frames, axis=0)
        print("⚠️ Parole peu détectée par VAD, utilisation de tout l'audio...")

    # Vérifier qu'on a assez d'audio (au moins 0.8 secondes)
    if len(audio) < SAMPLE_RATE * 0.8:
        print("⚠️ Enregistrement trop court")
        return False

    write(filename, SAMPLE_RATE, audio)
    print(f"✅ Réponse enregistrée ({len(audio)/SAMPLE_RATE:.1f}s)")
    return True

# =========================
# RÉCUPÉRATION DES DONNÉES DES AGENTS PRÉCÉDENTS
# =========================

def get_talent_card_from_minio(candidate_id: int) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Récupère la Talent Card (A1) depuis MinIO.
    
    Returns:
        Tuple (success, talent_card_data, error_message)
    """
    try:
        from minio_storage import get_minio_storage
        
        # Chercher le fichier talentcard
        minio_storage = get_minio_storage()
        if not minio_storage or not minio_storage.client:
            return False, None, "Client MinIO non initialisé"
        
        # Lister les fichiers pour trouver le talentcard
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
            print(f"✅ Talent Card récupérée pour candidat {candidate_id}")
            return True, talent_card_data, None
            
        except Exception as e:
            return False, None, f"Erreur lors de la recherche de la Talent Card: {str(e)}"
            
    except Exception as e:
        return False, None, f"Erreur lors de la récupération de la Talent Card: {str(e)}"


def get_corrected_cv_from_minio(candidate_id: int) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Récupère le CV corrigé (B1) depuis MinIO.
    Cherche d'abord corrected_cv/corrected_data.json, puis candidates/{id}/corrected_data_*.json (format réel du backend).
    
    Returns:
        Tuple (success, corrected_cv_data, error_message)
    """
    try:
        from minio_storage import get_minio_storage
        
        minio_storage = get_minio_storage()
        if not minio_storage or not minio_storage.client:
            return False, None, "Client MinIO non initialisé"
        
        from candidate_minio_path import get_candidate_minio_prefix
        minio_pre = get_candidate_minio_prefix(candidate_id)
        # 1. Essayer le chemin legacy attendu par B3
        object_name_legacy = f"{minio_pre}corrected_cv/corrected_data.json"
        success, file_bytes, error = minio_storage.download_file(object_name_legacy)
        if success and file_bytes:
            corrected_cv_data = json.loads(file_bytes.decode('utf-8'))
            print(f"✅ CV corrigé récupéré pour candidat {candidate_id} (corrected_cv/)")
            return True, corrected_cv_data, None
        
        # 2. Fallback: le backend upload sous candidates/{cat}/{id}/corrected_data_{uuid}_v{version}.json
        try:
            objects = list(minio_storage.client.list_objects(
                minio_storage.bucket_name,
                prefix=minio_pre + "corrected_data_",
                recursive=True
            ))
            json_objects = [obj for obj in objects if obj.object_name.endswith('.json')]
            if not json_objects:
                print(f"⚠️ CV corrigé non trouvé pour candidat {candidate_id}")
                return False, None, None
            # Prendre le plus récent (dernier dans la liste, ou trier par last_modified si dispo)
            latest = sorted(json_objects, key=lambda o: getattr(o, 'last_modified', None) or 0, reverse=True)[0]
            success, file_bytes, error = minio_storage.download_file(latest.object_name)
            if not success or not file_bytes:
                return False, None, None
            corrected_cv_data = json.loads(file_bytes.decode('utf-8'))
            print(f"✅ CV corrigé récupéré pour candidat {candidate_id} (corrected_data_*)")
            return True, corrected_cv_data, None
        except Exception as e_list:
            print(f"⚠️ Liste CV corrigé MinIO: {e_list}")
        
        print(f"⚠️ CV corrigé non trouvé pour candidat {candidate_id}")
        return False, None, None
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération du CV corrigé: {e}")
        return False, None, None


def get_chat_responses_from_minio(candidate_id: int) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Récupère les réponses du chatbot (B2) depuis MinIO.
    
    Returns:
        Tuple (success, chat_data, error_message)
    """
    try:
        from B2.chat.save_responses import get_chat_responses_from_minio as get_chat
        return get_chat(candidate_id)
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération des réponses du chatbot: {e}")
        return False, None, None


def get_portfolio_from_minio(candidate_id: int, candidate_uuid: str = None) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Récupère le portfolio (B2) depuis MinIO.
    
    Returns:
        Tuple (success, portfolio_data, error_message)
    """
    try:
        from minio_storage import get_minio_storage
        
        from candidate_minio_path import get_candidate_minio_prefix
        minio_pre = get_candidate_minio_prefix(candidate_id)
        # Chercher le portfolio JSON
        if candidate_uuid:
            object_name = f"{minio_pre}portfolio_{candidate_uuid}.json"
        else:
            object_name = f"{minio_pre}portfolio_*.json"
        
        minio_storage = get_minio_storage()
        if not minio_storage or not minio_storage.client:
            return False, None, "Client MinIO non initialisé"
        
        # Si on a un UUID, télécharger directement
        if candidate_uuid:
            object_name = f"{minio_pre}portfolio_{candidate_uuid}.json"
            success, file_bytes, error = minio_storage.download_file(object_name)
            if not success:
                print(f"⚠️ Portfolio non trouvé pour candidat {candidate_id}")
                return False, None, None
        else:
            # Lister les fichiers pour trouver le portfolio
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
                    print(f"⚠️ Portfolio non trouvé pour candidat {candidate_id}")
                    return False, None, None
                
                success, file_bytes, error = minio_storage.download_file(portfolio_object)
                if not success:
                    return False, None, error or "Erreur téléchargement Portfolio"
            except Exception as e:
                return False, None, f"Erreur lors de la recherche du Portfolio: {str(e)}"
        
        portfolio_data = json.loads(file_bytes.decode('utf-8'))
        print(f"✅ Portfolio récupéré pour candidat {candidate_id}")
        return True, portfolio_data, None
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération du Portfolio: {e}")
        return False, None, None


def get_candidate_data_from_db(candidate_id: int) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Récupère les données de base du candidat depuis la base de données.
    
    Returns:
        Tuple (success, candidate_data, error_message)
    """
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
        
        print(f"✅ Données candidat récupérées depuis la base de données")
        return True, dict(row), None
        
    except Exception as e:
        return False, None, f"Erreur lors de la récupération des données candidat: {str(e)}"


def retrieve_all_agent_data(candidate_id: int, candidate_uuid: Optional[str] = None) -> Dict:
    """
    Récupère toutes les données des agents précédents pour un candidat (en parallèle).
    
    Args:
        candidate_id: ID du candidat en base de données
        candidate_uuid: UUID du candidat (optionnel, pour le portfolio)
    
    Returns:
        Dictionnaire contenant toutes les données récupérées
    """
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
    
    print(f"✅ Récupération terminée:")
    print(f"   - Talent Card: {'✅' if all_data['talent_card'] else '❌'}")
    print(f"   - CV corrigé: {'✅' if all_data['corrected_cv'] else '⚠️'}")
    print(f"   - Réponses chatbot: {'✅' if all_data['chat_responses'] else '⚠️'}")
    print(f"   - Portfolio: {'✅' if all_data['portfolio'] else '⚠️'}")
    print(f"   - Données DB: {'✅' if all_data['candidate_db'] else '❌'}")
    
    return all_data


def build_interview_prompt_from_data(agent_data: Dict) -> str:
    """
    Construit le prompt d'entretien personnalisé à partir des données des agents précédents.
    
    Args:
        agent_data: Dictionnaire contenant toutes les données récupérées
    
    Returns:
        Prompt d'entretien personnalisé
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

Tu mènes un entretien oral pour un poste de {job_title}. Tu as lu son CV, sa Talent Card, son portfolio et ses réponses sur ses projets. Tu connais bien son profil.

DÉROULEMENT DE L'ENTRETIEN (comme tout recruteur) :
- PREMIÈRE QUESTION OBLIGATOIRE : demande au candidat de se PRÉSENTER, comme le font tous les recruteurs. Ex. : "Pour commencer, pouvez-vous vous présenter brièvement ? Parlez-moi de votre parcours et de ce qui vous amène vers ce poste." ou "Commençons par une présentation : qui êtes-vous, votre parcours en quelques mots ?" Le candidat n'a pas encore répondu : ne dis JAMAIS "merci pour votre réponse" à la première question.
- À partir de la 2e question : réagis brièvement à ce qu'il vient de dire (reprise, intérêt, lien) puis pose ta question. Montre que tu as ÉCOUTÉ sa réponse.
- Parle comme un recruteur : naturel, professionnel mais chaleureux. Pas de formules robotiques.
- Comprends bien le profil : adapte ton vocabulaire et tes sujets au métier (IA, design, dev, édition, etc.) et aux expériences/projets du candidat. Fais référence à des éléments concrets de son parcours quand c'est pertinent.

THÈMES À COUVRIR (répartis sur les 10 questions – NE PAS rester sur un seul projet) :
1. Présentation du candidat (parcours, motivation) – première question.
2. Expériences professionnelles : pose des questions sur PLUSIEURS expériences ou postes, pas seulement une. Ex. : "Sur votre expérience chez X, comment… ?" puis plus tard "Et dans votre rôle chez Y, vous avez… ?"
3. Projets : si le candidat a plusieurs projets (CV, portfolio, chatbot), pose des questions sur PLUSIEURS projets au fil de l'entretien, pas uniquement sur un seul. Alterne ou rebondis sur différents projets/expériences.
4. Logiciels et outils en lien avec le poste : demande quels logiciels, frameworks, outils métier il a déjà utilisés (ex. : "Quels outils ou logiciels utilisez-vous au quotidien dans votre métier ?", "Avez-vous déjà travaillé avec [outils typiques du poste] ?", "Comment vous organisez-vous avec [stack technique] ?").
Adapte ces thèmes au poste visé ({job_title}) et au profil du candidat.

Règles techniques :
- Pose UNE seule question à la fois (éventuellement précédée d'une courte réaction à sa dernière réponse).
- Total : 10 questions. Niveau progressif, varié (présentation, expériences, projets, outils).
- Langue : français. Ton professionnel mais bienveillant. N'utilise pas d'astérisques (*) ni de formatage markdown dans tes questions (elles sont lues à voix haute par un TTS).

Validation des réponses :
- Si la réponse est trop courte (moins de 10 mots), vague ou test, demande poliment de développer.
- Ne passe pas à une nouvelle question si la réponse n'est pas pertinente ; demande une précision.
"""
    
    # Construire le contexte du candidat
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
**INSTRUCTIONS POUR L'ENTRETIEN:**
- PREMIER MESSAGE (le candidat n'a pas encore parlé) : demande au candidat de se PRÉSENTER (comme tout recruteur). Ex. : "Pour commencer, pouvez-vous vous présenter brièvement ? Parlez-moi de votre parcours et de ce qui vous amène vers ce poste." Ne dis pas "merci pour votre réponse" au premier message.
- À partir du 2e message : réagis brièvement à sa réponse puis pose ta question. Varie les sujets : présentation, puis expériences (plusieurs), projets (plusieurs), logiciels/outils métier. NE PAS enchaîner toutes les questions sur un seul projet.
- Utilise le contexte ci-dessus : prénom, poste visé, expériences, projets, compétences. Fais référence à plusieurs expériences ou projets au fil de l'entretien.
- Pose des questions qui s'enchaînent naturellement : creuse un point qu'il a évoqué, ou rebondis sur une autre expérience/projet. Demande aussi quels logiciels ou outils il utilise en lien avec le poste.
- Adapte le niveau et les thèmes au métier (design, dev, IA, édition, etc.) et aux années d'expérience.
"""
    
    return full_prompt


# =========================
# PROMPT ENTRETIEN (par défaut, sans données)
# =========================
INTERVIEW_PROMPT_DEFAULT = """
Tu es un VRAI recruteur : tu mènes une CONVERSATION avec le candidat, pas un questionnaire.
- PREMIÈRE QUESTION : demande au candidat de se PRÉSENTER (comme tout recruteur). Ex. : "Pour commencer, pouvez-vous vous présenter brièvement ? Parlez-moi de votre parcours."
- À partir du 2e tour : réagis brièvement à ce qu'il vient de dire, puis pose ta question. Varie les sujets : expériences (plusieurs), projets (plusieurs), logiciels/outils en lien avec le poste. Ne reste pas sur un seul projet.
- Poste et métier sont dans le contexte (IA, Designer, Dev, Éditeur, etc.) : adapte tes questions en conséquence. Demande aussi quels outils/logiciels il utilise.
- Total : 10 questions. Une seule question par tour (éventuellement précédée d'une courte réaction). Ton naturel, professionnel, pas robotique.
"""

def ask_gemini(user_text, conversation_history):
    """
    Pose une question à Gemini avec l'historique de conversation.
    
    Args:
        user_text: Texte de l'utilisateur
        conversation_history: Historique de la conversation
    
    Returns:
        Tuple (réponse, nouvel historique)
    """
    # Vérifier si la réponse semble être un test ou non pertinente
    user_text_lower = user_text.lower().strip()
    test_keywords = ["test", "testing", "test test", "essai", "micro", "microphone", "check"]
    is_test = any(keyword in user_text_lower for keyword in test_keywords) and len(user_text_lower.split()) <= 3
    
    if is_test or len(user_text.strip()) < 10:
        # Si c'est un test, demander poliment de répéter
        prompt_addition = "\n\nIMPORTANT: La réponse du candidat semble être un test ou trop courte. Demande-lui poliment de répéter sa réponse de manière plus complète et détaillée. Sois bref et professionnel."
    else:
        prompt_addition = ""
    
    new_history = conversation_history + f"\nCandidat: {user_text}{prompt_addition}"
    response = gemini_model.generate_content(new_history)
    response_text = (response.text or "").strip()
    updated_history = new_history + f"\nRecruteur: {response_text}"
    return response_text, updated_history

# =========================
# MAIN LOOP
# =========================

def interview_voice(candidate_id: Optional[int] = None, candidate_uuid: Optional[str] = None, use_agent_data: bool = True):
    """
    Lance l'entretien vocal avec récupération optionnelle des données des agents précédents.
    
    Args:
        candidate_id: ID du candidat en base de données (optionnel)
        candidate_uuid: UUID du candidat (optionnel, pour le portfolio)
        use_agent_data: Si True, récupère et utilise les données des agents précédents
    """
    print("\n🎯 Entretien oral IA – Ingénieur IA\n")
    
    # Récupérer les données des agents précédents si demandé
    agent_data = None
    conversation_history = None
    
    if use_agent_data and candidate_id:
        agent_data = retrieve_all_agent_data(candidate_id, candidate_uuid)
        interview_prompt = build_interview_prompt_from_data(agent_data)
        conversation_history = interview_prompt
        
        # Message d'introduction personnalisé
        candidate_db = agent_data.get("candidate_db", {})
        prenom = candidate_db.get("prenom", "")
        nom = candidate_db.get("nom", "")
        titre = candidate_db.get("titre_profil", "")
        
        # Récupérer le poste visé depuis le portfolio
        portfolio = agent_data.get("portfolio")
        job_title = "Ingénieur IA"  # Par défaut
        if portfolio:
            portfolio_sections = portfolio.get("portfolio_sections", [])
            for section in portfolio_sections:
                if section.get("section_key") == "hero":
                    content = section.get("content", {})
                    job_title = content.get("job_title") or content.get("title") or job_title
                    break
        
        if prenom:
            intro = f"Bonjour {prenom}. Nous allons commencer l'entretien pour le poste de {job_title}."
        else:
            intro = f"Bonjour. Nous allons commencer l'entretien pour le poste de {job_title}."
        
        speak(intro)
    else:
        conversation_history = INTERVIEW_PROMPT_DEFAULT
        speak("Bonjour. Nous allons commencer l'entretien pour le poste d'ingénieur en intelligence artificielle.")
    
    # Première question
    question, conversation_history = ask_gemini("", conversation_history)
    print("🤖", question)
    speak(question)
    time.sleep(0.5)  # Délai après la première question
    
    # Boucle principale : 5 questions
    for i in range(5):
        # Délai après la question pour laisser le temps de commencer à parler
        time.sleep(0.5)
        success = record_audio_vad()
        if not success:
            speak("Je n'ai pas bien entendu. Pouvez-vous répéter ?")
            continue
        
        answer = speech_to_text()
        print("👤 Réponse :", answer)
        
        if not answer or len(answer.strip()) < 3:
            speak("Je n'ai pas bien compris votre réponse. Pouvez-vous répéter ?")
            continue
        
        question, conversation_history = ask_gemini(answer, conversation_history)
        print("🤖", question)
        speak(question)
    
    speak("Merci pour vos réponses. L'entretien est maintenant terminé.")
    print("\n✅ Entretien terminé")
    
    # Déclencher le prochain agent via n8n après la fin de l'entretien
    if candidate_id and candidate_uuid:
        trigger_n8n_after_interview(candidate_id, candidate_uuid, agent_data)


def interview_voice_simple():
    """
    Version simple de l'entretien sans récupération de données (compatibilité).
    """
    return interview_voice(candidate_id=None, use_agent_data=False)


# =========================
# FONCTION UTILITAIRE POUR INTÉGRATION
# =========================

def trigger_n8n_after_interview(candidate_id: int, candidate_uuid: str, agent_data: Optional[Dict] = None):
    """
    Déclenche le workflow n8n après la fin de l'entretien pour passer au prochain agent.
    
    Args:
        candidate_id: ID du candidat en base de données
        candidate_uuid: UUID du candidat
        agent_data: Données des agents précédents (optionnel)
    """
    n8n_webhook_agent4_next_url = os.getenv("N8N_WEBHOOK_agent4", None)
    
    if not n8n_webhook_agent4_next_url:
        print(f"ℹ️ N8N_WEBHOOK_AGENT4_NEXT non défini - le prochain agent ne sera pas déclenché automatiquement")
        return
    
    def trigger_n8n():
        """Fonction pour déclencher n8n en arrière-plan"""
        import traceback
        try:
            print(f"🔄 [n8n Agent4 Next Thread] Début de l'appel n8n pour candidate_uuid={candidate_uuid}")
            
            # Préparer le payload pour n8n
            n8n_payload = {
                "db_candidate_id": candidate_id,
                "candidate_uuid": candidate_uuid,
                "interview_completed": True,
                "timestamp": time.time()
            }
            
            # Ajouter les données des agents précédents si disponibles
            if agent_data:
                n8n_payload["agent_data"] = {
                    "candidate_db": agent_data.get("candidate_db", {}),
                    "talent_card": agent_data.get("talent_card") is not None,
                    "corrected_cv": agent_data.get("corrected_cv") is not None,
                    "chat_responses": agent_data.get("chat_responses") is not None,
                    "portfolio": agent_data.get("portfolio") is not None
                }
            
            print(f"🔄 [n8n Agent4 Next Thread] Envoi de la requête à {n8n_webhook_agent4_next_url}")
            n8n_response = requests.post(
                n8n_webhook_agent4_next_url,
                json=n8n_payload,
                timeout=300  # 5 minutes timeout
            )
            
            if n8n_response.status_code == 200:
                print(f"✅ [n8n Agent4 Next Thread] Webhook n8n déclenché avec succès pour candidate_uuid={candidate_uuid}")
                try:
                    n8n_result = n8n_response.json()
                    print(f"✅ [n8n Agent4 Next Thread] Réponse n8n: {n8n_result}")
                except:
                    print(f"ℹ️ [n8n Agent4 Next Thread] Réponse n8n vide (200 OK mais body vide)")
            else:
                print(f"⚠️ [n8n Agent4 Next Thread] n8n erreur HTTP {n8n_response.status_code}: {n8n_response.text[:200]}")
        except requests.exceptions.Timeout as e:
            print(f"⚠️ [n8n Agent4 Next Thread] Timeout lors de l'appel n8n (timeout > 5min): {e}")
        except requests.exceptions.ConnectionError as e:
            print(f"⚠️ [n8n Agent4 Next Thread] Erreur de connexion n8n (n8n non accessible?): {e}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ [n8n Agent4 Next Thread] Erreur lors de l'appel n8n: {e}")
            traceback.print_exc()
        except Exception as e:
            print(f"⚠️ [n8n Agent4 Next Thread] Erreur lors de l'orchestration n8n: {e}")
            traceback.print_exc()
    
    # Lancer en thread séparé (non-bloquant)
    thread = threading.Thread(target=trigger_n8n, daemon=True)
    thread.start()
    print(f"🔄 Appel n8n déclenché en arrière-plan après l'entretien pour candidate_uuid={candidate_uuid}")


def start_interview_with_candidate(candidate_id: int, candidate_uuid: Optional[str] = None) -> bool:
    """
    Fonction utilitaire pour démarrer un entretien avec un candidat spécifique.
    Cette fonction peut être appelée depuis d'autres modules (ex: app.py).
    
    Args:
        candidate_id: ID du candidat en base de données
        candidate_uuid: UUID du candidat (optionnel)
    
    Returns:
        True si l'entretien s'est terminé avec succès, False sinon
    """
    try:
        interview_voice(
            candidate_id=candidate_id,
            candidate_uuid=candidate_uuid,
            use_agent_data=True
        )
        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'entretien: {e}")
        import traceback
        traceback.print_exc()
        return False


# Point d'entrée principal
if __name__ == "__main__":
    import sys
    
    # Vérifier les arguments de ligne de commande
    candidate_id = None
    candidate_uuid = None
    
    if len(sys.argv) > 1:
        try:
            candidate_id = int(sys.argv[1])
            print(f"📋 Candidat ID: {candidate_id}")
        except ValueError:
            print("⚠️ ID candidat invalide, utilisation du mode simple")
    
    if len(sys.argv) > 2:
        candidate_uuid = sys.argv[2]
        print(f"📋 Candidat UUID: {candidate_uuid}")
    
    # Lancer l'entretien
    interview_voice(candidate_id=candidate_id, candidate_uuid=candidate_uuid, use_agent_data=(candidate_id is not None))
