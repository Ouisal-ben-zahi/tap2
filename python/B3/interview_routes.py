# ======================================================
# Routes API pour l'entretien oral IA
# ======================================================

import os
import uuid
import json
import time
import threading
import subprocess
from flask import Blueprint, request, jsonify, send_file, Response, stream_with_context
from typing import Dict, Optional, Tuple, Any
from B3.interview import (
    retrieve_all_agent_data,
    build_interview_prompt_from_data,
    ask_gemini
)
from B3.interview_ecrit import (
    retrieve_all_agent_data as retrieve_all_agent_data_written,
    build_written_interview_prompt_from_data,
    ask_gemini_written
)
from B3.evaluate_candidate import (
    evaluate_candidate_interview,
    save_evaluation_to_minio,
)
from TTS.api import TTS
import whisper
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*google.generativeai.*")
import google.generativeai as genai
from minio_storage import get_minio_storage

interview_bp = Blueprint('interview', __name__, url_prefix='/interview')

# =========================
# CONFIGURATION
# =========================
AUDIO_SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "audio_sessions")
os.makedirs(AUDIO_SESSIONS_DIR, exist_ok=True)

# Modèles IA (modèle Gemini depuis .env : GOOGLE_MODEL)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
GEMINI_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
gemini_model = genai.GenerativeModel(GEMINI_MODEL)
# "small" = plus rapide sur CPU, "medium" = plus précis mais lent (configurable via .env)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
whisper_model = whisper.load_model(WHISPER_MODEL)

# TTS
tts = TTS(
    model_name="tts_models/fr/css10/vits",
    progress_bar=False,
    gpu=False
)

if hasattr(tts, 'speakers') and tts.speakers:
    clean_speakers = [s.strip() for s in tts.speakers if s.strip()]
    TTS_SPEAKER = clean_speakers[0] if clean_speakers else None
else:
    TTS_SPEAKER = None

# =========================
# SESSIONS D'ENTRETIEN EN MÉMOIRE
# En production avec plusieurs workers Gunicorn, utiliser GUNICORN_WORKERS=1
# ou sticky sessions pour que le front reçoive toujours les mises à jour (question générée).
# =========================
interview_sessions: Dict[str, Dict] = {}
session_audio_responses: Dict[str, list] = {}
written_interview_sessions: Dict[str, Dict] = {}
session_written_responses: Dict[str, list] = {}

# Cache agent_data (db_candidate_id, candidate_uuid) -> (data, timestamp), TTL 5 min
_agent_data_cache: Dict[Tuple[int, str], Tuple[Dict, float]] = {}
AGENT_DATA_CACHE_TTL = 300  # secondes


def sanitize_text_for_tts(text: str) -> str:
    """
    Nettoie le texte pour le TTS : retire *, ** et autres caractères
    non supportés par le vocabulaire (évite "[!] Character '*' not found" et blocages).
    """
    if not text or not isinstance(text, str):
        return text
    t = text.replace("*", "").strip()
    while "  " in t:
        t = t.replace("  ", " ")
    return t or text


def remove_bonjour_prefix(text: str) -> str:
    """
    Supprime un « Bonjour » redondant au début des questions générées.
    Utilisé pour éviter que chaque question écrite commence par une salutation.
    """
    if not text:
        return text

    original = text
    stripped = text.lstrip()
    lower = stripped.lower()

    prefixes = [
        "bonjour ",
        "bonjour,",
        "bonjour.",
        "bonjour!",
        "bonjour !",
    ]

    for prefix in prefixes:
        if lower.startswith(prefix):
            # Retirer le préfixe et nettoyer les espaces / ponctuation juste après
            stripped = stripped[len(prefix):].lstrip(" ,.-\n")
            break

    # Conserver la mise en forme d'origine autant que possible
    return stripped if stripped else original


def _get_agent_data_cached(db_candidate_id: int, candidate_uuid: str, retrieve_fn):
    """Retourne agent_data depuis le cache ou appelle retrieve_fn et met en cache."""
    cache_key = (db_candidate_id, candidate_uuid)
    now = time.time()
    if cache_key in _agent_data_cache:
        data, ts = _agent_data_cache[cache_key]
        if now - ts < AGENT_DATA_CACHE_TTL:
            print(f"✅ Agent data depuis le cache pour candidat {db_candidate_id}")
            return data
        del _agent_data_cache[cache_key]
    data = retrieve_fn(db_candidate_id, candidate_uuid)
    _agent_data_cache[cache_key] = (data, now)
    return data


def cleanup_old_sessions():
    """Nettoie les sessions anciennes (> 1 heure) et le cache agent_data expiré"""
    current_time = time.time()
    sessions_to_remove = []
    for session_id, session_data in interview_sessions.items():
        if current_time - session_data.get("created_at", 0) > 3600:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del interview_sessions[session_id]
        if session_id in session_audio_responses:
            del session_audio_responses[session_id]
    
    # Nettoyer le cache agent_data expiré
    expired = [k for k, (_, ts) in _agent_data_cache.items() if current_time - ts >= AGENT_DATA_CACHE_TTL]
    for k in expired:
        del _agent_data_cache[k]

# =========================
# ROUTES API
# =========================

@interview_bp.route("/<candidate_uuid>/start", methods=["POST"])
def start_interview(candidate_uuid):
    """
    Démarre une session d'entretien pour un candidat.
    
    Body (JSON):
        db_candidate_id: int (obligatoire)
    """
    try:
        data = request.get_json() or {}
        db_candidate_id = data.get("db_candidate_id")
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id is required"}), 400
        
        # Générer un session_id unique
        session_id = f"interview-{uuid.uuid4()}"
        
        # Créer le dossier de session
        session_dir = os.path.join(AUDIO_SESSIONS_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Initialiser la session
        interview_sessions[session_id] = {
            "session_id": session_id,
            "candidate_uuid": candidate_uuid,
            "db_candidate_id": db_candidate_id,
            "created_at": time.time(),
            "status": "starting",
            "current_question": 0,
            "total_questions": 5,
            "conversation_history": None,
            "agent_data": None
        }
        session_audio_responses[session_id] = []
        
        # Lancer l'entretien en arrière-plan
        def run_interview():
            try:
                print(f"🎤 [Interview Thread] Démarrage de l'entretien pour candidate_uuid={candidate_uuid}, db_candidate_id={db_candidate_id}")
                
                # Récupérer les données des agents précédents (cache ou fetch parallèle)
                agent_data = _get_agent_data_cached(db_candidate_id, candidate_uuid, retrieve_all_agent_data)
                interview_sessions[session_id]["agent_data"] = agent_data
                
                # Construire le prompt personnalisé
                interview_prompt = build_interview_prompt_from_data(agent_data)
                conversation_history = interview_prompt
                interview_sessions[session_id]["conversation_history"] = conversation_history
                
                # Message d'introduction personnalisé
                candidate_db = agent_data.get("candidate_db", {})
                prenom = candidate_db.get("prenom", "")
                titre = candidate_db.get("titre_profil", "")

                # Récupérer le poste visé (même logique que dans build_interview_prompt_from_data)
                job_title = "Ingénieur IA"  # Par défaut

                # 1) Portfolio (section hero)
                portfolio = agent_data.get("portfolio")
                if portfolio:
                    portfolio_sections = portfolio.get("portfolio_sections", [])
                    for section in portfolio_sections:
                        if section.get("section_key") == "hero":
                            content = section.get("content", {})
                            job_title = content.get("job_title") or content.get("title") or job_title
                            break

                # 2) CV corrigé
                if job_title == "Ingénieur IA":
                    corrected_cv = agent_data.get("corrected_cv")
                    if corrected_cv:
                        job_title = corrected_cv.get("Titre", job_title)

                # 3) Talent Card
                if job_title == "Ingénieur IA":
                    talent_card = agent_data.get("talent_card")
                    if talent_card:
                        job_title = talent_card.get("Titre de profil", job_title)
                
                if prenom:
                    intro = f"Bonjour {prenom}. Nous allons commencer l'entretien pour le poste de {job_title}."
                else:
                    intro = f"Bonjour. Nous allons commencer l'entretien pour le poste de {job_title}."
                
                # Générer l'audio de l'introduction
                intro_audio_file = os.path.join(session_dir, f"intro_{int(time.time())}.wav")
                intro_tts = sanitize_text_for_tts(intro)
                if TTS_SPEAKER:
                    tts.tts_to_file(text=intro_tts, file_path=intro_audio_file, speaker=TTS_SPEAKER, language="fr-fr")
                else:
                    tts.tts_to_file(text=intro_tts, file_path=intro_audio_file)
                
                interview_sessions[session_id]["status"] = "intro_ready"
                interview_sessions[session_id]["intro_text"] = intro
                interview_sessions[session_id]["intro_audio"] = os.path.basename(intro_audio_file)
                
                # Première question
                question, conversation_history = ask_gemini("", conversation_history)
                question = remove_bonjour_prefix(question)
                interview_sessions[session_id]["conversation_history"] = conversation_history
                interview_sessions[session_id]["current_question"] = 1
                interview_sessions[session_id]["status"] = "question_ready"
                
                # Générer l'audio de la question
                question_id = uuid.uuid4().hex[:8]
                question_audio_file = os.path.join(session_dir, f"question_{question_id}.wav")
                question_tts = sanitize_text_for_tts(question)
                if TTS_SPEAKER:
                    tts.tts_to_file(text=question_tts, file_path=question_audio_file, speaker=TTS_SPEAKER, language="fr-fr")
                else:
                    tts.tts_to_file(text=question_tts, file_path=question_audio_file)
                
                interview_sessions[session_id]["current_question_text"] = question
                interview_sessions[session_id]["current_question_audio"] = os.path.basename(question_audio_file)
                
                print(f"✅ Entretien démarré en arrière-plan pour session_id={session_id}")
                
            except Exception as e:
                print(f"❌ Erreur lors du démarrage de l'entretien: {e}")
                import traceback
                traceback.print_exc()
                interview_sessions[session_id]["status"] = "error"
                interview_sessions[session_id]["error"] = str(e)
        
        thread = threading.Thread(target=run_interview, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Entretien démarré en arrière-plan"
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur démarrage entretien: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _session_status_snapshot(session: Dict, session_id: str) -> Dict[str, Any]:
    """Snapshot léger du statut pour comparaison / SSE."""
    return {
        "session_id": session_id,
        "status": session.get("status", "unknown"),
        "current_question": session.get("current_question", 0),
        "total_questions": session.get("total_questions", 10),
        "current_question_text": session.get("current_question_text", ""),
        "intro_text": session.get("intro_text", ""),
        "error": session.get("error"),
    }


@interview_bp.route("/<session_id>/events", methods=["GET"])
def interview_events(session_id):
    """Server-Sent Events : pousse les mises à jour de statut (évite le polling)."""
    if session_id not in interview_sessions:
        return jsonify({"error": "Session introuvable"}), 404

    def generate():
        last_sent = None
        deadline = time.time() + 3600  # 1 h max
        while time.time() < deadline:
            session = interview_sessions.get(session_id)
            if not session:
                break
            snap = _session_status_snapshot(session, session_id)
            if last_sent != snap:
                last_sent = snap
                yield f"data: {json.dumps(snap)}\n\n"
            st = session.get("status", "")
            if st in ("completed", "error"):
                break
            time.sleep(0.35)
        yield "data: {}\n\n"

    resp = Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
    return resp


@interview_bp.route("/<session_id>/status", methods=["GET"])
def get_interview_status(session_id):
    """Récupère le statut de la session d'entretien"""
    if session_id not in interview_sessions:
        return jsonify({"error": "Session introuvable"}), 404
    
    session = interview_sessions[session_id]
    snap = _session_status_snapshot(session, session_id)
    resp = jsonify(snap)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp, 200


@interview_bp.route("/<session_id>/audio", methods=["GET"])
def get_interview_audio(session_id):
    """Récupère la liste des fichiers audio disponibles pour la session"""
    if session_id not in interview_sessions:
        return jsonify({"error": "Session introuvable"}), 404
    
    session = interview_sessions[session_id]
    session_dir = os.path.join(AUDIO_SESSIONS_DIR, session_id)
    
    audio_files = []
    
    # Intro
    if session.get("intro_audio"):
        audio_files.append({
            "type": "intro",
            "filename": session["intro_audio"],
            "text": session.get("intro_text", "")
        })
    
    # Questions
    if session.get("current_question_audio"):
        audio_files.append({
            "type": "question",
            "filename": session["current_question_audio"],
            "text": session.get("current_question_text", ""),
            "question_number": session.get("current_question", 0)
        })
    
    # Réponses
    if session_id in session_audio_responses:
        for idx, response in enumerate(session_audio_responses[session_id]):
            audio_files.append({
                "type": "response",
                "filename": response.get("audio_file", ""),
                "text": response.get("transcription", ""),
                "question_number": response.get("question_number", 0)
            })
    
    return jsonify({
        "session_id": session_id,
        "audio_files": audio_files
    }), 200


@interview_bp.route("/<session_id>/audio/<filename>", methods=["GET"])
def get_audio_file(session_id, filename):
    """Sert un fichier audio de la session"""
    if session_id not in interview_sessions:
        return jsonify({"error": "Session introuvable"}), 404
    
    session_dir = os.path.join(AUDIO_SESSIONS_DIR, session_id)
    audio_path = os.path.join(session_dir, filename)
    
    if not os.path.exists(audio_path):
        return jsonify({"error": "Fichier audio introuvable"}), 404
    
    return send_file(audio_path, mimetype="audio/wav")


@interview_bp.route("/<session_id>/evaluation", methods=["GET"])
def get_interview_evaluation(session_id):
    """
    Calcule et retourne l'évaluation de l'entretien oral pour une session terminée.
    """
    if session_id not in interview_sessions:
        return jsonify({"error": "Session introuvable"}), 404

    session = interview_sessions[session_id]

    if session.get("status") != "completed":
        return jsonify({"error": "L'entretien n'est pas encore terminé"}), 400

    conversation_history = session.get("conversation_history", "")
    if not conversation_history:
        return jsonify({"error": "Historique de conversation indisponible"}), 500

    agent_data = session.get("agent_data") or {}
    candidate_data = agent_data.get("candidate_db")

    success, evaluation_data, error = evaluate_candidate_interview(
        conversation_history=conversation_history,
        candidate_data=candidate_data,
    )

    if not success or not evaluation_data:
        return jsonify({"error": error or "Erreur lors de l'évaluation de l'entretien"}), 500

    db_candidate_id = session.get("db_candidate_id")
    candidate_uuid = session.get("candidate_uuid")
    if db_candidate_id and candidate_uuid:
        try:
            save_evaluation_to_minio(db_candidate_id, candidate_uuid, evaluation_data)
        except Exception:
            import traceback
            print("⚠️ Erreur lors de la sauvegarde de l'évaluation dans MinIO")
            traceback.print_exc()

    return jsonify({
        "success": True,
        "evaluation": evaluation_data
    }), 200


@interview_bp.route("/<session_id>/record", methods=["POST"])
def record_response(session_id):
    """
    Enregistre une réponse audio du candidat.
    
    Form data:
        audio: fichier audio (webm/wav)
    """
    try:
        if session_id not in interview_sessions:
            return jsonify({"error": "Session introuvable"}), 404
        
        print(f"📥 [RECORD] Requête POST reçue pour session {session_id}")
        print(f"📥 [RECORD] Headers: {dict(request.headers)}")
        print(f"📥 [RECORD] Files: {list(request.files.keys())}")
        print(f"📥 [RECORD] Form data: {list(request.form.keys())}")
        
        if 'audio' not in request.files:
            return jsonify({"error": "Aucun fichier audio fourni"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Fichier audio vide"}), 400
        
        session_dir = os.path.join(AUDIO_SESSIONS_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Extension depuis le fichier envoyé (webm, ogg, mp4 selon navigateur)
        raw_name = audio_file.filename or "response.webm"
        ext = (raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else "webm")
        if ext not in ("webm", "ogg", "mp4", "wav"):
            ext = "webm"
        
        response_id = uuid.uuid4().hex[:8]
        audio_filename = f"response_{response_id}.{ext}"
        audio_path = os.path.join(session_dir, audio_filename)
        audio_file.save(audio_path)
        
        file_size = os.path.getsize(audio_path)
        print(f"📥 Audio reçu et sauvegardé: {audio_filename} ({file_size} bytes) pour session {session_id}")
        if file_size < 3000:
            print(f"⚠️ Fichier très petit ({file_size} bytes) — enregistrement peut être trop court ou micro non capté. Demander 2–3 s de parole minimum.")
        
        # Transcriptions en arrière-plan
        def transcribe_audio():
            try:
                # Mettre le statut à "processing" pendant la transcription
                if session_id in interview_sessions:
                    interview_sessions[session_id]["status"] = "processing"
                
                print(f"🔄 Début transcription audio pour session {session_id}...")
                print(f"🎤 Transcription en cours pour {audio_path} (session: {session_id})...")
                
                # Vérifier que le fichier existe et n'est pas vide
                if not os.path.exists(audio_path):
                    raise FileNotFoundError(f"Fichier audio introuvable: {audio_path}")
                
                file_size = os.path.getsize(audio_path)
                print(f"📊 Taille du fichier audio: {file_size} bytes")
                
                if file_size == 0:
                    raise ValueError("Le fichier audio est vide")

                # Convertir WebM/Opus/MP4 en WAV 16kHz mono pour Whisper (obligatoire sur VPS pour éviter transcription vide)
                wav_path = os.path.join(session_dir, f"response_{response_id}_converted.wav")
                need_convert = audio_path.lower().endswith((".webm", ".ogg", ".mp4", ".m4a"))
                if need_convert:
                    ffmpeg_bin = "/usr/bin/ffmpeg" if os.path.exists("/usr/bin/ffmpeg") else "ffmpeg"
                    try:
                        out = subprocess.run(
                            [ffmpeg_bin, "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", wav_path],
                            capture_output=True, timeout=30, check=False
                        )
                        if out.returncode != 0:
                            stderr = (out.stderr or b"").decode(errors="replace")
                            print(f"⚠️ ffmpeg stderr: {stderr[:500]}")
                            raise ValueError(f"Conversion ffmpeg échouée (code {out.returncode})")
                        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
                            raise ValueError("Conversion ffmpeg a produit un fichier vide")
                        print(f"✅ Audio converti en WAV: {wav_path} ({os.path.getsize(wav_path)} bytes)")
                    except FileNotFoundError:
                        raise FileNotFoundError("ffmpeg non trouvé. Installez ffmpeg dans le conteneur.")
                else:
                    wav_path = audio_path

                # Transcrire avec Whisper (fp16=False sur CPU VPS pour éviter sortie vide)
                result = whisper_model.transcribe(
                    wav_path,
                    language="fr",
                    fp16=False,
                    task="transcribe",
                )
                transcription = (result.get("text") or "").strip()
                # Sur certains environnements (ex. CPU), result["text"] peut être vide alors que segments contient le texte
                if not transcription and result.get("segments"):
                    transcription = " ".join(
                        (s.get("text") or "").strip() for s in result["segments"]
                    ).strip()
                # Si toujours vide, réessayer sans forcer la langue (détection auto)
                if not transcription:
                    print(f"⚠️ Transcription vide avec language='fr', réessai en détection auto...")
                    result = whisper_model.transcribe(wav_path, fp16=False, task="transcribe")
                    transcription = (result.get("text") or "").strip()
                    if not transcription and result.get("segments"):
                        transcription = " ".join(
                            (s.get("text") or "").strip() for s in result["segments"]
                        ).strip()
                if not transcription:
                    print(f"📋 Whisper result keys: {list(result.keys())}, segments: {len(result.get('segments', []))}")

                print(f"✅ Audio traité et transcrit pour session {session_id}: '{transcription}'")
                print(f"📊 Longueur de la transcription: {len(transcription)} caractères")
                # Estimation très grossière de la durée audio (PCM 16kHz mono 16 bits = 32000 bytes/s)
                try:
                    wav_size = os.path.getsize(wav_path)
                    approx_duration_sec = wav_size / 32000.0
                except Exception:
                    approx_duration_sec = 0.0
                print(f"⏱️ Durée audio estimée: ~{approx_duration_sec:.1f} s")
                
                # Ajouter à la liste des réponses
                if session_id not in session_audio_responses:
                    session_audio_responses[session_id] = []
                
                session = interview_sessions[session_id]
                question_number = session.get("current_question", 0)
                
                session_audio_responses[session_id].append({
                    "audio_file": audio_filename,
                    "transcription": transcription,
                    "question_number": question_number,
                    "timestamp": time.time()
                })
                
                print(f"✅ Transcription ajoutée à session_audio_responses[{session_id}]:")
                print(f"   - Transcription: '{transcription}'")
                print(f"   - Nombre de réponses en attente: {len(session_audio_responses[session_id])}")
                
                # Validation de la qualité de la réponse
                def is_valid_response(text):
                    """Vérifie si la réponse est valide et pertinente"""
                    if not text or len(text.strip()) < 10:
                        return False, "Réponse trop courte"
                    
                    # Détecter les mots de test courants
                    test_keywords = ["test", "testing", "test test", "essai", "micro", "microphone", "check", "vérification"]
                    text_lower = text.lower().strip()
                    for keyword in test_keywords:
                        if keyword in text_lower and len(text_lower.split()) <= 3:
                            return False, "Réponse de test détectée"
                    
                    # Vérifier qu'il y a au moins quelques mots significatifs
                    words = text.split()
                    if len(words) < 3:
                        return False, "Pas assez de mots pour une réponse valide"
                    
                    return True, None
                
                # Vérifier la validité de la réponse
                is_valid, validation_error = is_valid_response(transcription)
                # Cas spécial: sur certains navigateurs/OS (Windows), Whisper renvoie parfois une transcription
                # très courte ("you", 1-2 mots) alors que le candidat a parlé longtemps.
                # Si l'audio est manifestement long mais la transcription reste minuscule, on considère la réponse
                # comme VALIDE pour ne pas bloquer l'entretien, et on envoie un texte générique au modèle IA.
                transcription_for_llm = transcription
                long_audio_but_short_text = bool(transcription) and not is_valid and approx_duration_sec >= 8.0
                if long_audio_but_short_text:
                    print("⚠️ Transcription courte mais audio long -> on continue l'entretien avec un résumé générique pour le LLM.")
                    is_valid = True
                    validation_error = None
                    transcription_for_llm = (
                        "Le candidat a fourni une réponse orale détaillée et relativement longue à la question "
                        "précédente (plusieurs secondes de parole), mais la transcription automatique est très "
                        "incomplète ou peu fiable (problème de reconnaissance vocale / accent / qualité audio). "
                        "Considérez que le candidat a réellement répondu de manière complète et professionnelle."
                    )
                
                # Générer la prochaine question si on a une transcription valide
                if transcription and is_valid:
                    try:
                        conversation_history = session.get("conversation_history", "")
                        if conversation_history:
                            next_question, updated_history = ask_gemini(transcription_for_llm, conversation_history)
                            interview_sessions[session_id]["conversation_history"] = updated_history
                            interview_sessions[session_id]["current_question"] = question_number + 1
                            interview_sessions[session_id]["current_question_text"] = next_question
                            interview_sessions[session_id]["current_question_audio"] = None
                            interview_sessions[session_id]["status"] = "question_ready"
                            print(f"🤖 Question {question_number + 1} ({len(next_question)} car.): {next_question}")
                            # Terminer seulement après que le candidat a répondu à la 10e question (pas dès qu'on génère la 10e)
                            if question_number + 1 > session.get("total_questions", 10):
                                interview_sessions[session_id]["status"] = "completed"
                                print(f"✅ Entretien terminé pour session {session_id}")
                            else:
                                def generate_tts_background():
                                    try:
                                        qid = uuid.uuid4().hex[:8]
                                        q_audio = os.path.join(session_dir, f"question_{qid}.wav")
                                        text_tts = sanitize_text_for_tts(next_question)
                                        if TTS_SPEAKER:
                                            tts.tts_to_file(text=text_tts, file_path=q_audio, speaker=TTS_SPEAKER, language="fr-fr")
                                        else:
                                            tts.tts_to_file(text=text_tts, file_path=q_audio)
                                        if session_id in interview_sessions and interview_sessions[session_id].get("status") == "question_ready":
                                            interview_sessions[session_id]["current_question_audio"] = os.path.basename(q_audio)
                                            print(f"🔊 TTS prêt pour question {question_number + 1}")
                                    except Exception as e_tts:
                                        print(f"⚠️ Erreur TTS en arrière-plan: {e_tts}")
                                threading.Thread(target=generate_tts_background, daemon=True).start()
                    except Exception as e:
                        print(f"⚠️ Erreur lors de la génération de la question suivante: {e}")
                        import traceback
                        traceback.print_exc()
                        # Remettre le statut à question_ready pour permettre de réessayer
                        interview_sessions[session_id]["status"] = "question_ready"
                        interview_sessions[session_id]["error"] = f"Erreur génération question: {str(e)}"
                else:
                    # Transcription invalide ou non pertinente
                    error_msg = validation_error if validation_error else f"Réponse trop courte (longueur: {len(transcription)})"
                    print(f"⚠️ Réponse invalide: {error_msg}. Transcription: '{transcription}'")
                    
                    # Générer une question de répétition au lieu d'avancer
                    try:
                        conversation_history = session.get("conversation_history", "")
                        if conversation_history:
                            repeat_prompt = f"L'intervieweur a dit: '{transcription}'. Cette réponse semble être un test ou trop courte. Demande poliment au candidat de répéter sa réponse de manière plus complète et détaillée. Sois bref et professionnel."
                            repeat_question, _ = ask_gemini(repeat_prompt, conversation_history)
                            interview_sessions[session_id]["current_question_text"] = repeat_question
                            interview_sessions[session_id]["current_question_audio"] = None
                            interview_sessions[session_id]["status"] = "question_ready"
                            interview_sessions[session_id]["error"] = None
                            print(f"🔄 Question de répétition générée: {repeat_question}")
                            print(f"✅ [REPEAT] Session {session_id} → status=question_ready, texte envoyé au front (len={len(repeat_question)})")
                            # TTS en arrière-plan
                            def generate_repeat_tts():
                                try:
                                    question_id = uuid.uuid4().hex[:8]
                                    question_audio_file = os.path.join(session_dir, f"question_{question_id}.wav")
                                    text_tts = sanitize_text_for_tts(repeat_question)
                                    if TTS_SPEAKER:
                                        tts.tts_to_file(text=text_tts, file_path=question_audio_file, speaker=TTS_SPEAKER, language="fr-fr")
                                    else:
                                        tts.tts_to_file(text=text_tts, file_path=question_audio_file)
                                    if session_id in interview_sessions:
                                        interview_sessions[session_id]["current_question_audio"] = os.path.basename(question_audio_file)
                                except Exception as e_tts:
                                    print(f"⚠️ Erreur TTS répétition: {e_tts}")
                            threading.Thread(target=generate_repeat_tts, daemon=True).start()
                    except Exception as e:
                        print(f"⚠️ Erreur lors de la génération de la question de répétition: {e}")
                        interview_sessions[session_id]["status"] = "question_ready"
                        interview_sessions[session_id]["error"] = f"Veuillez répéter votre réponse de manière plus claire et complète. ({error_msg})"
                
            except Exception as e:
                print(f"❌ Erreur lors de la transcription: {e}")
                import traceback
                traceback.print_exc()
                # Remettre le statut à question_ready pour permettre de réessayer
                if session_id in interview_sessions:
                    interview_sessions[session_id]["status"] = "question_ready"
                    interview_sessions[session_id]["error"] = f"Erreur transcription: {str(e)}"
        
        # Lancer la transcription en arrière-plan
        thread = threading.Thread(target=transcribe_audio, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "Audio reçu et en cours de traitement",
            "response_id": response_id
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur lors de l'enregistrement: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =========================
# ROUTES API POUR ENTRETIEN ÉCRIT
# =========================

@interview_bp.route("/written/<candidate_uuid>/start", methods=["POST"])
def start_written_interview(candidate_uuid):
    """
    Démarre une session d'entretien écrit pour un candidat.
    
    Body (JSON):
        db_candidate_id: int (obligatoire)
    """
    try:
        data = request.get_json() or {}
        db_candidate_id = data.get("db_candidate_id")
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id is required"}), 400
        
        # Générer un session_id unique
        session_id = f"written-interview-{uuid.uuid4()}"
        
        # Initialiser la session
        written_interview_sessions[session_id] = {
            "session_id": session_id,
            "candidate_uuid": candidate_uuid,
            "db_candidate_id": db_candidate_id,
            "created_at": time.time(),
            "status": "starting",
            "current_question": 0,
            "total_questions": 5,
            "conversation_history": None,
            "agent_data": None
        }
        session_written_responses[session_id] = []
        
        # Lancer l'entretien en arrière-plan
        def run_written_interview():
            try:
                print(f"✍️ [Written Interview Thread] Démarrage de l'entretien écrit pour candidate_uuid={candidate_uuid}, db_candidate_id={db_candidate_id}")
                
                # Récupérer les données des agents précédents (cache ou fetch parallèle)
                agent_data = _get_agent_data_cached(db_candidate_id, candidate_uuid, retrieve_all_agent_data_written)
                written_interview_sessions[session_id]["agent_data"] = agent_data
                
                # Construire le prompt personnalisé
                interview_prompt = build_written_interview_prompt_from_data(agent_data)
                conversation_history = interview_prompt
                written_interview_sessions[session_id]["conversation_history"] = conversation_history
                
                # Message d'introduction personnalisé
                candidate_db = agent_data.get("candidate_db", {})
                prenom = candidate_db.get("prenom", "")
                
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
                    intro = f"Bonjour {prenom}. Nous allons commencer l'entretien écrit pour le poste de {job_title}."
                else:
                    intro = f"Bonjour. Nous allons commencer l'entretien écrit pour le poste de {job_title}."
                
                written_interview_sessions[session_id]["status"] = "intro_ready"
                written_interview_sessions[session_id]["intro_text"] = intro
                
                # Première question
                question, conversation_history = ask_gemini_written("", conversation_history)
                question = remove_bonjour_prefix(question)
                written_interview_sessions[session_id]["conversation_history"] = conversation_history
                written_interview_sessions[session_id]["current_question"] = 1
                written_interview_sessions[session_id]["status"] = "question_ready"
                written_interview_sessions[session_id]["current_question_text"] = question
                
                print(f"✅ Entretien écrit démarré en arrière-plan pour session_id={session_id}")
                
            except Exception as e:
                print(f"❌ Erreur lors du démarrage de l'entretien écrit: {e}")
                import traceback
                traceback.print_exc()
                written_interview_sessions[session_id]["status"] = "error"
                written_interview_sessions[session_id]["error"] = str(e)
        
        thread = threading.Thread(target=run_written_interview, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Entretien écrit démarré en arrière-plan"
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur démarrage entretien écrit: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@interview_bp.route("/written/<session_id>/status", methods=["GET"])
def get_written_interview_status(session_id):
    """Récupère le statut de la session d'entretien écrit"""
    if session_id not in written_interview_sessions:
        return jsonify({"error": "Session introuvable"}), 404
    
    session = written_interview_sessions[session_id]
    
    return jsonify({
        "session_id": session_id,
        "status": session.get("status", "unknown"),
        "current_question": session.get("current_question", 0),
        "total_questions": session.get("total_questions", 10),
        "current_question_text": session.get("current_question_text", ""),
        "intro_text": session.get("intro_text", ""),
        "error": session.get("error")
    }), 200


@interview_bp.route("/written/<session_id>/response", methods=["POST"])
def submit_written_response(session_id):
    """
    Soumet une réponse écrite du candidat.
    
    Body (JSON):
        answer: str (obligatoire) - La réponse écrite du candidat
    """
    try:
        if session_id not in written_interview_sessions:
            return jsonify({"error": "Session introuvable"}), 404
        
        data = request.get_json() or {}
        answer = data.get("answer", "").strip()
        
        if not answer:
            return jsonify({"error": "La réponse ne peut pas être vide"}), 400
        
        session = written_interview_sessions[session_id]
        question_number = session.get("current_question", 0)
        
        # Ajouter la réponse à l'historique
        if session_id not in session_written_responses:
            session_written_responses[session_id] = []
        
        session_written_responses[session_id].append({
            "answer": answer,
            "question_number": question_number,
            "timestamp": time.time()
        })
        
        # Validation de la qualité de la réponse
        def is_valid_response(text):
            """Vérifie si la réponse est valide et pertinente"""
            if not text or len(text.strip()) < 20:
                return False, "Réponse trop courte (minimum 20 mots)"
            
            # Détecter les mots de test courants
            test_keywords = ["test", "testing", "test test", "essai", "check"]
            text_lower = text.lower().strip()
            words = text_lower.split()
            if len(words) <= 3:
                for keyword in test_keywords:
                    if keyword in text_lower:
                        return False, "Réponse de test détectée"
            
            # Vérifier qu'il y a au moins quelques mots significatifs
            if len(words) < 5:
                return False, "Pas assez de mots pour une réponse valide"
            
            return True, None
        
        # Vérifier la validité de la réponse
        is_valid, validation_error = is_valid_response(answer)
        
        # Générer la prochaine question si on a une réponse valide
        if is_valid:
            try:
                conversation_history = session.get("conversation_history", "")
                if conversation_history:
                    next_question, updated_history = ask_gemini_written(answer, conversation_history)
                    next_question = remove_bonjour_prefix(next_question)
                    written_interview_sessions[session_id]["conversation_history"] = updated_history
                    written_interview_sessions[session_id]["current_question"] = question_number + 1
                    written_interview_sessions[session_id]["current_question_text"] = next_question
                    written_interview_sessions[session_id]["status"] = "question_ready"
                    
                    print(f"🤖 Question {question_number + 1} ({len(next_question)} car.): {next_question}")
                    
                    # Terminer seulement après que le candidat a répondu à la 10e question
                    if question_number + 1 > session.get("total_questions", 10):
                        written_interview_sessions[session_id]["status"] = "completed"
                        print(f"✅ Entretien écrit terminé pour session {session_id}")
                    
                    return jsonify({
                        "success": True,
                        "message": "Réponse enregistrée",
                        "next_question": next_question,
                        "current_question": question_number + 1,
                        "is_completed": question_number + 1 > session.get("total_questions", 10)
                    }), 200
            except Exception as e:
                print(f"⚠️ Erreur lors de la génération de la question suivante: {e}")
                import traceback
                traceback.print_exc()
                written_interview_sessions[session_id]["status"] = "question_ready"
                written_interview_sessions[session_id]["error"] = f"Erreur génération question: {str(e)}"
                return jsonify({"error": f"Erreur génération question: {str(e)}"}), 500
        else:
            # Réponse invalide
            error_msg = validation_error if validation_error else f"Réponse trop courte (longueur: {len(answer)})"
            print(f"⚠️ Réponse invalide: {error_msg}. Réponse: '{answer[:100]}...'")
            
            # Générer une question de clarification au lieu d'avancer
            try:
                conversation_history = session.get("conversation_history", "")
                if conversation_history:
                    # Demander de développer avec un message contextuel
                    clarification_prompt = f"L'intervieweur a écrit: '{answer}'. Cette réponse semble être un test ou trop courte. Demande poliment au candidat de développer sa réponse de manière plus complète et détaillée. Sois bref et professionnel."
                    
                    clarification_question, _ = ask_gemini_written(clarification_prompt, conversation_history)
                    clarification_question = remove_bonjour_prefix(clarification_question)
                    
                    # Ne pas incrémenter le numéro de question, on reste sur la même
                    written_interview_sessions[session_id]["current_question_text"] = clarification_question
                    written_interview_sessions[session_id]["status"] = "question_ready"
                    written_interview_sessions[session_id]["error"] = None
                    
                    print(f"🔄 Question de clarification générée: {clarification_question}")
                    
                    return jsonify({
                        "success": False,
                        "message": "Réponse trop courte ou non pertinente",
                        "error": error_msg,
                        "clarification_question": clarification_question,
                        "current_question": question_number
                    }), 200
            except Exception as e:
                print(f"⚠️ Erreur lors de la génération de la question de clarification: {e}")
                written_interview_sessions[session_id]["status"] = "question_ready"
                written_interview_sessions[session_id]["error"] = f"Veuillez développer votre réponse de manière plus claire et complète. ({error_msg})"
                return jsonify({
                    "success": False,
                    "error": f"Veuillez développer votre réponse de manière plus claire et complète. ({error_msg})"
                }), 200
        
    except Exception as e:
        print(f"❌ Erreur lors de la soumission de la réponse: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@interview_bp.route("/written/<session_id>/responses", methods=["GET"])
def get_written_responses(session_id):
    """Récupère toutes les réponses écrites de la session"""
    if session_id not in written_interview_sessions:
        return jsonify({"error": "Session introuvable"}), 404
    
    responses = session_written_responses.get(session_id, [])
    
    return jsonify({
        "session_id": session_id,
        "responses": responses
    }), 200


@interview_bp.route("/written/<session_id>/evaluation", methods=["GET"])
def get_written_interview_evaluation(session_id):
    """
    Calcule et retourne l'évaluation de l'entretien écrit pour une session terminée.
    """
    if session_id not in written_interview_sessions:
        return jsonify({"error": "Session introuvable"}), 404

    session = written_interview_sessions[session_id]

    if session.get("status") != "completed":
        return jsonify({"error": "L'entretien n'est pas encore terminé"}), 400

    conversation_history = session.get("conversation_history", "")
    if not conversation_history:
        return jsonify({"error": "Historique de conversation indisponible"}), 500

    agent_data = session.get("agent_data") or {}
    candidate_data = agent_data.get("candidate_db")

    success, evaluation_data, error = evaluate_candidate_interview(
        conversation_history=conversation_history,
        candidate_data=candidate_data,
    )

    if not success or not evaluation_data:
        return jsonify({"error": error or "Erreur lors de l'évaluation de l'entretien"}), 500

    # Tentative de sauvegarde dans MinIO (best-effort, n'affecte pas la réponse HTTP)
    db_candidate_id = session.get("db_candidate_id")
    candidate_uuid = session.get("candidate_uuid")
    if db_candidate_id and candidate_uuid:
        try:
            save_evaluation_to_minio(db_candidate_id, candidate_uuid, evaluation_data)
        except Exception:
            import traceback
            print("⚠️ Erreur lors de la sauvegarde de l'évaluation dans MinIO")
            traceback.print_exc()

    return jsonify({
        "success": True,
        "evaluation": evaluation_data
    }), 200
