from flask import Flask, request, jsonify, send_file, redirect
from flask_cors import CORS
import glob
import json
import os
import re
import requests
import threading
import uuid
from io import BytesIO
from zipfile import ZipFile
from datetime import datetime
from jinja2 import Template
from A1.generate_talent import generate_talent_card
from A1.insert_data import insert_talent_card, generate_unique_id_agent, create_candidate_record
from A1.talent_html import generate_and_save_talent_card_html
from A1.ocr import ocr_pdf_bytes, ocr_image_bytes, extract_text_from_pdf_bytes, extract_text_from_image_bytes
from B1.generate_corrected_cv import (
    generate_corrected_cv as generate_corrected_cv_agent2,
    transform_corrected_json_to_cv_context,
    render_cv_html,
)
from minio_storage import get_minio_storage
from candidate_minio_path import get_candidate_minio_prefix, normalize_categorie_profil
from B3.interview_routes import interview_bp, cleanup_old_sessions
from B3.avatar_routes import avatar_api_bp
from auth import auth_bp, oauth_bp, get_optional_user_from_request
from A2.agent_scoring_v2 import AgentScoringV2
from A2.module_A2_Bis.A2_bis_dynamic_agent import A2BisDynamicAgent


app = Flask(__name__)
# Autoriser l'en-tête Authorization pour les requêtes cross-origin (login puis GET /auth/me/files)


CORS(
    app,
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Cache-Control",
        "Pragma",
    ],
    supports_credentials=True,
)


# Enregistrer le blueprint de l'entretien
app.register_blueprint(interview_bp)
# API Avatar (TTS playbook) - mêmes routes que le backend FastAPI avatar
app.register_blueprint(avatar_api_bp)
# Authentification (inscription / connexion)
app.register_blueprint(auth_bp)
# OAuth social (Google / GitHub / LinkedIn)
app.register_blueprint(oauth_bp)

UPLOAD_FOLDER = "uploads"
GENERATED_FOLDER = "generated"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

CORRECTED_FOLDER = os.path.join(GENERATED_FOLDER, "corrected_cv")
os.makedirs(CORRECTED_FOLDER, exist_ok=True)

CORRECTED_PDF_FOLDER = os.path.join(GENERATED_FOLDER, "corrected_cv_pdf")
os.makedirs(CORRECTED_PDF_FOLDER, exist_ok=True)

# Template CV : HTML A4 (Jinja2) — utilisé par défaut pour la génération du CV corrigé
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
DEFAULT_CORRECTED_HTML_TEMPLATE = os.path.join(_PROJECT_ROOT, "frontend", "src", "CV templates", "CV_template_A4.html")
# Chemins de fallback (Docker / volume)
CV_HTML_TEMPLATE_PATHS = [
    "/app/frontend/src/CV templates/CV_template_A4.html",
    "/frontend/src/CV templates/CV_template_A4.html",
    DEFAULT_CORRECTED_HTML_TEMPLATE,
]

# Timestamp de dernière génération du PDF portfolio par (db_candidate_id, version) — pour que la prévisualisation affiche le nouveau PDF après régénération
import time as _time
_portfolio_pdf_generated_at = {}


def _load_talentcard_from_db(db_candidate_id):
    """
    Reconstruit un talentcard_data depuis la base (candidates + skills + languages + contract_types + experiences + realisations).
    Utilisé pour générer le CV corrigé après validation, sans dépendre du JSON côté frontend.
    """
    from database.connection import DatabaseConnection

    DatabaseConnection.initialize()

    with DatabaseConnection.get_connection() as db:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM candidates WHERE id = %s", (db_candidate_id,))
        candidate = cursor.fetchone()
        if not candidate:
            cursor.close()
            return None

        cursor.execute(
            """
            SELECT 
                c.*,
                GROUP_CONCAT(DISTINCT s.skill_name) as skills,
                GROUP_CONCAT(DISTINCT l.language_name) as languages,
                GROUP_CONCAT(DISTINCT ct.type_name) as contract_types
            FROM candidates c
            LEFT JOIN skills s ON c.id = s.candidate_id
            LEFT JOIN languages l ON c.id = l.candidate_id
            LEFT JOIN contract_types ct ON c.id = ct.candidate_id
            WHERE c.id = %s
            GROUP BY c.id
            """,
            (db_candidate_id,),
        )
        candidate_full = cursor.fetchone() or {}

        cursor.execute("SELECT * FROM experiences WHERE candidate_id = %s", (db_candidate_id,))
        experiences = cursor.fetchall() or []

        cursor.execute("SELECT * FROM realisations WHERE candidate_id = %s", (db_candidate_id,))
        realisations = cursor.fetchall() or []

        cursor.close()

    talentcard_data = {
        "id_agent": candidate.get("id_agent"),
        "nom": candidate.get("nom", "") or "",
        "prenom": candidate.get("prenom", "") or "",
        "Titre de profil": candidate.get("titre_profil", "") or "",
        "ville": candidate.get("ville", "") or "",
        "pays": candidate.get("pays", "") or "",
        "linkedin": candidate.get("linkedin", "") or "",
        "email": candidate.get("email", "") or "",
        "phone": candidate.get("phone", "") or "",
        "annees_experience": candidate.get("annees_experience"),
        "disponibilite": candidate.get("disponibilite", "") or "",
        "pret_a_relocater": candidate.get("pret_a_relocater", "") or "",
        "niveau_seniorite": candidate.get("niveau_seniorite", "") or "",
        "pays_cible": candidate.get("pays_cible", "") or candidate.get("target_country", "") or "",
        "salaire_minimum": candidate.get("salaire_minimum", "") or "",
        "resume_bref": candidate.get("resume_bref", "") or "",
        "skills": candidate_full.get("skills", "").split(",") if candidate_full.get("skills") else [],
        "experience": [
            {
                "Role": exp.get("role", "") or "",
                "entreprise": exp.get("entreprise", "") or "",
                "periode": exp.get("periode", "") or "",
                "description": exp.get("description", "") or "",
            }
            for exp in experiences
        ],
        "realisations": [r.get("description", "") or "" for r in realisations],
        "langues_parlees": candidate_full.get("languages", "").split(",") if candidate_full.get("languages") else [],
        "type_contrat": candidate_full.get("contract_types", "").split(",") if candidate_full.get("contract_types") else [],
        "analyse": candidate.get("analyse", "") or "",
        "categorie_profil": (candidate.get("categorie_profil") or "").strip() or "autre",
    }

    return talentcard_data


def _convert_minio_url_to_proxy(minio_url: str | None, flask_base_url: str = "http://localhost:5002") -> str | None:
    """
    Convertit une URL MinIO en URL proxy Flask.
    
    Args:
        minio_url: URL MinIO (ex: http://localhost:9000/tap-files/candidates/123/profile.jpg)
        flask_base_url: URL de base du serveur Flask
    
    Returns:
        URL proxy (ex: http://localhost:5002/minio-proxy/candidates/123/profile.jpg)
    """
    if not minio_url:
        return None
    
    try:
        # Extraire le nom de l'objet depuis l'URL MinIO
        # Format attendu: http(s)://endpoint/bucket/object_path
        parts = minio_url.split('/', 4)  # Split: ['http:', '', 'localhost:9000', 'bucket', 'object_path']
        
        if len(parts) >= 5:
            object_path = parts[4]
            return f"{flask_base_url}/minio-proxy/{object_path}"
        return minio_url
    except Exception:
        return minio_url


def _convert_project_images_to_proxy(projects: list, flask_base_url: str = "http://localhost:5002") -> list:
    """
    Convertit toutes les URLs MinIO des images de projets en URLs proxy.
    
    Args:
        projects: Liste des projets avec leurs images
        flask_base_url: URL de base du serveur Flask
    
    Returns:
        Liste des projets avec URLs converties
    """
    if not projects or not isinstance(projects, list):
        return projects
    
    for project in projects:
        if not isinstance(project, dict):
            continue
        
        # Convertir main_image_url
        if project.get("main_image_url"):
            project["main_image_url"] = _convert_minio_url_to_proxy(
                project["main_image_url"],
                flask_base_url
            )
        
        # Convertir preview_images
        if project.get("preview_images") and isinstance(project["preview_images"], list):
            for img in project["preview_images"]:
                if isinstance(img, dict) and img.get("url"):
                    img["url"] = _convert_minio_url_to_proxy(img["url"], flask_base_url)
        
        # Convertir images (si présent)
        if project.get("images") and isinstance(project["images"], list):
            converted_images = []
            for img in project["images"]:
                if isinstance(img, str):
                    converted_images.append(_convert_minio_url_to_proxy(img, flask_base_url))
                elif isinstance(img, dict) and img.get("url"):
                    img["url"] = _convert_minio_url_to_proxy(img["url"], flask_base_url)
                    converted_images.append(img)
                else:
                    converted_images.append(img)
            project["images"] = converted_images
    
    return projects


def _minio_object_name_from_url(url: str, bucket_name: str) -> str | None:
    if not url:
        return None
    try:
        marker = f"/{bucket_name}/"
        if marker in url:
            return url.split(marker, 1)[1]
        # fallback (moins fiable): après le dernier /
        return url.split("/")[-1]
    except Exception:
        return None


def _get_candidate_info(db_candidate_id: int, fields: list[str]) -> dict:
    """
    Fonction utilitaire pour récupérer des informations sur un candidat depuis la base de données.
    
    Args:
        db_candidate_id: ID du candidat
        fields: Liste des champs à récupérer (ex: ['image_minio_url', 'email', 'phone'])
    
    Returns:
        dict avec les valeurs récupérées (clés = noms des champs)
    """
    from database.connection import DatabaseConnection
    
    try:
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            fields_str = ", ".join(fields)
            cursor.execute(
                f"SELECT {fields_str} FROM candidates WHERE id = %s",
                (db_candidate_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            return row or {}
    except Exception as e:
        print(f"⚠️  Erreur récupération infos candidat: {e}")
        return {}


def _get_candidate_contract_types(db_candidate_id: int) -> list[str]:
    """Retourne la liste des types de contrat du candidat (CDI, Freelance, etc.)."""
    from database.connection import DatabaseConnection
    try:
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor()
            cursor.execute(
                "SELECT type_name FROM contract_types WHERE candidate_id = %s AND type_name IS NOT NULL ORDER BY id",
                (db_candidate_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [r[0].strip() for r in rows if r and r[0]]
    except Exception as e:
        print(f"⚠️  Erreur récupération contract_types: {e}")
        return []


def _get_candidate_image_url(db_candidate_id: int) -> str | None:
    """
    Fonction utilitaire pour récupérer l'URL de l'image d'un candidat.
    
    Args:
        db_candidate_id: ID du candidat
    
    Returns:
        URL de l'image ou None
    """
    result = _get_candidate_info(db_candidate_id, ['image_minio_url'])
    return result.get('image_minio_url')


def _upload_to_minio_with_logging(minio_storage, file_bytes: bytes, object_name: str, content_type: str = None) -> tuple[bool, str | None, str | None]:
    """
    Upload un fichier vers MinIO avec logs automatiques.
    
    Args:
        minio_storage: Instance du client MinIO
        file_bytes: Contenu du fichier à uploader
        object_name: Nom de l'objet dans MinIO
        content_type: Type MIME du fichier (optionnel)
    
    Returns:
        tuple (success, url, error)
    """
    try:
        success, url, error = minio_storage.upload_file(
            file_bytes,
            object_name,
            content_type=content_type
        )
        if success:
            print(f"✅ Fichier uploadé vers MinIO: {object_name}")
            return True, url, None
        else:
            print(f"⚠️  Échec upload vers MinIO ({object_name}): {error}")
            return False, None, error
    except Exception as e:
        error_msg = str(e)
        print(f"⚠️  Erreur upload vers MinIO ({object_name}): {error_msg}")
        return False, None, error_msg


def _get_candidate_cv_text(db_candidate_id: int) -> tuple[str | None, str | None]:
    """
    Récupère et extrait le texte du CV d'un candidat depuis MinIO.
    
    Args:
        db_candidate_id: ID du candidat
    
    Returns:
        tuple (cv_text, cv_filename) ou (None, None) si erreur
    """
    from database.connection import DatabaseConnection
    
    try:
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT cv_minio_url FROM candidates WHERE id = %s", (db_candidate_id,))
            row = cursor.fetchone() or {}
            cursor.close()

        cv_url = row.get("cv_minio_url")
        minio_storage = get_minio_storage()

        object_name = None
        if not cv_url:
            print(f"⚠️  Aucun cv_minio_url en base pour candidate_id={db_candidate_id}")
            # Fallback: retrouver automatiquement un objet CV dans MinIO (self-heal)
            try:
                prefix = get_candidate_minio_prefix(int(db_candidate_id)) + "cv_"
                objs = list(minio_storage.client.list_objects(minio_storage.bucket_name, prefix=prefix, recursive=True))
                if objs:
                    def _lm_ts(o):
                        lm = getattr(o, "last_modified", None)
                        return lm.timestamp() if lm else 0
                    best = max(objs, key=_lm_ts)
                    object_name = getattr(best, "object_name", None)
                    if object_name:
                        cv_url = minio_storage.get_file_url(object_name)
                        print(f"✅ CV trouvé via fallback MinIO: {object_name}")
                        # Persister en base
                        try:
                            with DatabaseConnection.get_connection() as db:
                                cursor2 = db.cursor()
                                cursor2.execute(
                                    "UPDATE candidates SET cv_minio_url = %s WHERE id = %s",
                                    (cv_url, db_candidate_id),
                                )
                                db.commit()
                                cursor2.close()
                        except Exception as e:
                            print(f"⚠️  Impossible de persister cv_minio_url: {e}")
            except Exception as e:
                print(f"⚠️  Fallback MinIO (recherche CV) échoué: {e}")

        if cv_url:
            if not object_name:
                object_name = _minio_object_name_from_url(cv_url, minio_storage.bucket_name)
            if not object_name:
                print(f"⚠️  Impossible de déduire object_name depuis cv_minio_url: {cv_url}")
                return None, None
            
            print(f"✅ MinIO object_name CV: {object_name}")
            success, cv_bytes, error = minio_storage.download_file(object_name)
            if success and cv_bytes:
                filename = os.path.basename(object_name)
                cv_text = _extract_text_from_cv_bytes(cv_bytes, filename)
                preview = (cv_text[:240] + "...") if len(cv_text) > 240 else cv_text
                print(f"✅ CV texte extrait ({len(cv_text)} chars): {preview!r}")
                if cv_text and cv_text.strip():
                    return cv_text, filename
            else:
                print(f"⚠️  Impossible de télécharger le CV depuis MinIO: {error}")
    except Exception as e:
        print(f"⚠️  Erreur récupération/extraction CV: {e}")
    
    return None, None


def _convert_docx_to_pdf(docx_path: str, pdf_path: str) -> bool:
    """
    Convertit un fichier DOCX en PDF.
    
    Args:
        docx_path: Chemin vers le fichier DOCX source
        pdf_path: Chemin de destination pour le PDF
        
    Returns:
        bool: True si la conversion réussit, False sinon
    """
    if not os.path.exists(docx_path):
        print(f"⚠️  Fichier DOCX introuvable: {docx_path}")
        return False
    
    try:
        # ✅ Priorité: LibreOffice headless (solution la plus robuste côté serveur)
        import shutil
        import subprocess

        libreoffice_cmd = None
        mac_soffice = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if os.path.exists(mac_soffice):
            libreoffice_cmd = mac_soffice
        else:
            libreoffice_cmd = shutil.which("soffice") or shutil.which("libreoffice")

        if libreoffice_cmd:
            pdf_dir = os.path.dirname(pdf_path)
            os.makedirs(pdf_dir, exist_ok=True)

            cmd = [
                libreoffice_cmd,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--convert-to", "pdf",
                "--outdir", pdf_dir,
                docx_path,
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=90)
            if result.returncode == 0:
                base_name = os.path.splitext(os.path.basename(docx_path))[0]
                produced_pdf = os.path.join(pdf_dir, f"{base_name}.pdf")
                if os.path.exists(produced_pdf):
                    if produced_pdf != pdf_path:
                        os.replace(produced_pdf, pdf_path)
                    print(f"✅ Conversion DOCX -> PDF réussie via LibreOffice: {pdf_path}")
                    return True
            else:
                stderr = (result.stderr or b"").decode(errors="ignore")
                stdout = (result.stdout or b"").decode(errors="ignore")
                print(f"⚠️  LibreOffice conversion failed (rc={result.returncode}). stderr={stderr!r} stdout={stdout!r}")
        else:
            print("⚠️  LibreOffice non trouvé (soffice/libreoffice).")

        # Fallback: docx2pdf (utile sur certains environnements, mais moins fiable sur serveur/macOS sans Word)
        try:
            from docx2pdf import convert  # type: ignore
            convert(docx_path, pdf_path)
            if os.path.exists(pdf_path):
                print(f"✅ Conversion DOCX -> PDF réussie via docx2pdf (fallback): {pdf_path}")
                return True
        except Exception as e:
            print(f"⚠️  docx2pdf fallback échoué: {e}")

        print("❌ Impossible de convertir DOCX en PDF (LibreOffice/docx2pdf indisponibles ou en erreur).")
        return False

    except Exception as e:
        print(f"❌ Erreur lors de la conversion DOCX -> PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


# Format A4 pour le CV : 21 cm × 29,7 cm
CV_PDF_FORMAT_WIDTH_CM = 21
CV_PDF_FORMAT_HEIGHT_CM = 29.7


def _convert_cv_html_to_pdf(html_path: str, pdf_path: str) -> bool:
    """
    Convertit le CV HTML en PDF au format A4 (21 cm × 29,7 cm) via Playwright.
    """
    if not os.path.exists(html_path):
        print(f"⚠️  Fichier HTML CV introuvable: {html_path}")
        return False
    try:
        import http.server
        import socketserver
        import random
        import threading
        from playwright.sync_api import sync_playwright

        temp_dir = os.path.dirname(html_path)
        html_filename = os.path.basename(html_path)

        class _CVHTTPHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=temp_dir, **kwargs)
            def log_message(self, format, *args):
                pass

        class _Reusable(socketserver.TCPServer):
            allow_reuse_address = True

        httpd = None
        for _ in range(15):
            try:
                port = random.randint(8000, 9000)
                httpd = _Reusable(("", port), _CVHTTPHandler)
                break
            except OSError:
                continue
        if not httpd:
            print("❌ Aucun port disponible pour servir le HTML CV")
            return False
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                # Viewport et PDF en A4 : 21 cm × 29,7 cm
                inch_w = CV_PDF_FORMAT_WIDTH_CM / 2.54
                inch_h = CV_PDF_FORMAT_HEIGHT_CM / 2.54
                page.set_viewport_size({"width": int(round(inch_w * 96)), "height": int(round(inch_h * 96))})
                page.goto(f"http://localhost:{port}/{html_filename}", wait_until="networkidle", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=10000)
                page.wait_for_timeout(1500)
                os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)
                page.pdf(
                    path=pdf_path,
                    print_background=True,
                    format="A4",  # 21 cm × 29,7 cm
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                )
                browser.close()
            httpd.shutdown()
            server_thread.join(timeout=2)
            if os.path.exists(pdf_path):
                print(f"✅ Conversion CV HTML -> PDF réussie: {pdf_path}")
                return True
        finally:
            try:
                httpd.shutdown()
                server_thread.join(timeout=1)
            except Exception:
                pass
        return False
    except Exception as e:
        print(f"❌ Erreur conversion CV HTML -> PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def _extract_text_from_cv_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Extrait un texte du CV (PDF/DOCX/images) pour aider l'agent B1 à corriger.
    Retourne "" si extraction impossible.
    """
    if not file_bytes:
        return ""

    ext = os.path.splitext(filename or "")[1].lower()

    # PDF (extraction déterministe, puis fallback OCR si nécessaire)
    if ext == ".pdf":
        extracted_text = ""
        try:
            extracted_text, warnings = extract_text_from_pdf_bytes(file_bytes)
            if warnings:
                print(f"⚠️  Extraction PDF warnings: {warnings}")
        except Exception as e:
            print(f"⚠️  Extraction texte PDF échouée: {e}")

        # Si pas assez de texte, fallback OCR (peut nécessiter Poppler)
        # Utiliser la fonction heuristique pour détecter les PDFs qui nécessitent OCR
        from A1.ocr import should_fallback_to_ocr
        
        should_use_ocr = should_fallback_to_ocr(extracted_text or "", min_chars=200)
        
        if should_use_ocr:
            print(f"📸 Texte extrait insuffisant ou de mauvaise qualité ({len((extracted_text or '').strip())} chars), utilisation de l'OCR...")
            try:
                ocr_res = ocr_pdf_bytes(file_bytes, lang="fra+eng")
                if ocr_res.warnings:
                    print(f"⚠️  OCR PDF warnings: {ocr_res.warnings}")
                ocr_text = (ocr_res.text or "").strip()
                # Utiliser le texte OCR si il est meilleur que l'extraction normale
                if len(ocr_text) > len((extracted_text or "").strip()):
                    print(f"✅ OCR réussi: {len(ocr_text)} caractères extraits (vs {len((extracted_text or '').strip())} avec extraction normale)")
                    return ocr_text
                elif ocr_text:
                    print(f"✅ OCR a extrait {len(ocr_text)} caractères")
                    return ocr_text
            except Exception as e:
                print(f"⚠️  OCR PDF échoué (fallback): {e}")
                # Continuer avec le texte extrait même s'il est court

        return (extracted_text or "").strip()

    # DOCX
    if ext == ".docx":
        try:
            import tempfile
            import docx2txt  # type: ignore

            with tempfile.NamedTemporaryFile(suffix=".docx", delete=True) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                txt = docx2txt.process(tmp.name) or ""
                return str(txt).strip()
        except Exception as e:
            print(f"⚠️  Extraction texte DOCX échouée: {e}")
            return ""

    # Images (OCR)
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
        try:
            txt, warnings = extract_text_from_image_bytes(file_bytes)
            if warnings:
                print(f"⚠️  OCR image warnings: {warnings}")
            return (txt or "").strip()
        except Exception as e:
            print(f"⚠️  OCR image échoué: {e}")
            return ""

    # Autres formats: pas gérés pour l'instant
    return ""


def _generate_corrected_cv_from_talentcard(
    talentcard_data: dict,
    db_candidate_id: int,
    candidate_uuid: str,
    *,
    cv_text: str | None = None,
    feedback_comments: str | None = None,
    version_number: int = 1,
):
    """
    Enchaîne agent 1 -> agent 2:
    - candidate = talentcard (agent 1)
    - analysis = déterministe (petites règles) pour guider l'agent 2
    - feedback_comments = commentaires précédents pour améliorer la génération
    """
    # Enrichir le talentcard avec l'URL de la photo (pour affichage ville, pays, image sur le CV)
    img_url = _get_candidate_image_url(db_candidate_id)
    if img_url:
        talentcard_data = dict(talentcard_data)
        talentcard_data["profile_image_url"] = _convert_minio_url_to_proxy(img_url) or img_url
        talentcard_data["image_minio_url"] = img_url
    # On envoie à l'agent B1 l'output A1 EXACT (talentcard_data) via le paramètre `analysis`
    analysis = talentcard_data
    html_template_path = None
    for p in CV_HTML_TEMPLATE_PATHS:
        if os.path.exists(p):
            html_template_path = p
            break
    if not html_template_path:
        raise FileNotFoundError(f"Template CV HTML introuvable. Chemins essayés: {CV_HTML_TEMPLATE_PATHS}")
    out_html_path = os.path.join(CORRECTED_FOLDER, f"corrected_cv_{candidate_uuid}_v{version_number}.html")
    out_json_path = os.path.join(CORRECTED_FOLDER, f"corrected_data_{candidate_uuid}_v{version_number}.json")

    result_agent2 = generate_corrected_cv_agent2(
        candidate=talentcard_data,
        analysis=analysis,
        cv_text=cv_text,
        template_path=html_template_path,
        out_html_path=out_html_path,
        out_json_path=out_json_path,
        provider="gemini",
        model=None,
        feedback_comments=feedback_comments,
    )

    agent_explanation = result_agent2.get("agent_explanation", "")

    out_pdf_path = os.path.join(CORRECTED_PDF_FOLDER, f"corrected_cv_{candidate_uuid}_v{version_number}.pdf")
    pdf_converted = False
    if os.path.exists(out_html_path):
        pdf_converted = _convert_cv_html_to_pdf(out_html_path, out_pdf_path)
        if not pdf_converted:
            print(f"⚠️  Conversion CV HTML -> PDF échouée pour {out_html_path}")

    minio_storage = get_minio_storage()
    minio_prefix = get_candidate_minio_prefix(db_candidate_id)
    corrected_minio = {"corrected_cv_url": None, "corrected_cv_html_url": None, "corrected_json_url": None, "corrected_pdf_url": None}
    try:
        if os.path.exists(out_html_path):
            with open(out_html_path, "rb") as f:
                html_bytes = f.read()
            object_name = f"{minio_prefix}corrected_cv_{candidate_uuid}_v{version_number}.html"
            success, url, _ = _upload_to_minio_with_logging(
                minio_storage, html_bytes, object_name, content_type="text/html; charset=utf-8"
            )
            if success:
                corrected_minio["corrected_cv_html_url"] = url

        if os.path.exists(out_json_path):
            with open(out_json_path, "rb") as f:
                json_bytes = f.read()
            object_name = f"{minio_prefix}corrected_data_{candidate_uuid}_v{version_number}.json"
            success, url, _ = _upload_to_minio_with_logging(
                minio_storage, json_bytes, object_name, content_type="application/json"
            )
            if success:
                corrected_minio["corrected_json_url"] = url

        if pdf_converted and os.path.exists(out_pdf_path):
            with open(out_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            object_name = f"{minio_prefix}corrected_cv_{candidate_uuid}_v{version_number}.pdf"
            success, url, _ = _upload_to_minio_with_logging(
                minio_storage, pdf_bytes, object_name, content_type="application/pdf"
            )
            if success:
                corrected_minio["corrected_pdf_url"] = url
                corrected_minio["corrected_cv_url"] = url
                print(f"✅ PDF du CV corrigé uploadé vers MinIO: {url}")
    except Exception as e:
        print(f"⚠️  Erreur upload corrected outputs vers MinIO: {e}")

    # Enregistrer la version en base de données
    cv_version_id = None
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor()
            cursor.execute(
                """
                INSERT INTO corrected_cv_versions 
                (candidate_id, candidate_uuid, corrected_cv_minio_url, corrected_json_minio_url, 
                 corrected_pdf_minio_url, validation_status, feedback_comment, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    db_candidate_id,
                    candidate_uuid,
                    corrected_minio.get("corrected_cv_url"),
                    corrected_minio.get("corrected_json_url"),
                    corrected_minio.get("corrected_pdf_url"),
                    "pending",
                    feedback_comments,
                    version_number,
                ),
            )
            cv_version_id = cursor.lastrowid
            cursor.close()
    except Exception as e:
        print(f"⚠️  Erreur lors de l'enregistrement de la version CV en base: {e}")

    normalized_flat = result_agent2.get("normalized_flat") or result_agent2.get("corrected_json") or {}
    return {
        "html_path": out_html_path,
        "json_path": out_json_path,
        "pdf_path": out_pdf_path if pdf_converted else None,
        "pdf_available": pdf_converted,
        "minio_urls": corrected_minio,
        "analysis_used": analysis,
        "download_url": f"/correctedcv/{candidate_uuid}/download",
        "preview_url": f"/correctedcv/{candidate_uuid}/preview?version={version_number}" if pdf_converted else None,
        "version_number": version_number,
        "cv_version_id": cv_version_id,
        "agent_explanation": agent_explanation,
        "Realisations": normalized_flat.get("Realisations") or normalized_flat.get("realisations") or [],
        "Educations": normalized_flat.get("Educations") or normalized_flat.get("educations") or [],
        "corrected_json": normalized_flat,
    }




@app.route("/process", methods=["POST"])
def process_candidate():
    # Générer l'ID agent unique dans la base de données
    try:
        id_agent = generate_unique_id_agent()
        print(f"✅ ID agent généré: {id_agent}")
    except Exception as e:
        print(f"❌ Erreur lors de la génération de l'ID agent: {e}")
        return jsonify({"error": f"Erreur lors de la génération de l'ID agent: {e}"}), 500
    
    # Récupérer l'utilisateur connecté (optionnel) pour lier le candidat dès la création
    # Utilise get_optional_user_from_request pour supporter Authorization ET form auth_token (multipart)
    current_user_id, _ = get_optional_user_from_request()

    # Créer l'enregistrement minimal dans la base de données AVANT la génération de la talent card
    try:
        db_candidate_id = create_candidate_record(id_agent, user_id=current_user_id)
        print(f"✅ Enregistrement candidat créé avec ID DB: {db_candidate_id}" + (f" (user_id={current_user_id})" if current_user_id else ""))
    except Exception as e:
        print(f"❌ Erreur lors de la création de l'enregistrement candidat: {e}")
        return jsonify({"error": f"Erreur lors de la création de l'enregistrement candidat: {e}"}), 500
    
    candidate_uuid = str(uuid.uuid4())
    
    cv_file = request.files.get("cv_file")
    cv_content = b""

    if cv_file:
        # On lit le contenu AVANT de sauvegarder ou on fait un seek(0)
        cv_content = cv_file.read()
        
        filename = f"{candidate_uuid}_{cv_file.filename}"
        cv_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Pour sauvegarder après un .read(), il faut parfois réinitialiser le curseur
        cv_file.seek(0)
        cv_file.save(cv_path)

    # Récupérer l'image
    img_file = request.files.get("img_file")
    img_content = b""
    
    if img_file:
        img_content = img_file.read()
        img_file.seek(0)
        filename_img = f"{candidate_uuid}_{img_file.filename}"
        img_path = os.path.join(UPLOAD_FOLDER, filename_img)
        img_file.save(img_path)

    # Récupérer type_contrat (peut être plusieurs valeurs)
    type_contrat_list = request.form.getlist("type_contrat")
    
    # Récupérer other_links si présent (JSON string)
    other_links = []
    other_links_json = request.form.get("other_links")
    if other_links_json:
        try:
            other_links = json.loads(other_links_json)
            if not isinstance(other_links, list):
                other_links = []
        except json.JSONDecodeError:
            print(f"⚠️  Erreur parsing other_links JSON: {other_links_json}")
            other_links = []
    
    form_info = {
        "linkedin_url": request.form.get("linkedin_url"),
        "github_url": request.form.get("github_url"),
        "behance_url": request.form.get("behance_url"),
        "other_links": other_links,
        "target_position": request.form.get("target_position"),
        "target_country": request.form.get("target_country"),
        "pret_a_relocater": request.form.get("pret_a_relocater"),
        "constraints": request.form.get("constraints"),
        "search_criteria": request.form.get("search_criteria"),
        "nationality": request.form.get("nationality"),
        "location_country": request.form.get("location_country"),
        "seniority_level": request.form.get("seniority_level"),
        "disponibilite": request.form.get("disponibilite"),
        "salaire_minimum": request.form.get("salaire_minimum"),
        "domaine_activite": request.form.get("domaine_activite"),
        "type_contrat": type_contrat_list,
    }

    # 🔗 Déduire automatiquement le lien Behance depuis other_links si le champ dédié est vide
    if not (form_info.get("behance_url") or "").strip() and other_links:
        inferred_behance = None
        for link in other_links:
            if not isinstance(link, dict):
                continue
            link_type = (link.get("type") or "").lower()
            link_url = (link.get("url") or "").strip()
            if not link_url:
                continue
            if "behance" in link_type or "behance.net" in link_url:
                inferred_behance = link_url
                break
        if inferred_behance:
            form_info["behance_url"] = inferred_behance

    lang = (request.form.get("lang") or "fr").strip().lower()
    if lang not in ("fr", "en"):
        lang = "fr"

    # Génération des données Talent Card (extraction CV + Gemini) sans DOCX ; PDF via HTML ensuite
    recruit_base = os.getenv("RECRUIT_BASE_URL") or request.url_root.rstrip("/")
    recruit_url = f"{recruit_base}/recruit/{db_candidate_id}"
    result = generate_talent_card(
        form_info, cv_content,
        img_bytes=img_content,
        id_agent=id_agent,
        recruit_url=recruit_url,
        lang=lang,
    )

    if not result:
        return jsonify({"error": "Échec de génération de la Talent Card"}), 500

    # Priorité au domaine choisi dans le formulaire (et non à l'agent)
    selected_domaine = (form_info.get("domaine_activite") or "").strip()
    if selected_domaine:
        result["talentcard"]["domaine_activite"] = selected_domaine
        result["talentcard"]["categorie_profil"] = selected_domaine

    # Upload CV et image vers MinIO
    minio_storage = get_minio_storage()
    minio_urls = {
        'cv_url': None,
        'image_url': None,
        'talentcard_url': None,
        'talentcard_pdf_url': None,
    }

    minio_prefix = get_candidate_minio_prefix(db_candidate_id, result["talentcard"].get("categorie_profil"))
    if cv_content and cv_file:
        cv_filename = cv_file.filename or 'cv.pdf'
        cv_object_name = f"{minio_prefix}cv_{cv_filename}"
        success, url, _ = _upload_to_minio_with_logging(minio_storage, cv_content, cv_object_name)
        if success:
            minio_urls['cv_url'] = url

    if img_content and img_file:
        img_filename = img_file.filename or 'image.jpg'
        img_extension = os.path.splitext(img_filename)[1] or '.jpg'
        img_object_name = f"{minio_prefix}image{img_extension}"
        success, url, _ = _upload_to_minio_with_logging(minio_storage, img_content, img_object_name)
        if success:
            minio_urls['image_url'] = url

    # Mise à jour de l'enregistrement en base de données avec les données complètes
    talentcard_data = result["talentcard"]
    # Priorité aux liens saisis dans le formulaire (LinkedIn, GitHub)
    if form_info.get("linkedin_url"):
        talentcard_data["linkedin"] = (form_info.get("linkedin_url") or "").strip()
    if form_info.get("github_url"):
        talentcard_data["github"] = (form_info.get("github_url") or "").strip()
    if form_info.get("behance_url"):
        talentcard_data["behance"] = (form_info.get("behance_url") or "").strip()
    # Pays cible : depuis le formulaire (target_country) pour persistance en base
    if form_info.get("target_country"):
        pays_cible = (form_info.get("target_country") or "").strip()
        if pays_cible:
            talentcard_data["pays_cible"] = pays_cible
            talentcard_data["target_country"] = pays_cible
    # Prêt à relocaliser : depuis le formulaire pour persistance en base
    if form_info.get("pret_a_relocater") is not None:
        pret = (form_info.get("pret_a_relocater") or "").strip()
        if pret:
            talentcard_data["pret_a_relocater"] = pret[:100]
    # Niveau de séniorité : formulaire (seniority_level) ou JSON IA (niveau de seniorite)
    niveau = (form_info.get("seniority_level") or "").strip() or talentcard_data.get("niveau de seniorite") or talentcard_data.get("niveau_seniorite")
    if niveau:
        talentcard_data["niveau_seniorite"] = (niveau if isinstance(niveau, str) else str(niveau))[:100]
    # Exigences / pré-requis et critères de recherche : depuis le formulaire pour persistance en base
    if form_info.get("constraints") is not None:
        talentcard_data["constraints"] = (form_info.get("constraints") or "").strip() or None
    if form_info.get("search_criteria") is not None:
        talentcard_data["search_criteria"] = (form_info.get("search_criteria") or "").strip() or None
    if form_info.get("salaire_minimum") is not None:
        talentcard_data["salaire_minimum"] = (form_info.get("salaire_minimum") or "").strip() or None
    if form_info.get("domaine_activite") is not None:
        selected_domaine = (form_info.get("domaine_activite") or "").strip()
        if selected_domaine:
            talentcard_data["domaine_activite"] = selected_domaine
            talentcard_data["categorie_profil"] = selected_domaine
    # Sauvegarder l'output brut de l'agent A1 (le JSON qui est envoyé à l'agent B1)
    talentcard_json_path = os.path.join(GENERATED_FOLDER, f"talentcard_{candidate_uuid}.json")
    try:
        with open(talentcard_json_path, "w", encoding="utf-8") as f:
            json.dump(talentcard_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Output A1 sauvegardé: {talentcard_json_path}")
        # Upload du JSON Talent Card vers MinIO (pour B3 / entretien)
        try:
            with open(talentcard_json_path, "rb") as f:
                talentcard_json_bytes = f.read()
            talentcard_json_object = f"{minio_prefix}talentcard_{candidate_uuid}.json"
            success_json, url_json, _ = _upload_to_minio_with_logging(
                minio_storage, talentcard_json_bytes, talentcard_json_object, content_type="application/json"
            )
            if success_json:
                print(f"✅ JSON Talent Card uploadé vers MinIO: {url_json}")
        except Exception as e_upload:
            print(f"⚠️  Upload JSON Talent Card vers MinIO échoué: {e_upload}")
    except Exception as e:
        print(f"⚠️  Impossible de sauvegarder l'output JSON A1: {e}")
        talentcard_json_path = None
    db_update_success = False
    db_error = None
    
    try:
        updated_candidate_id = insert_talent_card(talentcard_data, minio_urls=minio_urls, candidate_id=db_candidate_id)

        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor()
            cursor.execute(
                "UPDATE candidates SET candidate_uuid = %s WHERE id = %s",
                (candidate_uuid, db_candidate_id)
            )
            cursor.close()

        # Talent Card PDF : uniquement via HTML → PDF (plus de DOCX)
        flask_base = (os.getenv("RECRUIT_BASE_URL") or request.host_url or "http://localhost:5002").rstrip("/")
        if not flask_base.startswith("http"):
            flask_base = f"http://{flask_base}"
        extra_tc = {}
        if form_info.get("target_country"):
            extra_tc["pays_cible"] = (form_info.get("target_country") or "").strip()
        if form_info.get("pret_a_relocater") is not None and (form_info.get("pret_a_relocater") or "").strip():
            extra_tc["pret_a_relocater"] = (form_info.get("pret_a_relocater") or "").strip()[:100]
        if form_info.get("salaire_minimum") is not None and (form_info.get("salaire_minimum") or "").strip():
            extra_tc["salaire_minimum"] = (form_info.get("salaire_minimum") or "").strip()[:50]
        ok_html, _html_content, _url_html, url_pdf, _err = generate_and_save_talent_card_html(
            candidate_id=db_candidate_id,
            candidate_uuid=id_agent,
            candidate_image_url=minio_urls.get("image_url"),
            candidate_email=talentcard_data.get("email"),
            candidate_phone=talentcard_data.get("phone"),
            candidate_job_title=talentcard_data.get("Titre de profil") or talentcard_data.get("titre_profil"),
            candidate_years_experience=talentcard_data.get("annees_experience"),
            candidate_linkedin_url=talentcard_data.get("linkedin"),
            candidate_github_url=talentcard_data.get("github"),
            candidate_behance_url=talentcard_data.get("behance"),
            flask_base_url=flask_base,
            save_to_minio=True,
            generate_pdf=True,
            lang=lang,
            extra_candidate_data=extra_tc if extra_tc else None,
        )
        if ok_html and url_pdf:
            minio_urls["talentcard_pdf_url"] = url_pdf
            insert_talent_card(talentcard_data, minio_urls={"talentcard_pdf_url": url_pdf}, candidate_id=db_candidate_id)
            print(f"✅ Talent Card PDF (HTML) uploadé vers MinIO: {url_pdf}")

        db_update_success = True
        print(f"✅ Candidat mis à jour en base de données avec ID: {updated_candidate_id}, UUID: {candidate_uuid}")
    except Exception as e:
        db_error = str(e)
        print(f"❌ Erreur lors de la mise à jour en base de données: {e}")

    response_data = {
        "candidate_id": candidate_uuid,
        "id_agent": id_agent,
        "talentcard": talentcard_data,
        "talentcard_json_path": talentcard_json_path,
        "minio_urls": minio_urls,
        "agent_explanation": result.get("agent_explanation", ""),
        "database": {
            "updated": db_update_success,
            "db_candidate_id": db_candidate_id,
            "error": db_error
        }
    }

    # IMPORTANT: le CV corrigé (agent 2) est généré plus tard, après corrections + validation,
    # via un endpoint dédié /correctedcv/<candidate_uuid>/generate.
    # L'orchestration n8n pour Agent 2 se fait maintenant dans /talentcard/<db_candidate_id>/validate
    
    # Toujours retourner 200, mais avec un warning dans la réponse si la mise à jour a échoué
    if not db_update_success:
        response_data["warning"] = "Talent Card générée avec succès, mais la mise à jour en base de données a échoué"
    
    return jsonify(response_data), 200


def _get_corrected_cv_pdf_bytes(db_candidate_id: int, candidate_uuid: str):
    """Retourne (pdf_bytes, file_name) pour le CV corrigé PDF si disponible (disque puis MinIO), sinon (None, None)."""
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT version_number FROM corrected_cv_versions
                WHERE candidate_id = %s AND candidate_uuid = %s
                ORDER BY version_number DESC LIMIT 1
                """,
                (db_candidate_id, candidate_uuid),
            )
            result = cursor.fetchone()
            cursor.close()
        if result:
            v = result.get("version_number")
            path = os.path.join(CORRECTED_PDF_FOLDER, f"corrected_cv_{candidate_uuid}_v{v}.pdf")
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    return f.read(), f"cv_{candidate_uuid}.pdf"
        pattern = os.path.join(CORRECTED_PDF_FOLDER, f"corrected_cv_{candidate_uuid}*.pdf")
        files = glob.glob(pattern)
        if files:
            latest = max(files, key=os.path.getmtime)
            with open(latest, "rb") as f:
                return f.read(), os.path.basename(latest)

        # Fallback MinIO : le PDF peut exister uniquement dans MinIO
        minio_storage = get_minio_storage()
        if minio_storage and minio_storage.client:
            minio_prefix = get_candidate_minio_prefix(db_candidate_id)
            version_to_try = result.get("version_number") if result else None
            if version_to_try is not None:
                object_name = f"{minio_prefix}corrected_cv_{candidate_uuid}_v{version_to_try}.pdf"
                ok, file_bytes, _ = minio_storage.download_file(object_name)
                if ok and file_bytes:
                    return file_bytes, f"cv_{candidate_uuid}.pdf"
            for v in range(1, 20):
                object_name = f"{minio_prefix}corrected_cv_{candidate_uuid}_v{v}.pdf"
                ok, file_bytes, _ = minio_storage.download_file(object_name)
                if ok and file_bytes:
                    return file_bytes, f"cv_{candidate_uuid}.pdf"
    except Exception as e:
        print(f"⚠️ _get_corrected_cv_pdf_bytes: {e}")
    return None, None


def _get_portfolio_pdf_bytes(db_candidate_id: int, candidate_uuid: str, version: str = "long"):
    """
    Récupère les bytes du PDF portfolio depuis MinIO.
    Tente plusieurs variantes de noms (avec/sans suffixe langue) pour compatibilité.
    """
    try:
        minio_storage = get_minio_storage()
        if not minio_storage or not minio_storage.client:
            return None, None

        minio_prefix = get_candidate_minio_prefix(db_candidate_id)
        if version == "one-page":
            candidates = [
                f"{minio_prefix}portfolio_{candidate_uuid}_one-page.pdf",
                f"{minio_prefix}portfolio_{candidate_uuid}_one-page_fr.pdf",
                f"{minio_prefix}portfolio_{candidate_uuid}_one-page_en.pdf",
            ]
            download_name = "portfolio_one_page.pdf"
        else:
            candidates = [
                f"{minio_prefix}portfolio_{candidate_uuid}.pdf",
                f"{minio_prefix}portfolio_{candidate_uuid}_fr.pdf",
                f"{minio_prefix}portfolio_{candidate_uuid}_en.pdf",
            ]
            download_name = "portfolio_long.pdf"

        for object_name in candidates:
            ok, file_bytes, _ = minio_storage.download_file(object_name)
            if ok and file_bytes:
                return file_bytes, download_name
    except Exception as e:
        print(f"⚠️ _get_portfolio_pdf_bytes ({version}): {e}")
    return None, None


@app.route("/recruit/<db_candidate_id>", methods=["GET"])
def recruit_landing(db_candidate_id):
    """
    Page d’atterrissage pour le recruteur (lien du QR code de la Talent Card).
    Affiche les liens vers Talent Card PDF, CV, portfolio long, portfolio one-page
    et l'option « Tout télécharger » (ZIP).
    """
    try:
        from database.connection import DatabaseConnection
        from flask import Response
        DatabaseConnection.initialize()
        db_id = int(db_candidate_id)
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT candidate_uuid, nom, prenom FROM candidates WHERE id = %s", (db_id,))
            row = cursor.fetchone()
            cursor.close()
        if not row or not row.get("candidate_uuid"):
            return "<h1>Candidat introuvable</h1><p>Ce lien n'est pas valide ou le profil n'est pas encore disponible.</p>", 404
        candidate_uuid = row["candidate_uuid"]
        nom = row.get("nom") or ""
        prenom = row.get("prenom") or ""
        base = os.getenv("RECRUIT_BASE_URL") or request.url_root.rstrip("/")
        assets_base_url = base.rstrip("/") + "/recruit/static/"

        talentcard_pdf_bytes, _ = _get_talent_card_pdf_bytes(db_id)
        has_talentcard = bool(talentcard_pdf_bytes)
        talentcard_url = f"{base}/talentcard/{db_id}/download"
        cv_preview_url = f"{base}/correctedcv/{candidate_uuid}/preview?db_candidate_id={db_id}"
        portfolio_long_url = f"{base}/portfolio/{candidate_uuid}/pdf?db_candidate_id={db_id}&version=long"
        portfolio_one_page_url = f"{base}/portfolio/{candidate_uuid}/pdf?db_candidate_id={db_id}&version=one-page"
        download_all_url = f"{base}/recruit/{db_id}/download-all"

        links_html = []
        if has_talentcard:
            links_html.append(f'<a href="{talentcard_url}" class="btn">TÉLÉCHARGER LA TALENT CARD (PDF)</a>')
        links_html.append(f'<a href="{cv_preview_url}" class="btn">VOIR / TÉLÉCHARGER LE CV</a>')
        links_html.append(f'<a href="{portfolio_long_url}" class="btn">VOIR LE PORTFOLIO</a>')
        links_html.append(f'<a href="{portfolio_one_page_url}" class="btn">VOIR LE PORTFOLIO ONE PAGE</a>')
        links_html.append(f'<a href="{download_all_url}" class="btn">TÉLÉCHARGER TOUS LES FICHIERS (ZIP)</a>')

        links_block = "\n    ".join(links_html)
        candidate_name = f"{prenom} {nom}".strip().upper() or "CANDIDAT"
        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Profil candidat – CV & Portfolio</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      padding: 7rem 3rem;
      overflow: hidden;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      background: #0d0d0d url('{assets_base_url}Modif-2.jpeg') no-repeat center center;
      background-size: cover;
      color: #fff;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }}
    body::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: url('{assets_base_url}Background-3.png') no-repeat center center;
      background-size: cover;
      pointer-events: none;
    }}
    .content {{
      position: relative;
      z-index: 1;
      width: 100%;
      max-width: 900px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    h1 {{
      font-size: 72px;
      font-weight: 500;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin: 0 0 24px 0;
      color: #fff;
      line-height: 1.1;
    }}
    .candidate-name {{
      font-size: 42px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #fff;
      margin: 0 0 64px 0;
      line-height: 1.2;
    }}
    .links {{
      display: flex;
      flex-direction: column;
      gap: 3rem;
    
    }}
    a.btn {{
      display: block;
      padding: 15px 20px;
      background: #ca1b28;
      color: #fff;
      text-decoration: none;
      border-radius: 0;
      font-weight: bold;
      font-size: 28px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      text-align: center;
      border: none;
      width: 100rem;
      height: 4rem;
      font-weight: 500;
    }}
    a.btn:hover {{ opacity: 0.9; }}
    @media (max-width: 600px) {{
      html, body {{ padding: 5rem 1rem; overflow-x: hidden; overflow-y: auto; }}
      .content {{ max-width: 100%; }}
      h1 {{ font-size: 28px; margin-bottom: 16px; }}
      .candidate-name {{ font-size: 22px; margin-bottom: 2rem; }}
      a.btn {{ width: 100%; max-width: 100%; font-size: 14px; padding: 22px 16px; min-height: 3rem; }}
      .links {{ gap: 1.5rem; width: 100%; }}
    }}
  </style>
</head>
<body>
  <div class="content">
    <h1>Profil candidat</h1>
    <p class="candidate-name">{candidate_name}</p>
    <div class="links">
      {links_block}
    </div>
  </div>
</body>
</html>"""
        return Response(html, mimetype="text/html; charset=utf-8")
    except Exception as e:
        print(f"❌ Erreur page recruteur: {e}")
        return "<h1>Erreur</h1><p>Impossible de charger cette page.</p>", 500


@app.route("/recruit/<db_candidate_id>/download-all", methods=["GET"])
def recruit_download_all(db_candidate_id):
    """
    Télécharge un ZIP contenant tous les fichiers disponibles
    (Talent Card PDF, CV corrigé PDF, portfolio long PDF, portfolio one-page PDF).
    Valide dès la création du candidat.
    """
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        db_id = int(db_candidate_id)
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT candidate_uuid, nom, prenom FROM candidates WHERE id = %s", (db_id,))
            row = cursor.fetchone()
            cursor.close()
        if not row or not row.get("candidate_uuid"):
            return jsonify({"error": "Candidat introuvable"}), 404
        candidate_uuid = row["candidate_uuid"]
        nom = row.get("nom") or ""
        prenom = row.get("prenom") or ""
        safe_name = re.sub(r"[^\w\s-]", "", f"{prenom}_{nom}".strip()) or "candidat"

        buf = BytesIO()
        with ZipFile(buf, "w") as zf:
            pdf_bytes, tc_name = _get_talent_card_pdf_bytes(db_id)
            if pdf_bytes:
                zf.writestr("talent_card.pdf", pdf_bytes)
            cv_bytes, cv_name = _get_corrected_cv_pdf_bytes(db_id, candidate_uuid)
            if cv_bytes:
                zf.writestr("cv.pdf", cv_bytes)
            portfolio_long_bytes, portfolio_long_name = _get_portfolio_pdf_bytes(
                db_id, candidate_uuid, version="long"
            )
            if portfolio_long_bytes:
                zf.writestr(portfolio_long_name, portfolio_long_bytes)
            portfolio_one_page_bytes, portfolio_one_page_name = _get_portfolio_pdf_bytes(
                db_id, candidate_uuid, version="one-page"
            )
            if portfolio_one_page_bytes:
                zf.writestr(portfolio_one_page_name, portfolio_one_page_bytes)

        buf.seek(0)
        download_name = f"{safe_name}_fichiers.zip"
        return send_file(
            buf,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/zip",
        )
    except Exception as e:
        print(f"❌ Erreur download-all: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/talentcard/<candidate_id>/docx", methods=["GET"])
def generate_docx(candidate_id):
    """Talent Card n'est plus générée en DOCX ; utiliser /talentcard/<db_candidate_id>/download pour le PDF."""
    return jsonify({
        "error": "Talent Card disponible uniquement en PDF",
        "download_pdf": f"/talentcard/{candidate_id}/download",
    }), 410


@app.route("/talentcard/<candidate_id>/json", methods=["GET"])
def download_talentcard_json(candidate_id):
    """
    Télécharge le JSON brut généré par l'agent A1 pour une exécution donnée.
    """
    file_name = f"talentcard_{candidate_id}.json"
    file_path = os.path.join(GENERATED_FOLDER, file_name)

    if not os.path.exists(file_path):
        return jsonify({"error": "Fichier JSON introuvable"}), 404

    return send_file(
        file_path,
        as_attachment=True,
        download_name=file_name,
        mimetype="application/json"
    )


@app.route("/talentcard/<db_candidate_id>", methods=["GET"])
def get_talent_card(db_candidate_id):
    """
    Récupère les données de la Talent Card depuis la base de données.
    
    Returns:
        JSON avec les données complètes de la Talent Card
    """
    try:
        talentcard_data = _load_talentcard_from_db(int(db_candidate_id))
        
        if not talentcard_data:
            return jsonify({"error": "Talent Card non trouvée pour ce candidat"}), 404
        
        return jsonify({
            "success": True,
            "talentcard": talentcard_data,
            "db_candidate_id": int(db_candidate_id)
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération de la Talent Card: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/talentcard/<db_candidate_id>/generate-html", methods=["POST"])
def generate_talent_card_html_route(db_candidate_id):
    """
    Génère la Talent Card en HTML (template talent_card_template.html), la sauvegarde dans MinIO,
    la convertit en PDF et uploade le PDF dans MinIO.
    Body (JSON, optionnel): { "lang": "fr" | "en" }
    Returns:
        JSON { success, talentcard_html_url, talentcard_html_pdf_url, error? }
    """
    try:
        db_candidate_id_int = int(db_candidate_id)
    except (TypeError, ValueError):
        return jsonify({"error": "ID candidat invalide"}), 400
    data = request.get_json() or {}
    lang = (data.get("lang") or "fr").strip().lower()
    if lang not in ("fr", "en"):
        lang = "fr"
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, id_agent, image_minio_url, email, phone, linkedin, github, behance, annees_experience, titre_profil FROM candidates WHERE id = %s",
                (db_candidate_id_int,),
            )
            candidate = cursor.fetchone()
            cursor.close()
        if not candidate:
            return jsonify({"error": "Candidat introuvable"}), 404
        flask_base_url = (os.getenv("RECRUIT_BASE_URL") or request.host_url or "http://localhost:5002").rstrip("/")
        if not flask_base_url.startswith("http"):
            flask_base_url = f"http://{flask_base_url}"
        success, html_content, minio_html_url, minio_pdf_url, error = generate_and_save_talent_card_html(
            candidate_id=db_candidate_id_int,
            candidate_uuid=candidate["id_agent"] or "",
            candidate_image_url=candidate.get("image_minio_url"),
            candidate_email=candidate.get("email"),
            candidate_phone=candidate.get("phone"),
            candidate_job_title=candidate.get("titre_profil"),
            candidate_years_experience=candidate.get("annees_experience"),
            candidate_linkedin_url=candidate.get("linkedin"),
            candidate_github_url=candidate.get("github"),
            candidate_behance_url=candidate.get("behance"),
            flask_base_url=flask_base_url,
            save_to_minio=True,
            generate_pdf=True,
            lang=lang,
        )
        if not success:
            return jsonify({"success": False, "error": error or "Génération échouée"}), 500
        return jsonify({
            "success": True,
            "talentcard_html_url": minio_html_url,
            "talentcard_html_pdf_url": minio_pdf_url,
        }), 200
    except Exception as e:
        print(f"❌ Erreur génération Talent Card HTML/PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/talentcard/<db_candidate_id>/update", methods=["POST"])
def update_talent_card(db_candidate_id):
    """
    Applique les corrections proposées par le candidat et régénère le talent card.
    """
    try:
        data = request.get_json()
        corrections = data.get("corrections", {})
        
        try:
            db_candidate_id_int = int(db_candidate_id)
        except Exception:
            db_candidate_id_int = db_candidate_id
        # Récupérer les données actuelles du candidat depuis la base
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM candidates WHERE id = %s", (db_candidate_id,))
            candidate = cursor.fetchone()
            
            if not candidate:
                return jsonify({"error": "Candidat introuvable"}), 404
            
            # Récupérer les données complètes depuis la base
            cursor.execute("""
                SELECT 
                    c.*,
                    GROUP_CONCAT(DISTINCT s.skill_name) as skills,
                    GROUP_CONCAT(DISTINCT l.language_name) as languages,
                    GROUP_CONCAT(DISTINCT ct.type_name) as contract_types
                FROM candidates c
                LEFT JOIN skills s ON c.id = s.candidate_id
                LEFT JOIN languages l ON c.id = l.candidate_id
                LEFT JOIN contract_types ct ON c.id = ct.candidate_id
                WHERE c.id = %s
                GROUP BY c.id
            """, (db_candidate_id,))
            candidate_full = cursor.fetchone()
            
            cursor.execute("SELECT * FROM experiences WHERE candidate_id = %s", (db_candidate_id,))
            experiences = cursor.fetchall()
            
            cursor.execute("SELECT * FROM realisations WHERE candidate_id = %s", (db_candidate_id,))
            realisations = cursor.fetchall()
            
            cursor.close()
        
        # Helper : ne pas écraser la valeur en base par une correction vide (champ non modifié envoyé en "")
        def _apply_correction(key, candidate_key=None):
            ckey = candidate_key or key
            raw = candidate.get(ckey, "") or ""
            val = corrections.get(key)
            if val is None:
                return raw.strip() if isinstance(raw, str) else (raw or "")
            if isinstance(val, str) and not val.strip():
                return raw.strip() if isinstance(raw, str) else ""
            return val.strip() if isinstance(val, str) else val

        # Construire les données du talent card avec les corrections appliquées
        talentcard_data = {
            "id_agent": candidate["id_agent"],
            "nom": _apply_correction("nom"),
            "prenom": _apply_correction("prenom"),
            "Titre de profil": _apply_correction("Titre de profil", "titre_profil"),
            "ville": _apply_correction("ville"),
            "pays": _apply_correction("pays"),
            "linkedin": _apply_correction("linkedin"),
            "github": _apply_correction("github"),
            "behance": _apply_correction("behance"),
            "email": _apply_correction("email"),
            "phone": _apply_correction("phone"),
            "annees_experience": corrections["annees_experience"] if "annees_experience" in corrections else candidate.get("annees_experience"),
            "disponibilite": _apply_correction("disponibilite"),
            "pret_a_relocater": _apply_correction("pret_a_relocater"),
            "niveau_seniorite": _apply_correction("niveau_seniorite"),
            "resume_bref": corrections.get("resume_bref", candidate.get("resume_bref", "")),
            "skills": corrections.get("skills", candidate_full.get("skills", "").split(",") if candidate_full.get("skills") else []),
            "experience": corrections.get("experience", [
                {
                    "Role": exp.get("role", ""),
                    "entreprise": exp.get("entreprise", ""),
                    "periode": exp.get("periode", ""),
                    "description": exp.get("description", "")
                } for exp in experiences
            ]),
            "realisations": corrections.get("realisations", [r.get("description", "") for r in realisations]),
            "langues_parlees": corrections.get("langues_parlees", candidate_full.get("languages", "").split(",") if candidate_full.get("languages") else []),
            "type_contrat": corrections.get("type_contrat", candidate_full.get("contract_types", "").split(",") if candidate_full.get("contract_types") else []),
            "analyse": corrections.get("analyse", "") or "",
        }
        
        minio_storage = get_minio_storage()
        minio_urls = {}

        # Mettre à jour la base avec les corrections
        updated_id = insert_talent_card(talentcard_data, minio_urls=minio_urls, candidate_id=db_candidate_id_int)
        print(f"[Update] insert_talent_card returned id : {updated_id}")

        # Régénérer la Talent Card en HTML puis PDF (plus de DOCX)
        flask_base = (os.getenv("RECRUIT_BASE_URL") or request.host_url or "http://localhost:5002").rstrip("/")
        if not flask_base.startswith("http"):
            flask_base = f"http://{flask_base}"
        update_lang = (data.get("lang") or "fr").strip().lower()
        if update_lang not in ("fr", "en"):
            update_lang = "fr"
        ok_html, _, _url_html, url_pdf, _err = generate_and_save_talent_card_html(
            candidate_id=db_candidate_id_int,
            candidate_uuid=candidate.get("id_agent") or "",
            candidate_image_url=candidate.get("image_minio_url"),
            candidate_email=talentcard_data.get("email"),
            candidate_phone=talentcard_data.get("phone"),
            candidate_job_title=talentcard_data.get("Titre de profil") or talentcard_data.get("titre_profil"),
            candidate_years_experience=talentcard_data.get("annees_experience"),
            candidate_linkedin_url=talentcard_data.get("linkedin"),
            candidate_github_url=talentcard_data.get("github"),
            candidate_behance_url=talentcard_data.get("behance") or candidate.get("behance"),
            flask_base_url=flask_base,
            save_to_minio=True,
            generate_pdf=True,
            lang=update_lang,
        )
        if ok_html and url_pdf:
            insert_talent_card(talentcard_data, minio_urls={"talentcard_pdf_url": url_pdf}, candidate_id=db_candidate_id_int)

        return jsonify({
            "success": True,
            "message": "Talent Card mis à jour avec succès",
            "talentcard": talentcard_data,
            "db_candidate_id": updated_id,
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour du talent card: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/talentcard/<db_candidate_id>/validate", methods=["POST"])
def validate_talent_card(db_candidate_id):
    """
    Valide la Talent Card (PDF généré via HTML). Retourne l'URL de téléchargement du PDF.
    """
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()

        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id_agent, candidate_uuid FROM candidates WHERE id = %s", (db_candidate_id,))
            candidate = cursor.fetchone()
            cursor.close()

        if not candidate:
            return jsonify({"error": "Candidat introuvable"}), 404

        candidate_uuid = candidate.get("candidate_uuid") or candidate.get("id_agent")
        talentcard_data = _load_talentcard_from_db(int(db_candidate_id))

        # Ne plus déclencher n8n/Agent 2 (B1) automatiquement après validation.
        # B1 (CV corrigé) et Agent 3 (chatbot) ne se lancent que lorsque l'utilisateur
        # les demande explicitement (bouton "Générer le CV" et "Démarrer la collecte").

        return jsonify({
            "success": True,
            "message": "Talent Card validée",
            "download_url": f"/talentcard/{db_candidate_id}/download",
            "preview_url": f"/talentcard/{db_candidate_id}/preview",
            "candidate_uuid": candidate_uuid,
            "agent2_triggered": False,
        }), 200
            
    except Exception as e:
        print(f"❌ Erreur lors de la validation du talent card: {e}")
        return jsonify({"error": str(e)}), 500


def _get_talent_card_pdf_bytes(db_candidate_id: int):
    """
    Retourne (pdf_bytes, file_name) pour la Talent Card PDF.
    Priorité : 1) Nouvelle version HTML (MinIO talentcard_html_{id_agent}.pdf), 2) Ancienne version (fichier local ou MinIO DOCX-based).
    """
    from database.connection import DatabaseConnection
    import glob as _glob

    DatabaseConnection.initialize()
    with DatabaseConnection.get_connection() as db:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id_agent FROM candidates WHERE id = %s", (db_candidate_id,))
        candidate = cursor.fetchone()
        cursor.close()
    if not candidate:
        return None, None

    id_agent = candidate.get("id_agent")
    if not id_agent:
        return None, None

    # 1) Nouvelle version : PDF généré depuis le HTML (MinIO)
    object_name = f"{get_candidate_minio_prefix(db_candidate_id)}talentcard_html_{id_agent}.pdf"
    try:
        minio_storage = get_minio_storage()
        success, pdf_bytes, _ = minio_storage.download_file(object_name)
        if success and pdf_bytes:
            return pdf_bytes, f"talentcard_{id_agent}.pdf"
    except Exception as e:
        print(f"⚠️ MinIO talentcard_html PDF: {e}")

    # 2) Fallback : ancienne version (fichier local généré depuis DOCX)
    pattern = os.path.join(GENERATED_FOLDER, "talentcard_*.pdf")
    files = _glob.glob(pattern)
    if files:
        matching = [f for f in files if id_agent and id_agent in os.path.basename(f)]
        latest = max(matching, key=os.path.getmtime) if matching else max(files, key=os.path.getmtime)
        if os.path.isfile(latest):
            with open(latest, "rb") as f:
                return f.read(), f"talentcard_{id_agent}.pdf"

    return None, None


@app.route("/talentcard/<db_candidate_id>/download", methods=["GET"])
def download_talent_card(db_candidate_id):
    """
    Télécharge le talent card en PDF (nouvelle version HTML si disponible, sinon ancienne version).
    """
    try:
        try:
            db_id = int(db_candidate_id)
        except (TypeError, ValueError):
            return jsonify({"error": "ID candidat invalide"}), 400

        pdf_bytes, file_name = _get_talent_card_pdf_bytes(db_id)
        if not pdf_bytes:
            return jsonify({"error": "Fichier Talent Card PDF introuvable"}), 404

        return send_file(
            BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=file_name or "talentcard.pdf",
            mimetype="application/pdf",
        )
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement Talent Card: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/talentcard/<db_candidate_id>/preview", methods=["GET"])
def preview_talent_card_pdf(db_candidate_id):
    """
    Affiche le PDF de la Talent Card pour prévisualisation (nouvelle version HTML si disponible).
    Sans ?raw=1 : retourne une page HTML (favicon TAP + iframe) pour que l'onglet affiche l'icône TAP.
    Avec ?raw=1 : retourne le PDF brut (pour l'iframe).
    """
    if not request.args.get("raw"):
        pdf_url = _build_pdf_preview_url()
        return _pdf_preview_html_wrapper("Talent Card - Aperçu", pdf_url)
    try:
        try:
            db_id = int(db_candidate_id)
        except (TypeError, ValueError):
            return jsonify({"error": "ID candidat invalide"}), 400

        pdf_bytes, file_name = _get_talent_card_pdf_bytes(db_id)
        if not pdf_bytes:
            return jsonify({"error": "Fichier Talent Card PDF introuvable"}), 404

        return send_file(
            BytesIO(pdf_bytes),
            as_attachment=False,
            download_name=file_name or "talentcard.pdf",
            mimetype="application/pdf",
        )
    except Exception as e:
        print(f"❌ Erreur prévisualisation Talent Card PDF: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/correctedcv/<candidate_uuid>/preview", methods=["GET"])
def preview_corrected_cv_pdf(candidate_uuid):
    """
    Affiche le PDF du CV corrigé pour prévisualisation dans le navigateur.
    Sans ?raw=1 : retourne une page HTML (favicon TAP + iframe) pour que l'onglet affiche l'icône TAP.
    Avec ?raw=1 : retourne le PDF brut (pour l'iframe ou le téléchargement).
    
    Query params:
        version: Numéro de version (optionnel, utilise la dernière si non fourni)
        db_candidate_id: ID du candidat en base de données (optionnel)
        raw: si présent, retourne le PDF directement (utilisé par l'iframe)
    """
    if not request.args.get("raw"):
        pdf_url = _build_pdf_preview_url()
        return _pdf_preview_html_wrapper("CV - Aperçu", pdf_url)
    try:
        version_number = request.args.get("version")
        db_candidate_id = request.args.get("db_candidate_id")
        
        # Si version_number est fourni, utiliser cette version
        if version_number:
            try:
                version_number = int(version_number)
            except ValueError:
                return jsonify({"error": "version_number invalide"}), 400
            
            pdf_path = os.path.join(CORRECTED_PDF_FOLDER, f"corrected_cv_{candidate_uuid}_v{version_number}.pdf")
            if os.path.exists(pdf_path):
                return send_file(
                    pdf_path,
                    as_attachment=False,
                    mimetype="application/pdf"
                )
        
        # Sinon, chercher la dernière version disponible
        import glob
        pattern = os.path.join(CORRECTED_PDF_FOLDER, f"corrected_cv_{candidate_uuid}_v*.pdf")
        pdf_files = glob.glob(pattern)
        
        if pdf_files:
            # Extraire le numéro de version du nom de fichier et prendre le plus récent
            def extract_version(filename):
                try:
                    match = re.search(r'_v(\d+)\.pdf$', filename)
                    return int(match.group(1)) if match else 0
                except:
                    return 0
            
            latest_pdf = max(pdf_files, key=lambda f: (extract_version(f), os.path.getmtime(f)))
            return send_file(
                latest_pdf,
                as_attachment=False,
                mimetype="application/pdf"
            )
        
        # Si pas de PDF trouvé sur disque, essayer de convertir depuis le HTML
        if db_candidate_id:
            html_pattern = os.path.join(CORRECTED_FOLDER, f"corrected_cv_{candidate_uuid}_v*.html")
            html_files = glob.glob(html_pattern)
            if html_files:
                latest_html = max(html_files, key=os.path.getmtime)
                match = re.search(r'_v(\d+)\.html$', latest_html)
                if match:
                    version_num = int(match.group(1))
                    pdf_path = os.path.join(CORRECTED_PDF_FOLDER, f"corrected_cv_{candidate_uuid}_v{version_num}.pdf")
                    if _convert_cv_html_to_pdf(latest_html, pdf_path):
                        return send_file(
                            pdf_path,
                            as_attachment=False,
                            mimetype="application/pdf"
                        )

        # Fallback MinIO : le PDF peut exister uniquement dans MinIO (pas sur disque)
        if db_candidate_id:
            try:
                db_id = int(db_candidate_id)
                minio_storage = get_minio_storage()
                if minio_storage and minio_storage.client:
                    minio_prefix = get_candidate_minio_prefix(db_id)
                    # Récupérer la dernière version depuis la base
                    from database.connection import DatabaseConnection
                    DatabaseConnection.initialize()
                    with DatabaseConnection.get_connection() as db:
                        cur = db.cursor(dictionary=True)
                        cur.execute(
                            """
                            SELECT version_number FROM corrected_cv_versions
                            WHERE candidate_id = %s AND candidate_uuid = %s
                            ORDER BY version_number DESC LIMIT 1
                            """,
                            (db_id, candidate_uuid),
                        )
                        row = cur.fetchone()
                        cur.close()
                    if row:
                        v = row.get("version_number")
                        object_name = f"{minio_prefix}corrected_cv_{candidate_uuid}_v{v}.pdf"
                        ok, pdf_bytes, _ = minio_storage.download_file(object_name)
                        if ok and pdf_bytes:
                            from flask import Response
                            return Response(
                                pdf_bytes,
                                mimetype="application/pdf",
                                headers={"Content-Disposition": "inline; filename=corrected_cv.pdf"}
                            )
                    # Essayer v1, v2, ... si pas de version en base
                    for v in range(1, 20):
                        object_name = f"{minio_prefix}corrected_cv_{candidate_uuid}_v{v}.pdf"
                        ok, pdf_bytes, _ = minio_storage.download_file(object_name)
                        if ok and pdf_bytes:
                            from flask import Response
                            return Response(
                                pdf_bytes,
                                mimetype="application/pdf",
                                headers={"Content-Disposition": "inline; filename=corrected_cv.pdf"}
                            )
            except Exception as e:
                print(f"⚠️ preview_corrected_cv_pdf MinIO fallback: {e}")
        
        return jsonify({"error": "Fichier PDF introuvable. Le PDF sera généré automatiquement lors de la prochaine génération du CV."}), 404
        
    except Exception as e:
        print(f"❌ Erreur lors de la prévisualisation du PDF: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/correctedcv/<candidate_uuid>/download", methods=["GET"])
def download_corrected_cv(candidate_uuid):
    """
    Télécharge le CV corrigé (agent 2) en PDF. 
    Si version_number est fourni dans les query params, télécharge cette version spécifique.
    Sinon, télécharge la dernière version approuvée ou la dernière version disponible.
    """
    try:
        version_number = request.args.get("version_number")
        db_candidate_id = request.args.get("db_candidate_id")
        
        # Si version_number est fourni, utiliser cette version
        if version_number:
            file_path = os.path.join(CORRECTED_PDF_FOLDER, f"corrected_cv_{candidate_uuid}_v{version_number}.pdf")
            if os.path.exists(file_path):
                file_name = f"corrected_cv_{candidate_uuid}_v{version_number}.pdf"
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=file_name,
                    mimetype="application/pdf"
                )
        
        # Sinon, chercher la dernière version approuvée ou la dernière disponible
        if db_candidate_id:
            from database.connection import DatabaseConnection
            DatabaseConnection.initialize()
            
            with DatabaseConnection.get_connection() as db:
                cursor = db.cursor(dictionary=True)
                # D'abord chercher une version approuvée
                cursor.execute(
                    """
                    SELECT version_number, corrected_pdf_minio_url
                    FROM corrected_cv_versions
                    WHERE candidate_id = %s AND candidate_uuid = %s AND validation_status = 'approved'
                    ORDER BY version_number DESC
                    LIMIT 1
                    """,
                    (db_candidate_id, candidate_uuid),
                )
                result = cursor.fetchone()
                
                # Sinon, prendre la dernière version
                if not result:
                    cursor.execute(
                        """
                        SELECT version_number, corrected_pdf_minio_url
                        FROM corrected_cv_versions
                        WHERE candidate_id = %s AND candidate_uuid = %s
                        ORDER BY version_number DESC
                        LIMIT 1
                        """,
                        (db_candidate_id, candidate_uuid),
                    )
                    result = cursor.fetchone()
                cursor.close()
            
            if result and result.get("version_number"):
                version_number = result["version_number"]
                file_path = os.path.join(CORRECTED_PDF_FOLDER, f"corrected_cv_{candidate_uuid}_v{version_number}.pdf")
                if os.path.exists(file_path):
                    file_name = f"corrected_cv_{candidate_uuid}_v{version_number}.pdf"
                    return send_file(
                        file_path,
                        as_attachment=True,
                        download_name=file_name,
                        mimetype="application/pdf"
                    )
        
        # Fallback: chercher le fichier PDF le plus récent
        import glob
        pattern = os.path.join(CORRECTED_PDF_FOLDER, f"corrected_cv_{candidate_uuid}*.pdf")
        files = glob.glob(pattern)
        
        if files:
            # Prendre le fichier le plus récent (par date de modification)
            latest_file = max(files, key=os.path.getmtime)
            file_name = os.path.basename(latest_file)
            return send_file(
                latest_file,
                as_attachment=True,
                download_name=file_name,
                mimetype="application/pdf"
            )
        
        return jsonify({"error": "Fichier CV corrigé PDF introuvable"}), 404
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement du CV corrigé: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/correctedcv/<candidate_uuid>/generate", methods=["POST"])
def generate_corrected_cv_after_validation(candidate_uuid):
    """
    Génère le CV corrigé (agent 2) APRÈS la validation du Talent Card.

    Body JSON:
      {
        "db_candidate_id": <int>,
        "talentcard_data": <dict> (optionnel, fourni par n8n)
      }
    """
    try:
        data = request.get_json() or {}
        db_candidate_id = data.get("db_candidate_id")
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id manquant"}), 400

        # Vérifier si le CV corrigé existe déjà (idempotence) — chercher la dernière version HTML/PDF
        html_pattern = os.path.join(CORRECTED_FOLDER, f"corrected_cv_{candidate_uuid}_v*.html")
        html_files = glob.glob(html_pattern)
        if html_files:
            latest_html = max(html_files, key=os.path.getmtime)
            match = re.search(r'_v(\d+)\.html$', latest_html)
            if match:
                version_num = match.group(1)
                print(f"ℹ️  CV corrigé existe déjà pour candidate_uuid={candidate_uuid} (v{version_num}), retour du fichier existant")
                minio_storage = get_minio_storage()
                _minio_pre = get_candidate_minio_prefix(db_candidate_id)
                corrected_minio = {"corrected_cv_url": None, "corrected_cv_html_url": None, "corrected_json_url": None, "corrected_pdf_url": None}
                try:
                    object_name_pdf = f"{_minio_pre}corrected_cv_{candidate_uuid}_v{version_num}.pdf"
                    object_name_html = f"{_minio_pre}corrected_cv_{candidate_uuid}_v{version_num}.html"
                    object_name_json = f"{_minio_pre}corrected_data_{candidate_uuid}_v{version_num}.json"
                    corrected_minio["corrected_cv_url"] = minio_storage.get_file_url(object_name_pdf)
                    corrected_minio["corrected_cv_html_url"] = minio_storage.get_file_url(object_name_html)
                    corrected_minio["corrected_pdf_url"] = corrected_minio["corrected_cv_url"]
                    corrected_minio["corrected_json_url"] = minio_storage.get_file_url(object_name_json)
                except Exception:
                    pass
                corrected_payload = {
                    "html_path": latest_html,
                    "minio_urls": corrected_minio,
                    "download_url": f"/correctedcv/{candidate_uuid}/download",
                    "agent_explanation": "🤖 Agent B1 - CV corrigé déjà généré précédemment. Le document est disponible pour téléchargement."
                }
                json_path = os.path.join(CORRECTED_FOLDER, f"corrected_data_{candidate_uuid}_v{version_num}.json")
                if os.path.isfile(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            existing_json = json.load(f)
                        corrected_payload["Realisations"] = existing_json.get("Realisations") or existing_json.get("realisations") or []
                        corrected_payload["Educations"] = existing_json.get("Educations") or existing_json.get("educations") or []
                        corrected_payload["corrected_json"] = existing_json
                    except Exception as e:
                        print(f"⚠️ Lecture JSON existant pour already_exists: {e}")
                return jsonify({
                    "success": True,
                    "message": "CV corrigé déjà généré",
                    "corrected": corrected_payload,
                    "agent_explanation": corrected_payload.get("agent_explanation", ""),
                    "already_exists": True
                }), 200

        # Utiliser talentcard_data du payload si fourni (depuis n8n), sinon charger depuis DB
        if "talentcard_data" in data:
            talentcard_data = data["talentcard_data"]
            print("✅ Utilisation du talentcard_data fourni via n8n")
        else:
            # Reconstruire le talentcard depuis la base (incluant corrections appliquées)
            talentcard_data = _load_talentcard_from_db(db_candidate_id)
            if not talentcard_data:
                return jsonify({"error": "Candidat introuvable"}), 404

        # Télécharger le CV original depuis MinIO + extraire du texte pour aider l'agent B1
        cv_text_for_agent2, _ = _get_candidate_cv_text(db_candidate_id)

        # Récupérer les commentaires de feedback précédents si version > 1
        previous_feedback = None
        version_number = 1
        try:
            from database.connection import DatabaseConnection
            DatabaseConnection.initialize()
            with DatabaseConnection.get_connection() as db:
                cursor = db.cursor(dictionary=True)
                # Récupérer la version la plus récente avec ORDER BY au lieu de GROUP BY
                cursor.execute(
                    """
                    SELECT version_number, feedback_comment
                    FROM corrected_cv_versions
                    WHERE candidate_id = %s AND candidate_uuid = %s
                    ORDER BY version_number DESC
                    LIMIT 1
                    """,
                    (db_candidate_id, candidate_uuid),
                )
                result = cursor.fetchone()
                if result and result.get("version_number"):
                    version_number = result["version_number"] + 1
                    previous_feedback = result.get("feedback_comment")
                cursor.close()
        except Exception as e:
            print(f"⚠️  Erreur lors de la récupération de la version précédente: {e}")

        corrected = _generate_corrected_cv_from_talentcard(
            talentcard_data,
            db_candidate_id=int(db_candidate_id),
            candidate_uuid=candidate_uuid,
            cv_text=cv_text_for_agent2,
            feedback_comments=previous_feedback,
            version_number=version_number,
        )

        # Ne plus déclencher Agent 3 (n8n) automatiquement après génération du CV.
        # Agent 3 ne se lance que lorsque l'utilisateur clique "Démarrer la collecte" sur la page Chatbot
        # (appel direct à /agent3/<candidate_uuid>/process).

        # L'explication de l'agent B1 est déjà incluse dans `corrected` via `_generate_corrected_cv_from_talentcard`
        return jsonify({
            "success": True, 
            "corrected": corrected,
            "agent_explanation": corrected.get("agent_explanation", "")  # Explication de l'Agent B1
        }), 200
    except Exception as e:
        print(f"❌ Erreur génération CV corrigé (post-validation): {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/correctedcv/<candidate_uuid>/validate", methods=["POST"])
def validate_corrected_cv(candidate_uuid):
    """
    Valide ou rejette le CV corrigé avec possibilité d'ajouter des commentaires.
    
    Body JSON:
    {
        "status": "approved" | "rejected" | "needs_revision",
        "feedback_comment": "Commentaires optionnels pour amélioration",
        "db_candidate_id": <int>,
        "version_number": <int> (optionnel, utilise la dernière version si non fourni)
    }
    """
    try:
        data = request.get_json() or {}
        status = data.get("status")
        feedback_comment = data.get("feedback_comment", "")
        db_candidate_id = data.get("db_candidate_id")
        version_number = data.get("version_number")

        if not status or status not in ["approved", "rejected", "needs_revision"]:
            return jsonify({"error": "status invalide. Doit être 'approved', 'rejected' ou 'needs_revision'"}), 400

        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id manquant"}), 400

        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()

        # Si version_number non fourni, récupérer la dernière version
        if not version_number:
            with DatabaseConnection.get_connection() as db:
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT MAX(version_number) as max_version
                    FROM corrected_cv_versions
                    WHERE candidate_id = %s AND candidate_uuid = %s
                    """,
                    (db_candidate_id, candidate_uuid),
                )
                result = cursor.fetchone()
                if result and result.get("max_version"):
                    version_number = result["max_version"]
                else:
                    return jsonify({"error": "Aucune version de CV corrigé trouvée"}), 404
                cursor.close()

        # Mettre à jour le statut de validation
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor()
            cursor.execute(
                """
                UPDATE corrected_cv_versions
                SET validation_status = %s, feedback_comment = %s
                WHERE candidate_id = %s AND candidate_uuid = %s AND version_number = %s
                """,
                (status, feedback_comment, db_candidate_id, candidate_uuid, version_number),
            )
            db.commit()
            cursor.close()

        # Sauvegarder dans la mémoire des validations pour que l'agent B1 apprenne
        try:
            from agent_memory import save_validation
            save_validation("B1", status, feedback_comment or None, db_candidate_id)
        except Exception as e:
            print(f"⚠️ Mémoire agent (save_validation): {e}")

        response_data = {
            "success": True,
            "message": f"CV corrigé marqué comme {status}",
            "status": status,
            "version_number": version_number,
        }

        # Si rejeté ou nécessite révision, indiquer qu'une nouvelle version peut être générée
        if status in ["rejected", "needs_revision"]:
            response_data["can_regenerate"] = True
            response_data["message"] = f"CV corrigé marqué comme {status}. Vous pouvez générer une nouvelle version avec les améliorations demandées."
        
        return jsonify(response_data), 200

    except Exception as e:
        print(f"❌ Erreur lors de la validation du CV corrigé: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/correctedcv/<candidate_uuid>/enrich", methods=["POST"])
def enrich_corrected_cv(candidate_uuid):
    """
    Enrichit le CV corrigé avec des projets (Realisations) et/ou formations (Educations)
    saisis manuellement lorsque l'extraction ne les a pas trouvés.

    Body JSON:
    {
        "db_candidate_id": <int>,
        "realisations": [ { "nom": "", "contexte": "", "stack": "", "detail": "" }, ... ],
        "educations": [ { "degree": "", "school": "", "period": "" }, ... ]
    }
    """
    try:
        data = request.get_json() or {}
        db_candidate_id = data.get("db_candidate_id")
        realisations = data.get("realisations") or data.get("Realisations") or []
        educations = data.get("educations") or data.get("Educations") or []
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id manquant"}), 400

        json_pattern = os.path.join(CORRECTED_FOLDER, f"corrected_data_{candidate_uuid}_v*.json")
        json_files = glob.glob(json_pattern)
        if not json_files:
            return jsonify({"error": "Aucun CV corrigé trouvé pour ce candidat. Générez d'abord le CV corrigé."}), 404

        latest_json_path = max(json_files, key=os.path.getmtime)
        match = re.search(r'_v(\d+)\.json$', latest_json_path)
        version_number = int(match.group(1)) if match else 1

        with open(latest_json_path, "r", encoding="utf-8") as f:
            corrected = json.load(f)

        if realisations:
            corrected["Realisations"] = [
                {
                    "nom": (r.get("nom") or r.get("name") or "").strip(),
                    "contexte": (r.get("contexte") or r.get("context") or "").strip(),
                    "stack": (r.get("stack") or "").strip(),
                    "detail": (r.get("detail") or r.get("description") or "").strip(),
                }
                for r in realisations
                if isinstance(r, dict) and (r.get("nom") or r.get("name") or r.get("detail") or r.get("description"))
            ]
        if educations:
            corrected["Educations"] = [
                {
                    "degree": (e.get("degree") or e.get("diplome") or e.get("name") or "").strip(),
                    "school": (e.get("school") or e.get("etablissement") or e.get("organization") or "").strip(),
                    "period": (e.get("period") or e.get("annee") or e.get("year") or "").strip(),
                }
                for e in educations
                if isinstance(e, dict) and (e.get("degree") or e.get("diplome") or e.get("school") or e.get("etablissement"))
            ]

        with open(latest_json_path, "w", encoding="utf-8") as f:
            json.dump(corrected, f, ensure_ascii=False, indent=2)

        html_template_path = None
        for p in CV_HTML_TEMPLATE_PATHS:
            if os.path.exists(p):
                html_template_path = p
                break
        if not html_template_path:
            return jsonify({"error": "Template CV HTML introuvable"}), 500

        out_html_path = os.path.join(CORRECTED_FOLDER, f"corrected_cv_{candidate_uuid}_v{version_number}.html")
        out_pdf_path = os.path.join(CORRECTED_PDF_FOLDER, f"corrected_cv_{candidate_uuid}_v{version_number}.pdf")

        # Recréer le contexte du CV à partir du JSON corrigé
        cv_context = transform_corrected_json_to_cv_context(corrected)

        # Réinjecter ville, pays et surtout la photo à partir de la Talent Card,
        # comme lors de la génération initiale du CV corrigé.
        try:
            orig = _load_talentcard_from_db(int(db_candidate_id)) or {}
        except Exception:
            orig = {}

        c = cv_context.get("candidate") or {}
        if not (c.get("ville") or "").strip():
            c["ville"] = (orig.get("ville") or "").strip()
        if not (c.get("pays") or "").strip():
            c["pays"] = (orig.get("pays") or "").strip()

        # Récupérer l'URL de l'image (MinIO) et la convertir en URL proxy si nécessaire
        try:
            img_url = _get_candidate_image_url(int(db_candidate_id))
        except Exception:
            img_url = None
        if img_url and not (c.get("profile_image_url") or "").strip():
            c["profile_image_url"] = _convert_minio_url_to_proxy(img_url) or img_url

        cv_context["candidate"] = c

        render_cv_html(html_template_path, cv_context, out_html_path)
        pdf_converted = _convert_cv_html_to_pdf(out_html_path, out_pdf_path)

        minio_storage = get_minio_storage()
        minio_prefix = get_candidate_minio_prefix(db_candidate_id)
        try:
            if os.path.exists(out_html_path):
                with open(out_html_path, "rb") as f:
                    html_bytes = f.read()
                object_name = f"{minio_prefix}corrected_cv_{candidate_uuid}_v{version_number}.html"
                _upload_to_minio_with_logging(minio_storage, html_bytes, object_name, content_type="text/html; charset=utf-8")
            if os.path.exists(latest_json_path):
                with open(latest_json_path, "rb") as f:
                    json_bytes = f.read()
                object_name = f"{minio_prefix}corrected_data_{candidate_uuid}_v{version_number}.json"
                _upload_to_minio_with_logging(minio_storage, json_bytes, object_name, content_type="application/json")
            if pdf_converted and os.path.exists(out_pdf_path):
                with open(out_pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                object_name = f"{minio_prefix}corrected_cv_{candidate_uuid}_v{version_number}.pdf"
                _upload_to_minio_with_logging(minio_storage, pdf_bytes, object_name, content_type="application/pdf")
        except Exception as e:
            print(f"⚠️ Erreur upload MinIO après enrichissement: {e}")

        return jsonify({
            "success": True,
            "message": "CV corrigé enrichi avec vos projets et formations",
            "corrected": {
                "Realisations": corrected.get("Realisations", []),
                "Educations": corrected.get("Educations", []),
                "corrected_json": corrected,
                "agent_explanation": "✅ Vos projets et formations ont été ajoutés au CV corrigé.",
            },
        }), 200
    except Exception as e:
        print(f"❌ Erreur enrichissement CV corrigé: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/correctedcv/<candidate_uuid>/status", methods=["GET"])
def get_corrected_cv_status(candidate_uuid):
    """
    Récupère le statut et les versions du CV corrigé pour un candidat.
    
    Query params:
        db_candidate_id: ID du candidat en base de données
    """
    try:
        db_candidate_id = request.args.get("db_candidate_id")
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id manquant"}), 400

        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()

        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, version_number, validation_status, feedback_comment,
                       corrected_cv_minio_url, corrected_json_minio_url,
                       created_at, updated_at
                FROM corrected_cv_versions
                WHERE candidate_id = %s AND candidate_uuid = %s
                ORDER BY version_number DESC
                """,
                (db_candidate_id, candidate_uuid),
            )
            versions = cursor.fetchall()
            cursor.close()

        return jsonify({
            "success": True,
            "versions": versions,
            "latest_version": versions[0] if versions else None,
        }), 200

    except Exception as e:
        print(f"❌ Erreur lors de la récupération du statut: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/correctedcv/<candidate_uuid>/regenerate", methods=["POST"])
def regenerate_corrected_cv(candidate_uuid):
    """
    Régénère le CV corrigé en tenant compte des commentaires de feedback.
    
    Body JSON:
    {
        "db_candidate_id": <int>,
        "feedback_comment": "Commentaires pour amélioration" (optionnel si déjà en base)
    }
    """
    try:
        data = request.get_json() or {}
        db_candidate_id = data.get("db_candidate_id")
        feedback_comment = data.get("feedback_comment")

        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id manquant"}), 400

        # Charger les données du talentcard
        talentcard_data = _load_talentcard_from_db(db_candidate_id)
        if not talentcard_data:
            return jsonify({"error": "Candidat introuvable"}), 404

        # Récupérer la version précédente et ses commentaires
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        
        version_number = 1
        previous_feedback = feedback_comment
        
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            # Récupérer la version la plus récente avec ORDER BY au lieu de MAX() + feedback_comment
            cursor.execute(
                """
                SELECT version_number, feedback_comment
                FROM corrected_cv_versions
                WHERE candidate_id = %s AND candidate_uuid = %s
                ORDER BY version_number DESC
                LIMIT 1
                """,
                (db_candidate_id, candidate_uuid),
            )
            result = cursor.fetchone()
            if result and result.get("version_number"):
                version_number = result["version_number"] + 1
                # Utiliser le feedback fourni ou celui de la version précédente
                if not previous_feedback:
                    previous_feedback = result.get("feedback_comment")
            cursor.close()

        # Télécharger le CV original pour extraction du texte
        cv_text_for_agent2, _ = _get_candidate_cv_text(db_candidate_id)

        # Générer la nouvelle version
        corrected = _generate_corrected_cv_from_talentcard(
            talentcard_data,
            db_candidate_id=int(db_candidate_id),
            candidate_uuid=candidate_uuid,
            cv_text=cv_text_for_agent2,
            feedback_comments=previous_feedback,
            version_number=version_number,
        )

        return jsonify({
            "success": True,
            "message": f"Nouvelle version {version_number} du CV corrigé générée",
            "corrected": corrected,
        }), 200

    except Exception as e:
        print(f"❌ Erreur lors de la régénération du CV corrigé: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/agent3/files/<path:file_path>", methods=["GET"])
def proxy_minio_file(file_path):
    """
    Proxy pour télécharger des fichiers depuis MinIO sans exposer les credentials.
    Utilisé par n8n pour accéder aux fichiers JSON/DOCX depuis MinIO.
    
    Args:
        file_path: Chemin du fichier dans MinIO (ex: candidates/31/corrected_data_xxx.json)
    """
    try:
        print(f"🔄 [Proxy] Tentative de téléchargement: {file_path}")
        minio_storage = get_minio_storage()
        
        if not minio_storage or not minio_storage.client:
            error_msg = "Client MinIO non initialisé"
            print(f"❌ [Proxy] {error_msg}")
            return jsonify({"error": error_msg}), 500
        
        success, file_bytes, error = minio_storage.download_file(file_path)
        
        if not success:
            error_msg = error or "Fichier introuvable"
            print(f"❌ [Proxy] Erreur téléchargement fichier MinIO ({file_path}): {error_msg}")
            
            # Vérifier si c'est une erreur d'accès
            if "AccessDenied" in str(error) or "Forbidden" in str(error):
                return jsonify({
                    "error": "AccessDenied",
                    "message": "Accès refusé au fichier MinIO. Vérifiez les credentials et les permissions du bucket.",
                    "file_path": file_path
                }), 403
            elif "NoSuchKey" in str(error) or "Not Found" in str(error):
                return jsonify({
                    "error": "FileNotFound",
                    "message": f"Fichier introuvable dans MinIO: {file_path}",
                    "file_path": file_path
                }), 404
            else:
                return jsonify({
                    "error": "DownloadError",
                    "message": error_msg,
                    "file_path": file_path
                }), 500
        
        # Déterminer le content-type
        if file_path.endswith(".json"):
            content_type = "application/json"
        elif file_path.endswith(".docx"):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif file_path.endswith(".pdf"):
            content_type = "application/pdf"
        else:
            content_type = "application/octet-stream"
        
        print(f"✅ [Proxy] Fichier téléchargé avec succès: {file_path} ({len(file_bytes)} bytes)")
        return send_file(
            BytesIO(file_bytes),
            mimetype=content_type,
            as_attachment=False
        )
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [Proxy] Erreur proxy MinIO ({file_path}): {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "ProxyError",
            "message": error_msg,
            "file_path": file_path
        }), 500




@app.route("/chatbot/<db_candidate_id>/summary", methods=["GET"])
def get_chatbot_summary(db_candidate_id):
    """
    Récupère un résumé des données collectées par le chatbot.
    
    Query params:
        session_id: UUID de la session (optionnel)
    """
    try:
        from database.connection import DatabaseConnection
        
        DatabaseConnection.initialize()
        
        session_id = request.args.get("session_id")
        
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            
            # Récupérer les projets
            cursor.execute(
                """
                SELECT id, project_name, project_description, github_url, demo_url, 
                       image_urls, additional_links, status, created_at, updated_at
                FROM candidate_projects
                WHERE candidate_id = %s
                ORDER BY created_at ASC
                """,
                (db_candidate_id,)
            )
            projects = cursor.fetchall()
            
            # Récupérer l'historique de conversation
            query = """
                SELECT message_type, message_content, project_id, created_at, metadata
                FROM chatbot_conversations
                WHERE candidate_id = %s
            """
            params = [db_candidate_id]
            
            if session_id:
                query += " AND session_id = %s"
                params.append(session_id)
            
            query += " ORDER BY created_at ASC"
            
            cursor.execute(query, tuple(params))
            conversations = cursor.fetchall()
            
            cursor.close()
        
        return jsonify({
            "success": True,
            "candidate_id": db_candidate_id,
            "session_id": session_id,
            "projects_count": len(projects),
            "projects": projects,
            "conversations_count": len(conversations),
            "conversations": conversations
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur récupération résumé chatbot: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/chatbot/<db_candidate_id>/projects", methods=["GET"])
def get_candidate_projects(db_candidate_id):
    """
    Récupère tous les projets collectés pour un candidat.
    """
    try:
        from database.connection import DatabaseConnection
        
        DatabaseConnection.initialize()
        
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, project_name, project_description, github_url, demo_url,
                       image_urls, additional_links, status, notes, created_at, updated_at
                FROM candidate_projects
                WHERE candidate_id = %s
                ORDER BY created_at DESC
                """,
                (db_candidate_id,)
            )
            projects = cursor.fetchall()
            cursor.close()
        
        return jsonify({
            "success": True,
            "candidate_id": db_candidate_id,
            "projects": projects
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur récupération projets: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ENDPOINT AGENT 3 (B2) - GÉNÉRATION DE QUESTIONS AVEC GEMINI
# ============================================================================

@app.route("/agent3/<candidate_uuid>/process", methods=["POST"])
def agent3_process(candidate_uuid):
    """
    Endpoint pour l'Agent 3 (B2) qui génère des questions avec Gemini AI
    pour collecter les informations sur les projets du candidat.
    
    Utilisé par le workflow n8n après la génération de la Talent Card (A1) et du CV corrigé (B1).
    
    Body (JSON):
        db_candidate_id: int (obligatoire)
        id_agent: str (obligatoire)
        a1_output: dict - Output Agent 1 (Talent Card)
        b1_output: dict - Output Agent 2 (CV corrigé)
        talentcard_data: dict (optionnel) - Alias de a1_output
        corrected_cv_data: dict (optionnel) - Alias de b1_output
    
    Returns:
        JSON avec les questions générées et la session ID
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Body JSON requis"}), 400
        
        db_candidate_id = data.get("db_candidate_id")
        id_agent = data.get("id_agent")
        a1_output = data.get("a1_output") or data.get("talentcard_data")
        b1_output = data.get("b1_output") or data.get("corrected_cv_data")
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        
        if not a1_output or not b1_output:
            return jsonify({
                "error": "a1_output (talentcard_data) et b1_output (corrected_cv_data) sont requis"
            }), 400
        
        from B2.chat.pose_question import generate_questions_with_gemini
        
        # Construire le profil à partir des données A1 et B1
        profile_data = {}
        
        # Extraire les projets depuis b1_output (CV corrigé) ET a1_output (Talent Card)
        # Le CV corrigé utilise "Realisations" (pas "Projects")
        projects = []
        
        # ========== EXTRACTION DEPUIS B1_OUTPUT (CV corrigé) ==========
        # 1. Essayer d'extraire depuis "Realisations" (format du CV corrigé)
        realisations = b1_output.get("Realisations") or b1_output.get("realisations") or []
        if isinstance(realisations, list) and len(realisations) > 0:
            projects = [
                r.get("nom", "") if isinstance(r, dict) else str(r)
                for r in realisations
                if (isinstance(r, dict) and r.get("nom")) or (isinstance(r, str) and r.strip())
            ]
        projects_list = b1_output.get("Projects") or b1_output.get("projects") or []
        if not projects and isinstance(projects_list, list) and len(projects_list) > 0:
            projects = [
                p.get("Name", "") or p.get("name", "") if isinstance(p, dict) else str(p)
                for p in projects_list
                if (isinstance(p, dict) and (p.get("Name") or p.get("name"))) or (isinstance(p, str) and p.strip())
            ]
        experiences_b1 = b1_output.get("Experiences") or b1_output.get("experiences") or b1_output.get("Experience") or b1_output.get("experience") or []
        if not projects and isinstance(experiences_b1, list) and len(experiences_b1) > 0:
            for exp in experiences_b1:
                if isinstance(exp, dict):
                    desc = exp.get("description", "") or exp.get("Description", "") or exp.get("detail", "") or exp.get("Detail", "")
                    title = exp.get("title", "") or exp.get("Title", "") or exp.get("Role", "") or exp.get("role", "")
                    if desc and len(desc) > 20 and title and title not in projects:
                        projects.append(title)
        
        if not projects and isinstance(a1_output, dict):
            experience_a1 = a1_output.get("experience") or a1_output.get("Experience") or []
            if isinstance(experience_a1, list) and len(experience_a1) > 0:
                for exp in experience_a1:
                    if isinstance(exp, dict):
                        role = exp.get("Role", "") or exp.get("role", "") or exp.get("title", "") or exp.get("Title", "")
                        desc = exp.get("description", "") or exp.get("Description", "") or exp.get("detail", "") or exp.get("Detail", "")
                        if role and desc and len(desc) > 20 and role not in projects:
                            projects.append(role)
            realisations_a1 = a1_output.get("realisations") or a1_output.get("Realisations") or []
            if not projects and isinstance(realisations_a1, list) and len(realisations_a1) > 0:
                for r in realisations_a1:
                    if isinstance(r, dict):
                        nom = r.get("nom", "") or r.get("Nom", "") or r.get("name", "") or r.get("Name", "")
                        if nom and nom not in projects:
                            projects.append(nom)
        if not projects:
            titre = b1_output.get("Titre") or b1_output.get("titre") or b1_output.get("Title") or b1_output.get("title")
            if not titre and isinstance(a1_output, dict):
                titre = a1_output.get("Titre de profil") or a1_output.get("titre de profil") or a1_output.get("Title")
            if titre:
                projects = [titre]
        
        # Extraire l'expérience depuis b1_output (format: "Experiences" avec minuscule)
        experience = {}
        experiences_list = b1_output.get("Experiences") or b1_output.get("Experience", [])
        if isinstance(experiences_list, list) and len(experiences_list) > 0:
            exp = experiences_list[0]  # Prendre la première expérience
            experience = {
                "title": exp.get("title") or exp.get("Title", ""),
                "company": exp.get("company") or exp.get("Company", ""),
                "period": exp.get("period") or exp.get("Period", ""),
                "description": exp.get("description") or exp.get("Description", "")
            }
        
        # Extraire l'éducation depuis b1_output (format: "Educations" avec minuscule)
        education = []
        educations_list = b1_output.get("Educations") or b1_output.get("Education", [])
        if isinstance(educations_list, list):
            education = [
                {
                    "degree": (edu.get("degree") or edu.get("Degree", "")) if isinstance(edu, dict) else str(edu),
                    "school": (edu.get("school") or edu.get("School", "")) if isinstance(edu, dict) else "",
                    "period": (edu.get("period") or edu.get("Period", "")) if isinstance(edu, dict) else ""
                }
                for edu in educations_list
            ]
        
        # Construire le profil avec toutes les expériences (pas seulement la première)
        all_experiences = []
        if isinstance(experiences_list, list):
            all_experiences = [
                {
                    "title": exp.get("title") or exp.get("Title", "") or exp.get("Role", "") or exp.get("role", ""),
                    "company": exp.get("company") or exp.get("Company", "") or exp.get("entreprise", "") or exp.get("Entreprise", ""),
                    "period": exp.get("period") or exp.get("Period", "") or exp.get("periode", "") or exp.get("Periode", ""),
                    "description": exp.get("description") or exp.get("Description", "") or exp.get("detail", "") or exp.get("Detail", "")
                }
                for exp in experiences_list
                if isinstance(exp, dict)
            ]
        
        if isinstance(a1_output, dict):
            experience_a1 = a1_output.get("experience") or a1_output.get("Experience") or []
            if isinstance(experience_a1, list) and len(experience_a1) > 0:
                for exp_a1 in experience_a1:
                    if isinstance(exp_a1, dict):
                        # Vérifier si cette expérience n'est pas déjà dans la liste
                        role_a1 = exp_a1.get("Role", "") or exp_a1.get("role", "")
                        title_a1 = exp_a1.get("title", "") or exp_a1.get("Title", "")
                        # Ajouter si elle n'existe pas déjà
                        exists = any(
                            (e.get("title") == role_a1 or e.get("title") == title_a1) 
                            for e in all_experiences
                        )
                        if not exists:
                            all_experiences.append({
                                "title": role_a1 or title_a1,
                                "company": exp_a1.get("entreprise", "") or exp_a1.get("Entreprise", "") or exp_a1.get("company", "") or exp_a1.get("Company", ""),
                                "period": exp_a1.get("periode", "") or exp_a1.get("Periode", "") or exp_a1.get("period", "") or exp_a1.get("Period", ""),
                                "description": exp_a1.get("description", "") or exp_a1.get("Description", "") or exp_a1.get("detail", "") or exp_a1.get("Detail", "")
                            })
        
        # Construire le profil
        profile_data = {
            "experience": experience,  # Première expérience (pour compatibilité)
            "experiences": all_experiences,  # Toutes les expériences (b1 + a1)
            "education": education,
            "projects": projects,
            "realisations": b1_output.get("Realisations", []) or b1_output.get("realisations", [])  # Ajouter aussi les réalisations complètes
        }
        
        talentcard_data = a1_output
        
        # Générer les questions avec Gemini
        result = generate_questions_with_gemini(profile_data, talentcard_data)
        
        if not result["success"]:
            error_type = result.get("error_type", "unknown_error")
            error_msg = result.get("error", "Erreur inconnue")
            
            # Code HTTP selon le type d'erreur
            if error_type == "quota_exceeded":
                http_status = 429  # Too Many Requests
            elif error_type == "auth_error":
                http_status = 401  # Unauthorized
            elif error_type == "timeout":
                http_status = 504  # Gateway Timeout
            else:
                http_status = 500  # Internal Server Error
            
            print(f"❌ [Agent3] Erreur ({error_type}): {error_msg}")
            
            return jsonify({
                "success": False,
                "error": error_msg,
                "error_type": error_type,
                "candidate_uuid": candidate_uuid,
                "db_candidate_id": db_candidate_id,
                "suggestion": (
                    "Attendez quelques minutes et réessayez" if error_type == "quota_exceeded"
                    else "Vérifiez votre configuration" if error_type == "auth_error"
                    else "Réessayez plus tard"
                )
            }), http_status
        
        questions = result.get("questions", [])
        
        # Vérifier si des questions ont été générées
        if not questions or len(questions) == 0:
            return jsonify({
                "success": False,
                "error": f"Aucune question générée. Aucun projet identifié dans le CV (projets trouvés: {len(projects)}). Veuillez vérifier que votre CV contient des projets ou réalisations.",
                "candidate_uuid": candidate_uuid,
                "db_candidate_id": db_candidate_id,
                "projects_identified": len(projects),
                "projects": projects,
                "questions": [],
                "total_questions": 0,
                "suggestion": "Vérifiez que votre CV contient des sections 'Projets', 'Réalisations' ou des expériences avec des descriptions détaillées de projets."
            }), 400
        
        # Générer un session_id unique pour cette session
        session_id = str(uuid.uuid4())
        
        # Sauvegarder la session dans la base de données (optionnel)
        # Pour l'instant, on retourne juste les questions
        
        response_data = {
            "success": True,
            "candidate_uuid": candidate_uuid,
            "db_candidate_id": db_candidate_id,
            "id_agent": id_agent,
            "chatbot_started": True,
            "session_id": session_id,
            "projects_identified": len(projects),
            "projects": projects,  # Liste des projets identifiés
            "questions": questions,
            "total_questions": len(questions),
            "first_question": questions[0] if questions else None,
            "message": f"Bonjour ! J'ai analysé votre CV et identifié {len(projects)} projet(s). J'ai généré {len(questions)} question(s) pour collecter les informations nécessaires à votre portfolio.",
            "processed_at": datetime.now().isoformat(),
            "note": "Les questions ont été générées avec succès. Utilisez l'endpoint /agent3/<candidate_uuid>/save-responses pour sauvegarder les réponses."
        }
        
        print(f"✅ [Agent3] {len(questions)} questions générées avec succès pour candidate_uuid={candidate_uuid}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ [Agent3] Erreur lors du traitement: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "candidate_uuid": candidate_uuid
        }), 500


# ============================================================================
# ENDPOINT AGENT 3 - SAUVEGARDE DES RÉPONSES
# ============================================================================

def group_questions_by_project(questions, answers):
    """
    Groupe les questions et réponses par projet en analysant les IDs.
    
    Les IDs peuvent être au format:
    - proj1_title, proj1_github, proj2_title, etc.
    - exp1_title, exp1_description, exp2_title, etc.
    - project1_title, project2_title, etc.
    
    Returns:
        dict: {project_key: {"questions": [...], "answers": {...}, "project_name": str}}
    """
    projects = {}
    
    for question in questions:
        if not question or not question.get("id"):
            continue
        
        q_id = question["id"]
        answer = answers.get(q_id, "")
        
        # Identifier le projet depuis l'ID
        # Format attendu: proj1_title, exp1_description, project1_github, etc.
        project_key = None
        project_name = None
        
        # Patterns pour identifier le projet
        patterns = [
            r'^(proj|project|exp)(\d+)_',  # proj1_title, exp2_description
            r'^(\w+)_(\d+)_',  # project_1_title
        ]
        
        for pattern in patterns:
            match = re.match(pattern, q_id, re.IGNORECASE)
            if match:
                prefix = match.group(1).lower()
                num = match.group(2)
                project_key = f"{prefix}{num}"
                
                # Essayer d'extraire le nom du projet depuis la question
                if "title" in q_id.lower() and answer:
                    project_name = answer.strip()[:100]  # Limiter la longueur
                elif "nom" in q_id.lower() and answer:
                    project_name = answer.strip()[:100]
                break
        
        # Si pas de pattern trouvé, essayer d'extraire depuis le texte de la question
        if not project_key:
            # Chercher des mentions de projet dans le texte
            q_text = question.get("text", "")
            match = re.search(r"projet\s+['\"]([^'\"]+)['\"]", q_text, re.IGNORECASE)
            if match:
                project_name = match.group(1)
                # Créer une clé basée sur le nom
                project_key = re.sub(r'[^a-zA-Z0-9]', '_', project_name.lower())[:50]
        
        # Si toujours pas de projet identifié, essayer de trouver le projet depuis le texte de la question
        if not project_key:
            # Chercher des mentions de projet dans le texte de la question
            q_text = question.get("text", "").lower()
            # Chercher des patterns comme "projet X", "le projet Y", etc.
            match = re.search(r"(?:projet|project)\s+['\"]?([^'\"\?\.]+)['\"]?", q_text, re.IGNORECASE)
            if match:
                potential_name = match.group(1).strip()
                if len(potential_name) > 3:  # Nom valide
                    project_name = potential_name
                    project_key = re.sub(r'[^a-zA-Z0-9]', '_', potential_name.lower())[:50]
        
        # Si toujours pas de projet identifié, utiliser un projet par défaut
        if not project_key:
            project_key = "default"
            project_name = project_name or "Projet principal"
        
        # Initialiser le projet s'il n'existe pas
        if project_key not in projects:
            projects[project_key] = {
                "questions": [],
                "answers": {},
                "project_name": project_name or f"Projet {project_key}"
            }
        
        # Ajouter la question et la réponse
        projects[project_key]["questions"].append(question)
        if answer:
            projects[project_key]["answers"][q_id] = answer
    
    return projects


@app.route("/agent3/<candidate_uuid>/save-responses", methods=["POST"])
def agent3_save_responses(candidate_uuid):
    """
    Sauvegarde les réponses aux questions générées par Agent 3.
    Extrait les liens, télécharge les images et sauvegarde tout dans la base de données.
    Groupe automatiquement les questions par projet et sauvegarde chaque projet séparément.
    
    Body (JSON):
        db_candidate_id: int (obligatoire)
        project_name: str (optionnel) - Nom du projet par défaut si un seul projet
        answers: dict (obligatoire) - {question_id: answer}
        questions: list (obligatoire) - Liste des questions avec leurs IDs
        projects_list: list (optionnel) - Liste des projets identifiés
    
    Returns:
        JSON avec le résultat de la sauvegarde (peut inclure plusieurs projets)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Body JSON requis"}), 400
        
        db_candidate_id = data.get("db_candidate_id")
        default_project_name = data.get("project_name")
        answers = data.get("answers", {})
        questions = data.get("questions", [])
        projects_list = data.get("projects_list", [])
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        if not answers:
            return jsonify({"error": "answers est requis (ne peut pas être vide)"}), 400
        
        # Importer les fonctions de sauvegarde
        from B2.chat.save_responses import save_project_responses, save_chat_responses_to_minio
        
        print(f"🔄 [Agent3] Sauvegarde des réponses pour candidate_uuid={candidate_uuid}")
        print(f"🔄 [Agent3] Nombre de questions: {len(questions)}, Nombre de réponses: {len(answers)}")
        
        # ✅ Sauvegarder toutes les réponses dans MinIO (une seule fois pour tous les projets)
        minio_success, minio_url, minio_error = save_chat_responses_to_minio(
            db_candidate_id, answers, questions, projects_list
        )
        if minio_success:
            print(f"✅ [Agent3] Réponses sauvegardées dans MinIO: {minio_url}")
        else:
            print(f"⚠️  [Agent3] Erreur sauvegarde MinIO (continuons quand même): {minio_error}")
        
        # Grouper les questions par projet
        projects_grouped = group_questions_by_project(questions, answers)
        
        print(f"🔄 [Agent3] Projets identifiés: {len(projects_grouped)}")
        for key, proj_data in projects_grouped.items():
            print(f"  - {key}: {len(proj_data['questions'])} questions, nom: {proj_data['project_name']}")
        
        # Sauvegarder chaque projet séparément
        saved_projects = []
        errors = []
        
        for project_key, proj_data in projects_grouped.items():
            project_name = proj_data["project_name"]
            project_answers = proj_data["answers"]
            project_questions = proj_data["questions"]
            
            # Si pas de nom de projet, utiliser le nom par défaut ou générer un nom
            if not project_name or project_name == f"Projet {project_key}" or project_name == "Projet principal":
                # Essayer d'extraire l'index du projet depuis la clé
                idx_match = re.search(r'(\d+)', project_key)
                if idx_match and projects_list and len(projects_list) > 0:
                    idx = int(idx_match.group(1))
                    # Les indices commencent généralement à 1 (proj1, proj2, etc.)
                    if idx > 0 and idx <= len(projects_list):
                        project_name = projects_list[idx - 1]
                    elif len(projects_list) == 1:
                        # Si un seul projet, l'utiliser
                        project_name = projects_list[0]
                
                # Si toujours pas de nom, utiliser le nom par défaut
                if not project_name or project_name == f"Projet {project_key}" or project_name == "Projet principal":
                    if default_project_name:
                        project_name = default_project_name
                    elif projects_list and len(projects_list) > 0:
                        # Utiliser le premier projet de la liste
                        project_name = projects_list[0]
                    else:
                        project_name = f"Projet {project_key}"
            
            print(f"💾 [Agent3] Sauvegarde du projet: {project_name}")
            
            success, project_id, error = save_project_responses(
                db_candidate_id,
                project_name,
                project_answers,
                project_questions,
                projects_list
            )
            
            if success:
                saved_projects.append({
                    "project_id": project_id,
                    "project_name": project_name,
                    "questions_count": len(project_questions)
                })
            else:
                errors.append({
                    "project_name": project_name,
                    "error": error
                })
        
        if errors and not saved_projects:
            # Toutes les sauvegardes ont échoué
            return jsonify({
                "success": False,
                "error": f"Erreurs lors de la sauvegarde: {', '.join([e['error'] for e in errors])}",
                "candidate_uuid": candidate_uuid,
                "db_candidate_id": db_candidate_id,
                "errors": errors
            }), 500
        
        return jsonify({
            "success": True,
            "candidate_uuid": candidate_uuid,
            "db_candidate_id": db_candidate_id,
            "projects_saved": len(saved_projects),
            "projects": saved_projects,
            "errors": errors if errors else None,
            "message": f"{len(saved_projects)} projet(s) sauvegardé(s) avec succès" + (f" ({len(errors)} erreur(s))" if errors else "")
        }), 200
        
    except Exception as e:
        print(f"❌ [Agent3] Erreur lors de la sauvegarde des réponses: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "candidate_uuid": candidate_uuid
        }), 500


@app.route("/agent3/<candidate_uuid>/get-chat-responses", methods=["GET"])
def agent3_get_chat_responses(candidate_uuid):
    """
    Récupère les réponses du chat depuis MinIO pour un candidat.
    
    Query params:
        db_candidate_id: int (obligatoire)
    
    Returns:
        JSON avec les réponses du chat
    """
    try:
        db_candidate_id = request.args.get("db_candidate_id", type=int)
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        
        from B2.chat.save_responses import get_chat_responses_from_minio
        
        success, chat_data, error = get_chat_responses_from_minio(db_candidate_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": error or "Impossible de récupérer les réponses"
            }), 404
        
        return jsonify({
            "success": True,
            "candidate_uuid": candidate_uuid,
            "db_candidate_id": db_candidate_id,
            "chat_data": chat_data
        }), 200
        
    except Exception as e:
        print(f"❌ [Agent3] Erreur lors de la récupération des réponses: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "candidate_uuid": candidate_uuid
        }), 500


@app.route("/agent3/<candidate_uuid>/upload-image", methods=["POST"])
def agent3_upload_image(candidate_uuid):
    """
    Upload une image directement (pas depuis une URL) pour un projet.
    
    Form Data:
        db_candidate_id: int (obligatoire)
        project_name: str (obligatoire)
        image: file (obligatoire) - Fichier image
    
    Returns:
        JSON avec l'URL MinIO de l'image
    """
    try:
        db_candidate_id = request.form.get("db_candidate_id")
        project_name = request.form.get("project_name")
        image_file = request.files.get("image")
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        if not project_name:
            return jsonify({"error": "project_name est requis"}), 400
        if not image_file:
            return jsonify({"error": "image est requis"}), 400
        
        # Lire le fichier
        image_bytes = image_file.read()
        
        # Déterminer l'extension
        filename = image_file.filename or 'image.jpg'
        extension = os.path.splitext(filename)[1] or '.jpg'
        
        # Nom de l'objet dans MinIO
        safe_project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)[:50]
        minio_prefix = get_candidate_minio_prefix(db_candidate_id)
        object_name = f"{minio_prefix}projects/{safe_project_name}/uploaded_{filename}"
        
        # Upload vers MinIO
        minio_storage = get_minio_storage()
        if not minio_storage or not minio_storage.client:
            return jsonify({"error": "Client MinIO non initialisé"}), 500
        
        content_type = image_file.content_type or 'image/jpeg'
        success, minio_url, error = _upload_to_minio_with_logging(
            minio_storage,
            image_bytes,
            object_name,
            content_type=content_type
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": error or "Erreur lors de l'upload vers MinIO"
            }), 500
        
        # Mettre à jour le projet dans la base de données
        try:
            from database.connection import DatabaseConnection
            DatabaseConnection.initialize()
            
            with DatabaseConnection.get_connection() as db:
                cursor = db.cursor()
                
                # Récupérer les images existantes
                cursor.execute(
                    "SELECT image_urls FROM candidate_projects WHERE candidate_id = %s AND project_name = %s",
                    (db_candidate_id, project_name)
                )
                result = cursor.fetchone()
                
                if result and result[0]:
                    existing_images = json.loads(result[0]) if isinstance(result[0], str) else result[0]
                    if not isinstance(existing_images, list):
                        existing_images = []
                else:
                    existing_images = []
                
                # Ajouter la nouvelle image
                existing_images.append(minio_url)
                
                # Mettre à jour
                cursor.execute(
                    """
                    UPDATE candidate_projects
                    SET image_urls = %s, updated_at = NOW()
                    WHERE candidate_id = %s AND project_name = %s
                    """,
                    (json.dumps(existing_images), db_candidate_id, project_name)
                )
                db.commit()
                cursor.close()
        except Exception as db_error:
            print(f"⚠️  Erreur lors de la mise à jour de la base de données: {db_error}")
            # On continue quand même, l'image est uploadée
        
        return jsonify({
            "success": True,
            "minio_url": minio_url,
            "object_name": object_name,
            "message": "Image uploadée avec succès"
        }), 200
        
    except Exception as e:
        print(f"❌ [Agent3] Erreur lors de l'upload d'image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/agent3/<candidate_uuid>/upload-media", methods=["POST"])
def agent3_upload_media(candidate_uuid):
    """
    Upload une image ou une vidéo directement pour un projet.
    
    Form Data:
        db_candidate_id: int (obligatoire)
        project_name: str (obligatoire)
        question_id: str (optionnel) - ID de la question associée
        media: file (obligatoire) - Fichier image ou vidéo
    
    Returns:
        JSON avec l'URL MinIO du média
    """
    try:
        db_candidate_id = request.form.get("db_candidate_id")
        project_name = request.form.get("project_name")
        question_id = request.form.get("question_id")
        media_file = request.files.get("media")
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        if not project_name:
            return jsonify({"error": "project_name est requis"}), 400
        if not media_file:
            return jsonify({"error": "media est requis"}), 400
        
        # Lire le fichier
        media_bytes = media_file.read()
        
        # Vérifier le type de fichier
        filename = media_file.filename or 'file'
        content_type = media_file.content_type or 'application/octet-stream'
        
        # Déterminer si c'est une image ou une vidéo
        is_image = content_type.startswith('image/')
        is_video = content_type.startswith('video/')
        
        # Vérifier aussi par extension
        extension = os.path.splitext(filename)[1].lower()
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp']
        video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv']
        
        if extension in image_extensions:
            is_image = True
        elif extension in video_extensions:
            is_video = True
        
        if not is_image and not is_video:
            return jsonify({
                "success": False,
                "error": "Le fichier doit être une image ou une vidéo"
            }), 400
        
        # Nom de l'objet dans MinIO
        safe_project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)[:50]
        timestamp = int(datetime.now().timestamp())
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)[:100]
        minio_prefix = get_candidate_minio_prefix(db_candidate_id)
        object_name = f"{minio_prefix}projects/{safe_project_name}/media_{timestamp}_{safe_filename}"
        
        # Upload vers MinIO
        minio_storage = get_minio_storage()
        if not minio_storage or not minio_storage.client:
            return jsonify({"error": "Client MinIO non initialisé"}), 500
        
        success, minio_url, error = _upload_to_minio_with_logging(
            minio_storage,
            media_bytes,
            object_name,
            content_type=content_type
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": error or "Erreur lors de l'upload vers MinIO"
            }), 500
        
        # Mettre à jour le projet dans la base de données
        try:
            from database.connection import DatabaseConnection
            DatabaseConnection.initialize()
            
            with DatabaseConnection.get_connection() as db:
                cursor = db.cursor()
                
                # Récupérer les images existantes
                cursor.execute(
                    "SELECT image_urls FROM candidate_projects WHERE candidate_id = %s AND project_name = %s",
                    (db_candidate_id, project_name)
                )
                result = cursor.fetchone()
                
                if result and result[0]:
                    existing_media = json.loads(result[0]) if isinstance(result[0], str) else result[0]
                    if not isinstance(existing_media, list):
                        existing_media = []
                else:
                    existing_media = []
                
                # Ajouter le nouveau média
                existing_media.append(minio_url)
                
                # Mettre à jour
                cursor.execute(
                    """
                    UPDATE candidate_projects
                    SET image_urls = %s, updated_at = NOW()
                    WHERE candidate_id = %s AND project_name = %s
                    """,
                    (json.dumps(existing_media), db_candidate_id, project_name)
                )
                db.commit()
                cursor.close()
        except Exception as db_error:
            print(f"⚠️  Erreur lors de la mise à jour de la base de données: {db_error}")
            # On continue quand même, le média est uploadé
        
        return jsonify({
            "success": True,
            "minio_url": minio_url,
            "object_name": object_name,
            "file_type": "image" if is_image else "video",
            "filename": filename,
            "message": f"{'Image' if is_image else 'Vidéo'} uploadée avec succès"
        }), 200
        
    except Exception as e:
        print(f"❌ [Agent3] Erreur lors de l'upload de média: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Erreur lors de l'upload: {str(e)}"
        }), 500


# ============================================================================
# ENDPOINTS CHATBOT PORTFOLIO (SIMPLE)
# ============================================================================

@app.route("/portfolio/start", methods=["POST"])
def start_portfolio_session():
    """
    Démarre une nouvelle session de chatbot portfolio.
    
    Body (JSON):
        candidate_id: int (obligatoire)
        extracted_data: dict (optionnel) - Données extraites du CV + Talent Card
    """
    try:
        data = request.get_json()
        candidate_id = data.get("candidate_id")
        extracted_data = data.get("extracted_data", {})
        
        if not candidate_id:
            return jsonify({"error": "candidate_id is required"}), 400
        
        from B2.chat.portfolio_session import PortfolioSession
        from B2.chat.question_logic import QuestionLogic
        
        # Créer la session
        session = PortfolioSession.create(candidate_id, extracted_data)
        
        # Obtenir la première question
        next_question = QuestionLogic.get_next_question(session)
        
        if next_question:
            question_key, question_text = next_question
            session.set_current_question(question_key, question_text)
        
        # Récupérer l'état
        state = session.get_state()
        
        return jsonify({
            "success": True,
            "session_id": session.session_id,
            "question": question_text if next_question else None,
            "is_complete": state["is_complete"],
            "profile": state["profile"],
            "missing_fields": state["missing_fields"]
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur démarrage session portfolio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/portfolio/<session_id>/message", methods=["POST"])
def send_portfolio_message(session_id):
    """
    Envoie un message (réponse) au chatbot et obtient la question suivante.
    
    Body (JSON):
        message: str (obligatoire) - Réponse de l'utilisateur
    """
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return jsonify({"error": "message is required"}), 400
        
        from B2.chat.portfolio_session import PortfolioSession
        from B2.chat.question_logic import QuestionLogic
        
        # Charger la session
        session = PortfolioSession.load(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        state = session.get_state()
        
        # Si la session est déjà complète, on ne pose plus de questions
        if state["is_complete"]:
            return jsonify({
                "success": True,
                "session_id": session_id,
                "question": None,
                "is_complete": True,
                "message": "Toutes les informations ont été collectées !",
                "profile": state["profile"]
            }), 200
        
        # Extraire l'information de la réponse
        current_question_key = state["current_question_key"]
        if current_question_key:
            extracted_data = QuestionLogic.extract_answer(current_question_key, user_message)
            
            # Mettre à jour le profil seulement si on a extrait des données valides
            if extracted_data:
                session.update_profile(extracted_data)
        
        # Obtenir la prochaine question
        next_question = QuestionLogic.get_next_question(session)
        
        if next_question:
            question_key, question_text = next_question
            session.set_current_question(question_key, question_text)
        
        # Récupérer l'état mis à jour
        updated_state = session.get_state()
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "question": question_text if next_question else None,
            "is_complete": updated_state["is_complete"],
            "profile": updated_state["profile"],
            "missing_fields": updated_state["missing_fields"],
            "filled_field": current_question_key if current_question_key else None
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur traitement message portfolio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/portfolio/<session_id>/state", methods=["GET"])
def get_portfolio_session_state(session_id):
    """
    Récupère l'état actuel d'une session de portfolio.
    """
    try:
        from B2.chat.portfolio_session import PortfolioSession
        
        session = PortfolioSession.load(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        state = session.get_state()
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "state": state
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur récupération état session: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/portfolio/<candidate_uuid>/generate", methods=["POST"])
def generate_portfolio(candidate_uuid):
    """
    Génère le contenu du portfolio à partir des réponses du chatbot et du CV.
    
    Body (JSON):
        db_candidate_id: int (obligatoire) - ID du candidat en base de données
        template_path: str (optionnel) - Chemin vers le template PPTX
        output_pptx: bool (optionnel) - Si True, génère aussi le fichier PPTX
    
    Returns:
        JSON avec le contenu du portfolio généré
    """
    try:
        data = request.get_json() or {}
        db_candidate_id = data.get("db_candidate_id")
        lang = (data.get("lang") or "fr").strip().lower()
        if lang not in ("fr", "en"):
            lang = "fr"
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        
        from B2.agent_portfolio import generate_portfolio_content
       
        
        print(f"🔄 Génération du portfolio pour candidate_uuid={candidate_uuid}, db_candidate_id={db_candidate_id}, lang={lang}")
        
        # Chemin pour sauvegarder le JSON
        output_json_path = os.path.join(
            GENERATED_FOLDER,
            f"portfolio_{candidate_uuid}_{db_candidate_id}.json"
        )
        
        # Générer le contenu du portfolio (dans la langue choisie) — portfolio long = CV original
        success, portfolio_data, error = generate_portfolio_content(
            db_candidate_id,
            output_json_path=output_json_path,
            use_original_cv=True,
            lang=lang
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": error or "Erreur lors de la génération du portfolio"
            }), 500
        
        # Récupérer l'URL de l'image du candidat depuis la base de données
        candidate_image_url = _get_candidate_image_url(db_candidate_id)
        if candidate_image_url:
            print(f"✅ Image candidat trouvée: {candidate_image_url}")
        
        # Préparer la réponse
        response_data = {
            "success": True,
            "candidate_uuid": candidate_uuid,
            "db_candidate_id": db_candidate_id,
            "portfolio_content": portfolio_data,
            "candidate_image_url": candidate_image_url,
            "json_path": output_json_path
        }
        
        # Upload du JSON vers MinIO
        try:
            minio_storage = get_minio_storage()
            with open(output_json_path, 'rb') as f:
                json_bytes = f.read()
            
            minio_prefix = get_candidate_minio_prefix(db_candidate_id)
            object_name = f"{minio_prefix}portfolio_{candidate_uuid}.json"
            success, url, _ = _upload_to_minio_with_logging(
                minio_storage,
                json_bytes,
                object_name,
                content_type="application/json"
            )
            
            if success:
                response_data["json_minio_url"] = url
        except Exception as e:
            print(f"⚠️  Erreur upload JSON vers MinIO: {e}")
        
        # Générer le PDF en arrière-plan après la génération du JSON
        try:
            from B2.agent_portfolio import transform_portfolio_data_for_template, convert_html_to_pdf
            from jinja2 import Template
            import threading
            
            def generate_pdf_background():
                """Génère le PDF en arrière-plan"""
                try:
                    print(f"🔄 [PDF Thread] Démarrage génération PDF en arrière-plan pour candidate_id={db_candidate_id}")
                    print(f"🔄 [PDF Thread] candidate_uuid={candidate_uuid}")
                    
                    # 1. Récupérer les données du candidat depuis la base de données
                    candidate_data = _get_candidate_info(
                        db_candidate_id,
                        ['image_minio_url', 'email', 'phone', 'titre_profil', 'annees_experience']
                    )
                    minio_image_url = candidate_data.get("image_minio_url")
                    candidate_img_url = _convert_minio_url_to_proxy(minio_image_url)
                    candidate_email = candidate_data.get("email")
                    candidate_phone = candidate_data.get("phone")
                    candidate_job_title = candidate_data.get("titre_profil")
                    candidate_years_experience = candidate_data.get("annees_experience")
                    
                    # 2. Transformer les données pour le template
                    template_data = transform_portfolio_data_for_template(
                        portfolio_data,
                        candidate_image_url=candidate_img_url,
                        candidate_email=candidate_email,
                        candidate_phone=candidate_phone,
                        candidate_job_title=candidate_job_title,
                        candidate_years_experience=candidate_years_experience
                    )
                    
                    # 3. Convertir les URLs MinIO des images de projets en URLs proxy
                    if template_data.get("candidate") and template_data["candidate"].get("projects"):
                        template_data["candidate"]["projects"] = _convert_project_images_to_proxy(
                            template_data["candidate"]["projects"]
                        )
                    
                    # 4. Charger le template HTML
                    # Essayer plusieurs chemins possibles (dans l'ordre de priorité)
                    possible_template_paths = [
                        "/app/frontend/src/portfolio html/portfolio_template.html",  # Copié dans le conteneur (priorité)
                        "/frontend/src/portfolio html/portfolio_template.html",  # Volume monté Docker
                        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "src", "portfolio html", "portfolio_template.html"),  # Depuis racine projet
                    ]
                    
                    template_path = None
                    css_path = None
                    
                    for tp in possible_template_paths:
                        if os.path.exists(tp):
                            template_path = tp
                            # Construire le chemin CSS correspondant
                            css_path = tp.replace("portfolio_template.html", "index.css")
                            if not os.path.exists(css_path):
                                # Essayer d'autres variantes pour le CSS
                                css_dir = os.path.dirname(tp)
                                css_path = os.path.join(css_dir, "index.css")
                            break
                    
                    if not template_path or not os.path.exists(template_path):
                        print(f"⚠️  [PDF Thread] Template HTML introuvable après avoir essayé:")
                        for tp in possible_template_paths:
                            exists = "✅" if os.path.exists(tp) else "❌"
                            print(f"  {exists} {tp}")
                        print(f"🔍 [PDF Thread] Répertoire courant: {os.getcwd()}")
                        print(f"🔍 [PDF Thread] __file__: {__file__}")
                        print(f"🔍 [PDF Thread] /frontend existe: {os.path.exists('/frontend')}")
                        if os.path.exists('/frontend'):
                            try:
                                print(f"🔍 [PDF Thread] Contenu de /frontend: {os.listdir('/frontend')}")
                            except Exception as e:
                                print(f"🔍 [PDF Thread] Erreur listdir /frontend: {e}")
                        if os.path.exists('/app'):
                            try:
                                print(f"🔍 [PDF Thread] Contenu de /app: {os.listdir('/app')[:10]}")
                            except Exception as e:
                                print(f"🔍 [PDF Thread] Erreur listdir /app: {e}")
                        return
                    
                    print(f"✅ [PDF Thread] Template trouvé: {template_path}")
                    
                    # 5. Lire et rendre le template
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
                    
                    jinja_template = Template(template_content)
                    html_content = jinja_template.render(
                        candidate=template_data.get('candidate', {}),
                        portfolio=template_data.get('portfolio', {}),
                        db_candidate_id=db_candidate_id,
                        candidate_uuid=candidate_uuid
                    )
                    
                    # 6. Injecter le CSS
                    if os.path.exists(css_path):
                        with open(css_path, 'r', encoding='utf-8') as f:
                            css_content = f.read()
                        html_content = html_content.replace(
                            '<link rel="stylesheet" href="/portfolio/static/index.css">',
                            f'<style>\n{css_content}\n</style>'
                        )
                    
                    # 7. Injecter les données JavaScript (comme dans /view)
                    candidate = template_data.get("candidate", {})
                    first_name = candidate.get("first_name", "")
                    last_name = candidate.get("last_name", "")
                    title_text = f"Portfolio - {first_name} {last_name}".strip()
                    if not title_text or title_text == "Portfolio -":
                        title_text = "Portfolio"
                    
                    data_injection_script = f"""
<script>
    window.portfolioData = {json.dumps(template_data, ensure_ascii=False)};
    window.dbCandidateId = {db_candidate_id};
    window.candidateUuid = "{candidate_uuid}";
    if (typeof populateTemplate === 'function') {{
        populateTemplate();
    }}
</script>
"""
                    html_content = html_content.replace('</body>', f'{data_injection_script}\n</body>')
                    html_content = re.sub(r'<title>.*?</title>', f'<title>{title_text}</title>', html_content, flags=re.DOTALL)
                    
                    # 7b. Sauvegarder le HTML dans MinIO (version long)
                    try:
                        from B2.generate_portfolio_html import save_portfolio_html
                        save_ok, html_url, save_err = save_portfolio_html(
                            html_content,
                            db_candidate_id,
                            candidate_uuid,
                            version="long",
                            lang=lang
                        )
                        if save_ok:
                            print(f"✅ [PDF Thread] HTML long sauvegardé dans MinIO: {html_url}")
                        else:
                            print(f"⚠️  [PDF Thread] Échec sauvegarde HTML MinIO: {save_err}")
                    except Exception as e:
                        print(f"⚠️  [PDF Thread] Exception sauvegarde HTML: {e}")
                    
                    # 8. Convertir le HTML en PDF
                    print(f"🔄 [PDF Thread] Appel de convert_html_to_pdf...")
                    pdf_success, pdf_url, pdf_error = convert_html_to_pdf(
                        html_content,
                        db_candidate_id,
                        candidate_uuid
                    )
                    
                    if pdf_success:
                        print(f"✅ [PDF Thread] PDF généré avec succès: {pdf_url}")
                        # Sauvegarder l'URL du PDF dans la base de données si la colonne existe
                        try:
                            from database.connection import DatabaseConnection
                            DatabaseConnection.initialize()
                            with DatabaseConnection.get_connection() as db:
                                cursor = db.cursor()
                                cursor.execute("""
                                    SELECT COLUMN_NAME 
                                    FROM INFORMATION_SCHEMA.COLUMNS 
                                    WHERE TABLE_SCHEMA = DATABASE() 
                                    AND TABLE_NAME = 'candidates' 
                                    AND COLUMN_NAME = 'portfolio_pdf_minio_url'
                                """)
                                if cursor.fetchone():
                                    cursor.execute(
                                        "UPDATE candidates SET portfolio_pdf_minio_url = %s WHERE id = %s",
                                        (pdf_url, db_candidate_id)
                                    )
                                    db.commit()
                                    print(f"✅ URL PDF sauvegardée en base de données")
                                cursor.close()
                        except Exception as e:
                            print(f"⚠️  Erreur sauvegarde URL PDF en base: {e}")
                    else:
                        print(f"❌ [PDF Thread] Erreur génération PDF: {pdf_error}")
                        
                except Exception as e:
                    print(f"❌ [PDF Thread] Erreur lors de la génération PDF en arrière-plan: {e}")
                    import traceback
                    traceback.print_exc()
                    print(f"❌ [PDF Thread] Stack trace complet:")
                    traceback.print_exc()
            
            # Démarrer la génération du PDF en arrière-plan
            pdf_thread = threading.Thread(target=generate_pdf_background, daemon=True)
            pdf_thread.start()
            print(f"🔄 Génération PDF démarrée en arrière-plan (thread ID: {pdf_thread.ident})")
        except Exception as e:
            print(f"❌ Erreur lors du démarrage de la génération PDF: {e}")
            import traceback
            traceback.print_exc()
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération du portfolio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/portfolio/<candidate_uuid>/regenerate", methods=["POST"])
def regenerate_portfolio(candidate_uuid):
    """
    Régénère le portfolio avec des modifications demandées par le candidat.
    
    Body (JSON):
        db_candidate_id: int (obligatoire) - ID du candidat en base de données
        modifications: str (obligatoire) - Modifications demandées par le candidat
    
    Returns:
        JSON avec le nouveau contenu du portfolio
    """
    try:
        data = request.get_json() or {}
        db_candidate_id = data.get("db_candidate_id")
        modifications = data.get("modifications", "").strip()
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        
        if not modifications:
            return jsonify({"error": "Les modifications sont requises"}), 400
        
        # Supprimer les anciennes versions du portfolio depuis MinIO avant régénération
        try:
            minio_storage = get_minio_storage()
            prefix = get_candidate_minio_prefix(db_candidate_id) + f"portfolio_{candidate_uuid}"
            objects_to_remove = [
                f"{prefix}.pdf",
                f"{prefix}_one-page.pdf",
                f"{prefix}.html",
                f"{prefix}_one-page.html",
            ]
            for object_name in objects_to_remove:
                del_ok, _ = minio_storage.delete_file(object_name)
                if del_ok:
                    print(f"🗑️ Ancien portfolio supprimé de MinIO: {object_name}")
        except Exception as e:
            print(f"⚠️ Suppression des anciens portfolios MinIO (non bloquant): {e}")
        
        from B2.agent_portfolio import generate_portfolio_content_with_feedback
        
        print(f"🔄 Régénération du portfolio pour candidate_uuid={candidate_uuid}")
        print(f"📝 Modifications demandées: {modifications}")
        
        # Chemin pour sauvegarder le JSON
        import time
        timestamp = int(time.time())
        output_json_path = os.path.join(
            GENERATED_FOLDER,
            f"portfolio_{candidate_uuid}_{db_candidate_id}_v{timestamp}.json"
        )
        
        # Régénérer le contenu du portfolio avec les modifications
        success, portfolio_data, error = generate_portfolio_content_with_feedback(
            db_candidate_id,
            feedback_modifications=modifications,
            output_json_path=output_json_path
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": error or "Erreur lors de la régénération du portfolio"
            }), 500
        
        # Récupérer l'URL de l'image du candidat
        candidate_image_url = _get_candidate_image_url(db_candidate_id)
        
        # Préparer la réponse
        response_data = {
            "success": True,
            "candidate_uuid": candidate_uuid,
            "db_candidate_id": db_candidate_id,
            "portfolio_content": portfolio_data,
            "candidate_image_url": candidate_image_url,
            "json_path": output_json_path,
            "modifications_applied": modifications
        }
        
        # Upload du JSON vers MinIO
        try:
            minio_storage = get_minio_storage()
            with open(output_json_path, 'rb') as f:
                json_bytes = f.read()
            
            object_name = f"{get_candidate_minio_prefix(db_candidate_id)}portfolio_{candidate_uuid}_v{timestamp}.json"
            success, url, _ = _upload_to_minio_with_logging(
                minio_storage,
                json_bytes,
                object_name,
                content_type="application/json"
            )
            
            if success:
                response_data["json_minio_url"] = url
        except Exception as e:
            print(f"⚠️  Erreur upload JSON vers MinIO: {e}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ Erreur lors de la régénération du portfolio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/portfolio/<candidate_uuid>/template-data", methods=["POST"])
def get_portfolio_template_data(candidate_uuid):
    """
    Retourne les données du portfolio transformées pour le template (format JSON).
    Le frontend utilisera ces données pour remplacer les placeholders dans le template HTML.
    
    Body (JSON):
        db_candidate_id: int (obligatoire) - ID du candidat en base de données
    
    Returns:
        JSON avec les données transformées pour le template
    """
    try:
        data = request.get_json() or {}
        db_candidate_id = data.get("db_candidate_id")
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        
        from B2.agent_portfolio import generate_portfolio_content, transform_portfolio_data_for_template
        
        print(f"🔄 Génération données template pour candidate_uuid={candidate_uuid}, db_candidate_id={db_candidate_id}")
        
        # 1. Générer le contenu du portfolio (JSON brut) — portfolio long = CV original
        success, portfolio_data, error = generate_portfolio_content(
            db_candidate_id,
            output_json_path=None,
            use_original_cv=True
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": error or "Erreur lors de la génération du portfolio"
            }), 500
        
        # 2. Récupérer les données du candidat depuis la base de données
        candidate_data = _get_candidate_info(
            db_candidate_id, 
            ['image_minio_url', 'titre_profil', 'annees_experience', 'email', 'phone']
        )
        # Convertir l'URL MinIO en URL proxy
        minio_image_url = candidate_data.get("image_minio_url")
        candidate_image_url = _convert_minio_url_to_proxy(minio_image_url)
        candidate_job_title = candidate_data.get("titre_profil")
        candidate_years_experience = candidate_data.get("annees_experience")
        candidate_email = candidate_data.get("email")
        candidate_phone = candidate_data.get("phone")
        
        # 3. Transformer les données pour le template
        template_data = transform_portfolio_data_for_template(
            portfolio_data,
            candidate_image_url=candidate_image_url,
            candidate_job_title=candidate_job_title,
            candidate_years_experience=candidate_years_experience,
            candidate_email=candidate_email,
            candidate_phone=candidate_phone
        )
        
        # 4. Retourner les données transformées
        return jsonify({
            "success": True,
            "template_data": template_data
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération des données template: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/portfolio/<candidate_uuid>/view", methods=["GET"])
def view_portfolio_html(candidate_uuid):
    """
    Retourne la page HTML du portfolio avec les données injectées.
    L'utilisateur sera redirigé vers cette page après la génération du portfolio.
    
    Query params:
        db_candidate_id: int (obligatoire) - ID du candidat en base de données
    
    Returns:
        HTML page with portfolio data injected
    """
    try:
        db_candidate_id = request.args.get("db_candidate_id", type=int)
        
        if not db_candidate_id:
            return "<h1>Erreur</h1><p>db_candidate_id est requis</p>", 400
        
        from B2.agent_portfolio import generate_portfolio_content, transform_portfolio_data_for_template
        
        print(f"🔄 Génération page HTML portfolio pour candidate_uuid={candidate_uuid}, db_candidate_id={db_candidate_id}")
        
        # 1. Générer le contenu du portfolio (JSON brut) — portfolio long = CV original
        success, portfolio_data, error = generate_portfolio_content(
            db_candidate_id,
            output_json_path=None,
            use_original_cv=True
        )
        
        if not success:
            return f"<h1>Erreur</h1><p>{error or 'Erreur lors de la génération du portfolio'}</p>", 500
        
        # 2. Récupérer les données du candidat depuis la base de données
        candidate_data = _get_candidate_info(
            db_candidate_id,
            ['image_minio_url', 'email', 'phone', 'titre_profil', 'disponibilite', 'linkedin', 'github', 'behance']
        )
        # Convertir l'URL MinIO en URL proxy
        minio_image_url = candidate_data.get("image_minio_url")
        candidate_image_url = _convert_minio_url_to_proxy(minio_image_url)
        candidate_email = candidate_data.get("email")
        candidate_phone = candidate_data.get("phone")
        
        # 3. Transformer les données pour le template
        template_data = transform_portfolio_data_for_template(
            portfolio_data,
            candidate_image_url=candidate_image_url,
            candidate_email=candidate_email,
            candidate_phone=candidate_phone,
            candidate_job_title=candidate_data.get("titre_profil")
        )
        
        # 3.1 Convertir les URLs MinIO des images de projets en URLs proxy
        if template_data.get("candidate") and template_data["candidate"].get("projects"):
            print(f"🔄 Conversion des URLs d'images pour {len(template_data['candidate']['projects'])} projets...")
            template_data["candidate"]["projects"] = _convert_project_images_to_proxy(
                template_data["candidate"]["projects"]
            )
        
        # 3.2 LinkedIn / GitHub / Behance : priorité à la base de données
        if template_data.get("candidate"):
            for db_key, template_key in [("linkedin", "linkedin_url"), ("github", "github_url"), ("behance", "behance_url")]:
                db_val = (candidate_data.get(db_key) or "").strip()
                if db_val:
                    template_data["candidate"][template_key] = db_val
            # 3.3 Poste cible : titre, type de contrat, disponibilité (choix du candidat au début)
            if (candidate_data.get("titre_profil") or "").strip():
                template_data["candidate"]["job_title"] = (candidate_data.get("titre_profil") or "").strip()
            if (candidate_data.get("disponibilite") or "").strip():
                template_data["candidate"]["availability"] = (candidate_data.get("disponibilite") or "").strip()
                template_data["candidate"]["disponibilite"] = template_data["candidate"]["availability"]
            contract_types = _get_candidate_contract_types(db_candidate_id)
            if contract_types:
                template_data["candidate"]["contract_type"] = ", ".join(contract_types)
                template_data["candidate"]["type_contrat"] = contract_types
            # Scores A2 : score global + justification (5 dimensions technique/comportemental), pas les soft skills déclarés
            try:
                from B2.generate_portfolio_html import _inject_scoring_into_candidate
                _inject_scoring_into_candidate(template_data["candidate"], db_candidate_id)
            except Exception as inj_err:
                print(f"⚠️ Injection scores A2 (vue portfolio long): {inj_err}")
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_path = os.path.join(project_root, "frontend", "src", "portfolio html", "portfolio_long_template.html")
        css_path = os.path.join(project_root, "frontend", "src", "portfolio html", "index.css")
        
        if not os.path.exists(template_path):
            return f"<h1>Erreur</h1><p>Template HTML introuvable: {template_path}</p>", 500
        
        # Lire le template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # URL de base pour les assets (icônes SVG, images) — avec domaine/public, utiliser RECRUIT_BASE_URL
        base_url = (os.getenv("RECRUIT_BASE_URL") or (request.url_root.rstrip("/") if request else None) or "http://localhost:5002").rstrip("/")
        if not base_url.startswith("http"):
            base_url = f"http://{base_url}"
        assets_base_url = base_url + "/portfolio/static/"
        
        # Rendre le template avec Jinja2
        print(f"🔄 Rendu du template avec Jinja2...")
        try:
            jinja_template = Template(template_content)
            html_content = jinja_template.render(
                candidate=template_data.get('candidate', {}),
                portfolio=template_data.get('portfolio', {}),
                db_candidate_id=db_candidate_id,
                candidate_uuid=candidate_uuid,
                assets_base_url=assets_base_url,
                portfolio_lang=request.args.get("lang", "fr")
            )
            print(f"✅ Template rendu avec succès avec Jinja2")
        except Exception as e:
            print(f"❌ Erreur lors du rendu Jinja2: {e}")
            import traceback
            traceback.print_exc()
            return f"<h1>Erreur</h1><p>Erreur lors du rendu du template: {str(e)}</p>", 500
        
        # Lire le CSS et l'injecter directement dans le HTML
        if os.path.exists(css_path):
            with open(css_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
            # Remplacer la balise <link> par une balise <style> avec le CSS
            html_content = html_content.replace(
                '<link rel="stylesheet" href="/portfolio/static/index.css">',
                f'<style>\n{css_content}\n</style>'
            )
        else:
            print(f"⚠️  Fichier CSS introuvable: {css_path}")
        
        # 5. Injecter les données dans le HTML
        # On ajoute un script qui injecte les données et appelle populateTemplate
        # Debug: Vérifier que les projets sont présents dans template_data
        projects_count = len(template_data.get("candidate", {}).get("projects", []))
        print(f"🔍 [View Portfolio] Nombre de projets dans template_data: {projects_count}")
        if projects_count > 0:
            print(f"🔍 [View Portfolio] Premier projet: {template_data['candidate']['projects'][0].get('title', 'N/A')}")
        else:
            print(f"⚠️  [View Portfolio] AUCUN PROJET dans template_data!")
            print(f"🔍 [View Portfolio] Structure de template_data: {list(template_data.keys())}")
            if "candidate" in template_data:
                print(f"🔍 [View Portfolio] Clés de candidate: {list(template_data['candidate'].keys())}")
        
        # Préparer le titre pour le JavaScript aussi
        candidate = template_data.get("candidate", {})
        first_name = candidate.get("first_name", "")
        last_name = candidate.get("last_name", "")
        title_text = f"Portfolio - {first_name} {last_name}".strip()
        if not title_text or title_text == "Portfolio -":
            title_text = "Portfolio"
        
        data_injection_script = f"""
<script>
    // Données du portfolio injectées par le backend
    const portfolioData = {json.dumps(template_data, ensure_ascii=False, indent=2)};
    
    // Mettre à jour le titre de la page immédiatement
    document.title = {json.dumps(title_text)};
    
    // Debug immédiat pour vérifier les projets
    console.log('🔍 [Backend Injection] Vérification des projets:', {{
        hasCandidate: !!portfolioData.candidate,
        hasProjects: !!portfolioData.candidate?.projects,
        projectsType: typeof portfolioData.candidate?.projects,
        projectsIsArray: Array.isArray(portfolioData.candidate?.projects),
        projectsLength: portfolioData.candidate?.projects?.length || 0,
        projectsPreview: portfolioData.candidate?.projects?.slice(0, 2) || 'N/A'
    }});
    
    // Attendre que le DOM soit chargé
    document.addEventListener('DOMContentLoaded', function() {{
        console.log('🔄 Injection des données du portfolio...');
        console.log('📦 Données injectées:', portfolioData);
        
        // S'assurer que le titre est à jour
        document.title = {json.dumps(title_text)};
        
        // Appeler la fonction populateTemplate qui existe déjà dans le template
        if (typeof populateTemplate === 'function') {{
            populateTemplate(portfolioData);
        }} else {{
            console.error('❌ Fonction populateTemplate non trouvée');
        }}
    }});
</script>
"""
        
        candidate = template_data.get("candidate", {})
        first_name = candidate.get("first_name", "")
        last_name = candidate.get("last_name", "")
        title_text = f"Portfolio - {first_name} {last_name}".strip()
        if not title_text or title_text == "Portfolio -":
            title_text = "Portfolio"
        title_pattern = r'<title>.*?</title>'
        html_content = re.sub(title_pattern, f'<title>{title_text}</title>', html_content, flags=re.DOTALL)
        
        # Injecter le script juste avant la fermeture du body
        html_content = html_content.replace('</body>', f'{data_injection_script}\n</body>')
        
        print(f"✅ Page HTML portfolio générée avec succès")
        
        # 6. Convertir automatiquement en PDF en arrière-plan
        try:
            from B2.agent_portfolio import convert_html_to_pdf
            import threading
            
            def generate_pdf_background():
                """Génère le PDF en arrière-plan"""
                try:
                    print(f"🔄 Démarrage génération PDF en arrière-plan pour candidate_id={db_candidate_id}")
                    success, pdf_url, error = convert_html_to_pdf(
                        html_content,
                        db_candidate_id,
                        candidate_uuid
                    )
                    if success:
                        print(f"✅ PDF généré avec succès: {pdf_url}")
                        # Optionnel: sauvegarder l'URL du PDF dans la base de données
                        # Note: La colonne portfolio_pdf_minio_url doit exister dans la table candidates
                        try:
                            from database.connection import DatabaseConnection
                            DatabaseConnection.initialize()
                            with DatabaseConnection.get_connection() as db:
                                cursor = db.cursor()
                                # Vérifier si la colonne existe avant de l'utiliser
                                cursor.execute("""
                                    SELECT COLUMN_NAME 
                                    FROM INFORMATION_SCHEMA.COLUMNS 
                                    WHERE TABLE_SCHEMA = DATABASE() 
                                    AND TABLE_NAME = 'candidates' 
                                    AND COLUMN_NAME = 'portfolio_pdf_minio_url'
                                """)
                                if cursor.fetchone():
                                    cursor.execute(
                                        "UPDATE candidates SET portfolio_pdf_minio_url = %s WHERE id = %s",
                                        (pdf_url, db_candidate_id)
                                    )
                                    db.commit()
                                    print(f"✅ URL PDF sauvegardée en base de données")
                                else:
                                    print(f"ℹ️  Colonne portfolio_pdf_minio_url n'existe pas, skip sauvegarde")
                                cursor.close()
                        except Exception as e:
                            print(f"⚠️  Erreur sauvegarde URL PDF en base: {e}")
                    else:
                        print(f"❌ Erreur génération PDF: {error}")
                except Exception as e:
                    print(f"❌ Erreur dans le thread de génération PDF: {e}")
            
            # Lancer la génération PDF en arrière-plan
            pdf_thread = threading.Thread(target=generate_pdf_background, daemon=True)
            pdf_thread.start()
            print(f"🔄 Thread de génération PDF lancé en arrière-plan")
            
        except Exception as e:
            print(f"⚠️  Erreur lors du démarrage de la génération PDF: {e}")
            # Continuer même si la génération PDF échoue
        
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération de la page HTML: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Erreur</h1><p>{str(e)}</p>", 500


@app.route("/portfolio/<candidate_uuid>/saved-html/<version>", methods=["GET"])
def get_portfolio_saved_html(candidate_uuid, version):
    """
    Retourne le portfolio HTML déjà sauvegardé dans MinIO (sans régénération).
    Query params: db_candidate_id (obligatoire), lang (optionnel, "fr" ou "en"), redirect (optionnel, "1" = redirection vers l'URL MinIO directe).
    Version: "one-page" ou "long".
    Retourne 404 si le fichier n'existe pas dans MinIO.
    """
    try:
        db_candidate_id = request.args.get("db_candidate_id", type=int)
        lang = (request.args.get("lang") or "fr").strip().lower()
        if lang not in ("fr", "en"):
            lang = "fr"
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        if version not in ["one-page", "long"]:
            return jsonify({"error": f"Version invalide: {version}"}), 400

        minio_storage = get_minio_storage()
        minio_prefix = get_candidate_minio_prefix(db_candidate_id)
        object_name_with_lang = f"{minio_prefix}portfolio_{candidate_uuid}_{version}_{lang}.html"
        object_name_fallback = f"{minio_prefix}portfolio_{candidate_uuid}_{version}.html"

        # Redirection vers l'URL proxy Flask (URL VPS utilisable par le navigateur, pas minio:9000)
        if request.args.get("redirect") == "1":
            if not minio_storage or not minio_storage.client:
                return jsonify({"error": "MinIO non disponible"}), 503
            flask_base_url = request.host_url.rstrip("/")
            if not flask_base_url.startswith("http"):
                flask_base_url = f"http://{flask_base_url}"
            proxy_url = f"{flask_base_url}/minio-proxy/{object_name_with_lang}"
            return redirect(proxy_url, code=302)

        success, file_bytes, error = minio_storage.download_file(object_name_with_lang)
        if not success or not file_bytes:
            success, file_bytes, error = minio_storage.download_file(object_name_fallback)
        if not success or not file_bytes:
            return jsonify({"error": "Version one-page non sauvegardée dans MinIO", "detail": error or "Fichier introuvable"}), 404

        html_content = file_bytes.decode("utf-8")
        # Injecter le favicon TAP pour que l'onglet affiche l'icône TAP
        favicon_tag = '<link rel="icon" type="image/svg+xml" href="/TapIcon.svg">'
        if "</head>" in html_content and "TapIcon.svg" not in html_content:
            html_content = html_content.replace("</head>", f"{favicon_tag}\n</head>", 1)
        return html_content, 200, {"Content-Type": "text/html; charset=utf-8"}
    except Exception as e:
        print(f"❌ Erreur récupération HTML sauvegardé: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/portfolio/<candidate_uuid>/html/<version>", methods=["GET"])
def get_portfolio_html(candidate_uuid, version):
    """
    Génère et retourne le portfolio HTML dans la version demandée.
    
    Query params:
        db_candidate_id: int (obligatoire) - ID du candidat en base de données
    
    Path params:
        version: "one-page" ou "long" - Version du portfolio à générer
    
    Returns:
        HTML content ou erreur JSON
    """
    try:
        db_candidate_id = request.args.get("db_candidate_id", type=int)
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        
        if version not in ["one-page", "long"]:
            return jsonify({"error": f"Version invalide: {version}. Utilisez 'one-page' ou 'long'"}), 400
        
        from B2.generate_portfolio_html import generate_portfolio_html
        
        # Récupérer les données du candidat depuis la base de données
        candidate_data = _get_candidate_info(
            db_candidate_id,
            ['image_minio_url', 'email', 'phone', 'titre_profil', 'annees_experience', 'linkedin', 'github']
        )
        
        # Convertir l'URL MinIO en URL proxy
        minio_image_url = candidate_data.get("image_minio_url")
        candidate_image_url = _convert_minio_url_to_proxy(minio_image_url) if minio_image_url else None
        candidate_email = candidate_data.get("email")
        candidate_phone = candidate_data.get("phone")
        candidate_job_title = candidate_data.get("titre_profil")
        candidate_years_experience = candidate_data.get("annees_experience")
        candidate_linkedin_url = (candidate_data.get("linkedin") or "").strip() or None
        candidate_github_url = (candidate_data.get("github") or "").strip() or None
        
        print(f"🔄 Génération portfolio HTML (version: {version}) pour candidate_uuid={candidate_uuid}, db_candidate_id={db_candidate_id}")
        
        # Obtenir l'URL de base Flask pour les proxies (RECRUIT_BASE_URL pour domaine ex: https://demo.tap-hr.com/api)
        flask_base_url = (os.getenv("RECRUIT_BASE_URL") or request.host_url or "http://localhost:5002").rstrip('/')
        if not flask_base_url.startswith('http'):
            flask_base_url = f"http://{flask_base_url}"
        
        # Langue : query param ?lang=en ou ?lang=fr (défaut fr)
        lang_param = (request.args.get("lang") or "fr").strip().lower()
        if lang_param not in ("fr", "en"):
            lang_param = "fr"

        # Générer le HTML
        success, html_content, error = generate_portfolio_html(
            candidate_id=db_candidate_id,
            version=version,
            candidate_image_url=candidate_image_url,
            candidate_email=candidate_email,
            candidate_phone=candidate_phone,
            candidate_job_title=candidate_job_title,
            candidate_years_experience=candidate_years_experience,
            flask_base_url=flask_base_url,
            candidate_uuid=candidate_uuid,
            candidate_linkedin_url=candidate_linkedin_url,
            candidate_github_url=candidate_github_url,
            lang=lang_param
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": error or "Erreur lors de la génération du portfolio HTML"
            }), 500
        
        # Convertir les URLs MinIO des images de projets en URLs proxy
        # (le HTML généré contient déjà les URLs, mais on peut les post-traiter si nécessaire)
        
        # Générer le PDF en arrière-plan pour la version one-page aussi
        try:
            from B2.agent_portfolio import convert_html_to_pdf
            import threading
            
            def generate_pdf_background():
                """Génère le PDF en arrière-plan pour la version one-page"""
                try:
                    print(f"🔄 [PDF Thread One-Page] Démarrage génération PDF en arrière-plan pour candidate_id={db_candidate_id}")
                    # Utiliser le HTML déjà généré, même taille de page 1920×1080 pour contenu complet
                    pdf_success, pdf_url, pdf_error = convert_html_to_pdf(
                        html_content,
                        db_candidate_id,
                        candidate_uuid,
                        pdf_page_format="one-page"
                    )
                    
                    if pdf_success:
                        _portfolio_pdf_generated_at[(db_candidate_id, "one-page")] = _time.time()
                        print(f"✅ [PDF Thread One-Page] PDF généré avec succès: {pdf_url}")
                        # Sauvegarder l'URL du PDF dans la base de données si la colonne existe
                        try:
                            from database.connection import DatabaseConnection
                            DatabaseConnection.initialize()
                            with DatabaseConnection.get_connection() as db:
                                cursor = db.cursor()
                                cursor.execute("""
                                    SELECT COLUMN_NAME 
                                    FROM INFORMATION_SCHEMA.COLUMNS 
                                    WHERE TABLE_SCHEMA = DATABASE() 
                                    AND TABLE_NAME = 'candidates' 
                                    AND COLUMN_NAME = 'portfolio_pdf_minio_url'
                                """)
                                if cursor.fetchone():
                                    cursor.execute(
                                        "UPDATE candidates SET portfolio_pdf_minio_url = %s WHERE id = %s",
                                        (pdf_url, db_candidate_id)
                                    )
                                    db.commit()
                                    print(f"✅ URL PDF sauvegardée en base de données")
                                cursor.close()
                        except Exception as e:
                            print(f"⚠️  Erreur sauvegarde URL PDF en base: {e}")
                    else:
                        print(f"❌ [PDF Thread One-Page] Erreur génération PDF: {pdf_error}")
                except Exception as e:
                    print(f"❌ [PDF Thread One-Page] Erreur lors de la génération PDF: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Démarrer la génération du PDF en arrière-plan
            pdf_thread = threading.Thread(target=generate_pdf_background, daemon=True)
            pdf_thread.start()
            print(f"🔄 Génération PDF one-page démarrée en arrière-plan")
        except Exception as e:
            print(f"⚠️  Erreur lors du démarrage de la génération PDF one-page: {e}")
            # Ne pas bloquer la réponse HTML même si le PDF échoue
        
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération du portfolio HTML: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/portfolio/<candidate_uuid>/generate-html", methods=["POST"])
def generate_portfolio_html_endpoint(candidate_uuid):
    """
    Génère et sauvegarde le portfolio HTML dans MinIO.
    
    Body (JSON):
        db_candidate_id: int (obligatoire) - ID du candidat en base de données
        version: str (optionnel, défaut: "one-page") - Version du portfolio ("one-page" ou "long")
        save_to_minio: bool (optionnel, défaut: true) - Si True, sauvegarde dans MinIO
    
    Returns:
        JSON avec le HTML généré et l'URL MinIO si sauvegardé
    """
    try:
        data = request.get_json() or {}
        db_candidate_id = data.get("db_candidate_id")
        version = data.get("version", "one-page")
        save_to_minio = data.get("save_to_minio", True)
        lang = (data.get("lang") or "fr").strip().lower()
        if lang not in ("fr", "en"):
            lang = "fr"
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        
        if version not in ["one-page", "long"]:
            return jsonify({"error": f"Version invalide: {version}. Utilisez 'one-page' ou 'long'"}), 400
        
        from B2.generate_portfolio_html import generate_and_save_portfolio_html
        
        # Récupérer les données du candidat depuis la base de données
        candidate_data = _get_candidate_info(
            db_candidate_id,
            ['image_minio_url', 'email', 'phone', 'titre_profil', 'annees_experience', 'disponibilite', 'linkedin', 'github', 'behance']
        )
        
        # Convertir l'URL MinIO en URL proxy
        minio_image_url = candidate_data.get("image_minio_url")
        candidate_image_url = _convert_minio_url_to_proxy(minio_image_url) if minio_image_url else None
        candidate_email = candidate_data.get("email")
        candidate_phone = candidate_data.get("phone")
        candidate_job_title = candidate_data.get("titre_profil")
        candidate_years_experience = candidate_data.get("annees_experience")
        candidate_availability = (candidate_data.get("disponibilite") or "").strip() or None
        candidate_contract_type = ", ".join(_get_candidate_contract_types(db_candidate_id)) or None
        candidate_linkedin_url = (candidate_data.get("linkedin") or "").strip() or None
        candidate_github_url = (candidate_data.get("github") or "").strip() or None
        candidate_behance_url = (candidate_data.get("behance") or "").strip() or None
        
        print(f"🔄 Génération et sauvegarde portfolio HTML (version: {version}) pour candidate_uuid={candidate_uuid}, db_candidate_id={db_candidate_id}")
        
        # Pour la version "long", utiliser le même template que la vue (évite d'enregistrer l'ancien template dans MinIO)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        long_template_path = os.path.join(project_root, "frontend", "src", "portfolio html", "portfolio_long_template.html") if version == "long" else None
        
        # Obtenir l'URL de base Flask pour les proxies (RECRUIT_BASE_URL pour domaine ex: https://demo.tap-hr.com/api)
        flask_base_url = (os.getenv("RECRUIT_BASE_URL") or request.host_url or "http://localhost:5002").rstrip('/')
        if not flask_base_url.startswith('http'):
            flask_base_url = f"http://{flask_base_url}"
        
        from B2.generate_portfolio_html import generate_portfolio_html, save_portfolio_html
        
        # Générer le HTML (avec langue pour contenu + libellés)
        success, html_content, error = generate_portfolio_html(
            candidate_id=db_candidate_id,
            version=version,
            candidate_image_url=candidate_image_url,
            candidate_email=candidate_email,
            candidate_phone=candidate_phone,
            candidate_job_title=candidate_job_title,
            candidate_years_experience=candidate_years_experience,
            candidate_availability=candidate_availability,
            candidate_contract_type=candidate_contract_type,
            flask_base_url=flask_base_url,
            candidate_uuid=candidate_uuid,
            candidate_linkedin_url=candidate_linkedin_url,
            candidate_github_url=candidate_github_url,
            candidate_behance_url=candidate_behance_url,
            long_template_path=long_template_path,
            lang=lang
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": error or "Erreur lors de la génération du portfolio HTML"
            }), 500
        
        # Sauvegarder le HTML dans MinIO si demandé (one-page et long)
        minio_url = None
        html_minio_url = None
        if save_to_minio:
            save_success, html_minio_url, save_error = save_portfolio_html(
                html_content,
                db_candidate_id,
                candidate_uuid,
                version,
                lang=lang
            )
            minio_url = html_minio_url
            if save_success:
                print(f"✅ Portfolio HTML ({version}, {lang}) sauvegardé dans MinIO: {html_minio_url}")
            else:
                print(f"⚠️  Erreur sauvegarde HTML dans MinIO ({version}): {save_error}")
        
        # Lancer la génération du PDF en arrière-plan (pour que GET /pdf trouve le fichier après quelques secondes)
        try:
            import threading
            from B2.agent_portfolio import convert_html_to_pdf

            def _generate_pdf_background():
                try:
                    print(f"🔄 [PDF] Génération PDF en arrière-plan (version={version}, lang={lang})...")
                    pdf_page_format = "one-page" if version == "one-page" else None
                    pdf_success, pdf_url, pdf_error = convert_html_to_pdf(
                        html_content,
                        db_candidate_id,
                        candidate_uuid,
                        base_url=flask_base_url,
                        pdf_page_format=pdf_page_format,
                        lang=lang
                    )
                    if pdf_success:
                        _portfolio_pdf_generated_at[(db_candidate_id, version, lang)] = _time.time()
                        _portfolio_pdf_generated_at[(db_candidate_id, version)] = _time.time()  # rétrocompat
                        print(f"✅ [PDF] PDF généré et uploadé: {pdf_url}")
                    else:
                        print(f"❌ [PDF] Erreur: {pdf_error}")
                except Exception as e:
                    print(f"❌ [PDF] Exception: {e}")
                    import traceback
                    traceback.print_exc()

            threading.Thread(target=_generate_pdf_background, daemon=True).start()
            print(f"🔄 [PDF] Thread de génération PDF lancé (version={version}, lang={lang})")
        except Exception as e:
            print(f"⚠️ [PDF] Démarrage thread PDF échoué: {e}")

        # Générer et enregistrer l'autre langue (FR/EN) en arrière-plan pour one-page et long
        _other_lang = "en" if lang == "fr" else "fr"
        def _generate_other_lang_background():
            import time as _time2
            try:
                print(f"🔄 [PDF] Génération de l'autre langue ({_other_lang}, version={version}) en arrière-plan...")
                success_other, html_other, error_other = generate_portfolio_html(
                    candidate_id=db_candidate_id,
                    version=version,
                    candidate_image_url=candidate_image_url,
                    candidate_email=candidate_email,
                    candidate_phone=candidate_phone,
                    candidate_job_title=candidate_job_title,
                    candidate_years_experience=candidate_years_experience,
                    candidate_availability=candidate_availability,
                    candidate_contract_type=candidate_contract_type,
                    flask_base_url=flask_base_url,
                    candidate_uuid=candidate_uuid,
                    candidate_linkedin_url=candidate_linkedin_url,
                    candidate_github_url=candidate_github_url,
                    candidate_behance_url=candidate_behance_url,
                    long_template_path=long_template_path if version == "long" else None,
                    lang=_other_lang
                )
                if not success_other:
                    print(f"❌ [PDF] Génération HTML {_other_lang} échouée: {error_other}")
                    return
                if save_to_minio:
                    save_success, minio_url_other, _ = save_portfolio_html(
                        html_other, db_candidate_id, candidate_uuid, version, lang=_other_lang
                    )
                    if save_success:
                        print(f"✅ [PDF] HTML {_other_lang} sauvegardé dans MinIO: {minio_url_other}")
                pdf_page_format = "one-page" if version == "one-page" else None
                pdf_success, pdf_url_other, pdf_error = convert_html_to_pdf(
                    html_other,
                    db_candidate_id,
                    candidate_uuid,
                    base_url=flask_base_url,
                    pdf_page_format=pdf_page_format,
                    lang=_other_lang
                )
                if pdf_success:
                    _portfolio_pdf_generated_at[(db_candidate_id, version, _other_lang)] = _time2.time()
                    print(f"✅ [PDF] PDF {_other_lang} généré et uploadé: {pdf_url_other}")
                else:
                    print(f"❌ [PDF] Erreur PDF {_other_lang}: {pdf_error}")
            except Exception as e2:
                print(f"❌ [PDF] Exception génération autre langue ({_other_lang}): {e2}")
                import traceback
                traceback.print_exc()
        try:
            threading.Thread(target=_generate_other_lang_background, daemon=True).start()
            print(f"🔄 [PDF] Thread autre langue ({_other_lang}, version={version}) lancé")
        except Exception as e2:
            print(f"⚠️ [PDF] Démarrage thread autre langue échoué: {e2}")
        
        return jsonify({
            "success": True,
            "version": version,
            "html_content": html_content,
            "minio_url": minio_url,
            "html_minio_url": html_minio_url,
            "message": f"Portfolio HTML généré avec succès (version: {version})"
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération du portfolio HTML: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/portfolio/<candidate_uuid>/pdf-status", methods=["GET"])
def get_portfolio_pdf_status(candidate_uuid):
    """
    Indique si le PDF portfolio est prêt et son timestamp de génération.
    Permet au frontend d'attendre le nouveau PDF après une régénération (éviter d'afficher l'ancien).
    
    Query params:
        db_candidate_id: int (obligatoire)
        version: str (optionnel) - "long" ou "one-page". Défaut: "long".
        lang: str (optionnel) - "fr" ou "en" pour la version linguistique du PDF.
    
    Returns:
        JSON { "ready": true, "generated_at": <unix timestamp> } ou { "ready": false }
    """
    try:
        db_candidate_id = request.args.get("db_candidate_id", type=int)
        version = (request.args.get("version") or "long").strip().lower()
        if version not in ("long", "one-page"):
            version = "long"
        lang = (request.args.get("lang") or "").strip().lower()
        if lang not in ("fr", "en"):
            lang = None
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        lang_suffix = f"_{lang}" if lang else ""
        key = (db_candidate_id, version, lang) if lang else (db_candidate_id, version)
        key_legacy = (db_candidate_id, version)
        if key in _portfolio_pdf_generated_at:
            return jsonify({
                "ready": True,
                "generated_at": _portfolio_pdf_generated_at[key]
            })
        if not lang and key_legacy in _portfolio_pdf_generated_at:
            return jsonify({
                "ready": True,
                "generated_at": _portfolio_pdf_generated_at[key_legacy]
            })
        from minio_storage import get_minio_storage
        minio_storage = get_minio_storage()
        minio_prefix = get_candidate_minio_prefix(db_candidate_id)
        if version == "one-page":
            object_name = f"{minio_prefix}portfolio_{candidate_uuid}_one-page{lang_suffix}.pdf"
        else:
            object_name = f"{minio_prefix}portfolio_{candidate_uuid}{lang_suffix}.pdf"
        success, _, _ = minio_storage.download_file(object_name)
        if success:
            return jsonify({
                "ready": True,
                "generated_at": _portfolio_pdf_generated_at.get(key, _portfolio_pdf_generated_at.get(key_legacy, 0))
            })
        return jsonify({"ready": False})
    except Exception as e:
        return jsonify({"ready": False, "error": str(e)}), 500


@app.route("/portfolio/<candidate_uuid>/pdf", methods=["GET"])
def get_portfolio_pdf(candidate_uuid):
    """
    Retourne le PDF du portfolio s'il existe.
    Sans ?raw=1 : retourne une page HTML (favicon TAP + iframe) pour que l'onglet affiche l'icône TAP.
    Avec ?raw=1 : retourne le PDF brut (pour l'iframe).
    
    Query params:
        db_candidate_id: int (obligatoire) - ID du candidat en base de données
        version: str (optionnel) - "long" ou "one-page". Défaut: "long".
        lang: str (optionnel) - "fr" ou "en" pour la version linguistique du PDF.
    """
    if not request.args.get("raw"):
        pdf_url = _build_pdf_preview_url()
        return _pdf_preview_html_wrapper("Portfolio - Aperçu", pdf_url)
    try:
        db_candidate_id = request.args.get("db_candidate_id", type=int)
        version = request.args.get("version", "long").strip().lower()
        if version not in ("long", "one-page"):
            version = "long"
        lang = (request.args.get("lang") or "").strip().lower()
        if lang not in ("fr", "en"):
            lang = None
        
        if not db_candidate_id:
            return jsonify({"error": "db_candidate_id est requis"}), 400
        
        from minio_storage import get_minio_storage
        minio_storage = get_minio_storage()
        minio_prefix = get_candidate_minio_prefix(db_candidate_id)

        # Construire la liste des noms possibles (comme _get_portfolio_pdf_bytes) pour éviter 404
        # quand le fichier existe avec un suffixe langue (_fr, _en) mais que l'URL n'a pas ?lang=
        if version == "one-page":
            candidates = [
                f"{minio_prefix}portfolio_{candidate_uuid}_one-page.pdf",
                f"{minio_prefix}portfolio_{candidate_uuid}_one-page_fr.pdf",
                f"{minio_prefix}portfolio_{candidate_uuid}_one-page_en.pdf",
            ]
        else:
            candidates = [
                f"{minio_prefix}portfolio_{candidate_uuid}.pdf",
                f"{minio_prefix}portfolio_{candidate_uuid}_fr.pdf",
                f"{minio_prefix}portfolio_{candidate_uuid}_en.pdf",
            ]
        # Si une langue est demandée, on met sa variante en premier
        if lang:
            lang_suffix = f"_{lang}"
            if version == "one-page":
                preferred = f"{minio_prefix}portfolio_{candidate_uuid}_one-page{lang_suffix}.pdf"
            else:
                preferred = f"{minio_prefix}portfolio_{candidate_uuid}{lang_suffix}.pdf"
            if preferred not in candidates:
                candidates.insert(0, preferred)
            else:
                candidates = [preferred] + [c for c in candidates if c != preferred]

        success, pdf_bytes, error = False, None, None
        object_name = None
        for candidate_name in candidates:
            success, pdf_bytes, error = minio_storage.download_file(candidate_name)
            if success and pdf_bytes:
                object_name = candidate_name
                break

        if not success:
            user_message = "Ce fichier n'est pas encore genere. Veuillez reessayer dans quelques instants."
            # Par défaut on renvoie une page HTML design pour le navigateur.
            # Le JSON reste disponible via ?format=json (ou client API strict JSON).
            accept_header = (request.headers.get("Accept") or "").lower()
            wants_json = (
                (request.args.get("format") or "").strip().lower() == "json"
                or ("application/json" in accept_header and "text/html" not in accept_header)
            )
            if not wants_json:
                retry_url = request.url
                html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fichier en preparation</title>
  <link rel="icon" type="image/svg+xml" href="/TapIcon.svg">
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #f5f6f8;
      color: #1f2937;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }}
    .card {{
      width: 100%;
      max-width: 520px;
      background: #fff;
      border-radius: 14px;
      padding: 22px 18px;
      box-shadow: 0 8px 30px rgba(0, 0, 0, .08);
      border: 1px solid #eceef2;
      text-align: center;
    }}
    .badge {{
      display: inline-block;
      margin-bottom: 10px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .3px;
      text-transform: uppercase;
      color: #b91c1c;
      background: #fee2e2;
      padding: 6px 10px;
      border-radius: 999px;
    }}
    h1 {{ font-size: 1.15rem; margin: 0 0 .55rem 0; }}
    p {{ margin: 0 0 .95rem 0; line-height: 1.45; color: #4b5563; }}
    .actions {{ display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 14px; }}
    .btn {{
      display: inline-block;
      text-decoration: none;
      border-radius: 10px;
      padding: 10px 14px;
      font-weight: 700;
      font-size: 14px;
      border: 1px solid transparent;
    }}
    .btn-primary {{ background: #b91c1c; color: #fff; }}
    .btn-secondary {{ background: #fff; color: #374151; border-color: #d1d5db; }}
  </style>
</head>
<body>
  <div class="card">
    <span class="badge">Patientez</span>
    <h1>Le fichier n est pas encore disponible</h1>
    <p>{user_message}</p>
    <div class="actions">
      <a class="btn btn-primary" href="{retry_url}">Reessayer</a>
      <a class="btn btn-secondary" href="javascript:history.back()">Retour</a>
    </div>
  </div>
</body>
</html>"""
                return html, 404, {"Content-Type": "text/html; charset=utf-8"}

            # API/JSON: message utilisateur uniquement (sans details techniques MinIO)
            return jsonify({
                "error": "fichier_non_genere",
                "message": user_message
            }), 404
        
        from flask import Response
        filename = f"portfolio_{candidate_uuid}{f'_{lang}' if lang else ''}.pdf"
        headers = {
            'Content-Disposition': f'inline; filename={filename}',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        key = (db_candidate_id, version, lang) if lang else (db_candidate_id, version)
        gen_at = _portfolio_pdf_generated_at.get(key) or _portfolio_pdf_generated_at.get((db_candidate_id, version))
        if gen_at is not None:
            headers['X-PDF-Generated-At'] = str(int(gen_at))
        return Response(pdf_bytes, mimetype='application/pdf', headers=headers)
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du PDF: {e}")
        return jsonify({"error": str(e)}), 500



@app.route("/recruit/static/<path:filename>", methods=["GET"])
def serve_recruit_static(filename):
    """
    Sert les fichiers statiques de la page recruteur (images de fond, etc.) depuis le répertoire backend.
    """
    try:
        backend_dir = _BACKEND_DIR
        static_path = os.path.join(backend_dir, filename)
        if not os.path.abspath(static_path).startswith(os.path.abspath(backend_dir)):
            return "Accès non autorisé", 403
        if not os.path.exists(static_path):
            return f"Fichier introuvable: {filename}", 404
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
        }
        ext = os.path.splitext(filename)[1].lower()
        content_type = mime_types.get(ext, "application/octet-stream")
        return send_file(static_path, mimetype=content_type)
    except Exception as e:
        print(f"❌ Erreur serve_recruit_static {filename}: {e}")
        return f"Erreur: {str(e)}", 500


@app.route("/portfolio/static/<path:filename>", methods=["GET"])
def serve_portfolio_static(filename):
    """
    Sert les fichiers statiques du portfolio (CSS, images, etc.)
    """
    try:
        # Obtenir le répertoire racine du projet
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        static_path = os.path.join(project_root, "frontend", "src", "portfolio html", filename)
        
        # Sécurité : vérifier que le fichier est dans le bon répertoire
        static_dir = os.path.join(project_root, "frontend", "src", "portfolio html")
        if not os.path.abspath(static_path).startswith(os.path.abspath(static_dir)):
            return "Accès non autorisé", 403
        
        if not os.path.exists(static_path):
            return f"Fichier introuvable: {filename}", 404
        
        # Déterminer le type MIME
        mime_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
        }
        ext = os.path.splitext(filename)[1].lower()
        content_type = mime_types.get(ext, 'application/octet-stream')
        
        return send_file(static_path, mimetype=content_type)
        
    except Exception as e:
        print(f"❌ Erreur lors du service du fichier statique {filename}: {e}")
        return f"Erreur: {str(e)}", 500


@app.route("/talent/static/<path:filename>", methods=["GET"])
def serve_talent_static(filename):
    """
    Sert les fichiers statiques de la Talent Card (SVG, images de fond, QR, etc.)
    depuis frontend/src/talent card html/.
    Requis pour que les icônes et images s'affichent quand l'app est derrière un proxy (ex: https://demo.tap-hr.com).
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        static_dir = os.path.join(project_root, "frontend", "src", "talent card html")
        static_path = os.path.join(static_dir, filename)
        if not os.path.abspath(static_path).startswith(os.path.abspath(static_dir)):
            return "Accès non autorisé", 403
        if not os.path.exists(static_path):
            return f"Fichier introuvable: {filename}", 404
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
        }
        ext = os.path.splitext(filename)[1].lower()
        content_type = mime_types.get(ext, "application/octet-stream")
        return send_file(static_path, mimetype=content_type)
    except Exception as e:
        print(f"❌ Erreur serve_talent_static {filename}: {e}")
        return f"Erreur: {str(e)}", 500


@app.route("/static/TapIcon.svg", methods=["GET"])
@app.route("/TapIcon.svg", methods=["GET"])
def serve_tap_favicon():
    """Sert le favicon TAP pour les pages d'aperçu (CV, Talent Card) afin que l'onglet affiche l'icône TAP."""
    try:
        icon_path = os.path.join(_PROJECT_ROOT, "frontend", "public", "TapIcon.svg")
        if not os.path.exists(icon_path):
            return "Favicon introuvable", 404
        return send_file(icon_path, mimetype="image/svg+xml")
    except Exception as e:
        print(f"❌ Erreur serve_tap_favicon: {e}")
        return "Erreur", 500


def _build_pdf_preview_url():
    """
    Construit l'URL du PDF pour l'iframe (avec raw=1).
    En HTTPS derrière Nginx : utilise X-Forwarded-Proto et préfixe /api pour éviter Mixed Content.
    """
    scheme = "https" if request.headers.get("X-Forwarded-Proto") == "https" else request.scheme
    # Derrière le proxy Nginx, le backend reçoit le chemin sans /api ; le navigateur doit appeler /api/...
    if request.headers.get("X-Forwarded-Proto"):
        base_path = "/api" + request.path
    else:
        base_path = request.path
    # request.query_string peut être bytes (WSGI) → toujours convertir en str
    qs = request.query_string
    if qs:
        qs_str = qs.decode("utf-8") if isinstance(qs, bytes) else str(qs)
        query = "?" + qs_str
        raw_sep = "&"
    else:
        query = ""
        raw_sep = "?"
    return f"{scheme}://{request.host}{base_path}{query}{raw_sep}raw=1"


def _pdf_preview_html_wrapper(title: str, pdf_url: str) -> str:
    """Retourne une page HTML avec favicon TAP et iframe pour afficher le PDF (évite l'icône par défaut dans l'onglet)."""
    # /TapIcon.svg : en production (proxy) = frontend ; en standalone = backend (route ci-dessus)
    favicon_url = "/TapIcon.svg"
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="icon" type="image/svg+xml" href="{favicon_url}">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ height: 100%; }}
    iframe {{ width: 100%; height: 100%; border: none; }}
  </style>
</head>
<body>
  <iframe src="{pdf_url}" title="{title}"></iframe>
</body>
</html>"""


@app.route("/minio-proxy/<path:object_path>", methods=["GET"])
def minio_proxy(object_path):
    """
    Endpoint proxy pour servir les fichiers depuis MinIO.
    Permet d'accéder aux fichiers MinIO via le serveur Flask sans exposer les credentials.
    
    Usage: http://localhost:5002/minio-proxy/candidates/123/profile.jpg
    """
    try:
        minio_storage = get_minio_storage()
        
        if not minio_storage or not minio_storage.client:
            return jsonify({"error": "MinIO non disponible"}), 503
        
        # Télécharger le fichier depuis MinIO
        success, file_bytes, error = minio_storage.download_file(object_path)
        
        if not success:
            print(f"❌ Erreur proxy MinIO pour {object_path}: {error}")
            return jsonify({"error": f"Fichier non trouvé: {error}"}), 404
        
        # Déterminer le type MIME
        content_type = minio_storage._guess_content_type(object_path)
        
        # Envoyer le fichier
        return send_file(
            BytesIO(file_bytes),
            mimetype=content_type,
            as_attachment=False,
            download_name=os.path.basename(object_path)
        )
        
    except Exception as e:
        print(f"❌ Erreur inattendue proxy MinIO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.route('/api/recruteur/match-by-offre', methods=['POST'])
def match_by_offre():
    """
    Lance le matching (A4.test) pour une offre : candidats triés par score avec détail des scores + infos candidat.
    Body: { "job_id": int, "domaine_activite": "DEV" (optionnel), "top_n": 20 (optionnel) }.
    Retourne: { job_id, job_title, candidates: [ { scores + candidate } ] }.
    """
    data = request.get_json() or {}
    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "Le champ 'job_id' est requis"}), 400
    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        return jsonify({"error": "job_id doit être un entier"}), 400
    domaine_activite = (data.get("domaine_activite") or "").strip().upper() or None
    categorie_profil = (data.get("categorie_profil") or "").strip() or None
    top_n = data.get("top_n", 20)
    only_postule = bool(data.get("only_postule"))
    try:
        top_n = min(max(1, int(top_n)), 100)
    except (TypeError, ValueError):
        top_n = 20
    try:
        import pandas as pd
        from A4.test import (
            load_candidates_df,
            get_job_offer_from_job_id,
            find_matching_candidates,
        )
        job_offer = get_job_offer_from_job_id(job_id)
        if not job_offer:
            return jsonify({"error": "Offre introuvable", "job_id": job_id}), 404
        # Domaine exact : priorité à categorie_profil (dev, data, design...) puis domaine_activite (DATA, DEV...)
        req_categorie = (data.get("categorie_profil") or "").strip() or None
        domaine_for_filter = (job_offer.get("categorie_profil") or job_offer.get("domaine_activite") or req_categorie or domaine_activite or "").strip() or None
        # Si toujours vide, lire directement en base (au cas où load_job_criteria n'a pas retourné ces champs)
        if not domaine_for_filter:
            from database.connection import DatabaseConnection
            DatabaseConnection.initialize()
            with DatabaseConnection.get_connection() as db:
                cur = db.cursor(dictionary=True)
                row = None
                for query in [
                    "SELECT categorie_profil, domaine_activite FROM jobs WHERE id = %s",
                    "SELECT categorie_profil FROM jobs WHERE id = %s",
                    "SELECT domaine_activite FROM jobs WHERE id = %s",
                ]:
                    try:
                        cur.execute(query, (job_id,))
                        row = cur.fetchone()
                        if row:
                            break
                    except Exception:
                        continue
                cur.close()
            if row:
                domaine_for_filter = (row.get("categorie_profil") or row.get("domaine_activite") or "").strip() or None
        # Ne jamais charger tous les candidats sans filtre : si l'offre n'a pas de domaine, retourner liste vide
        if not domaine_for_filter:
            return jsonify({
                "job_id": job_id,
                "job_title": (job_offer.get("title") or job_offer.get("required_title") or "").strip(),
                "candidates": [],
                "message": "Précisez le domaine d'activité ou la catégorie de l'offre pour afficher les candidats matchés.",
            })
        # Normaliser pour matcher exactement la colonne candidats.categorie_profil (dev, data, design, video, autre)
        from candidate_minio_path import normalize_categorie_profil
        categorie_canonique = normalize_categorie_profil(domaine_for_filter)
        df = load_candidates_df(categorie_canonique)
        if df.empty:
            return jsonify({
                "job_id": job_id,
                "job_title": job_offer.get("title") or job_offer.get("required_title") or "",
                "candidates": [],
                "message": "Aucun candidat pour ce domaine.",
            })

        # Ne garder que les candidats qui ont effectivement postulé à cette offre
        if only_postule:
            from database.connection import DatabaseConnection
            DatabaseConnection.initialize()
            with DatabaseConnection.get_connection() as db:
                cur = db.cursor()
                try:
                    cur.execute(
                        "SELECT candidate_id FROM candidate_postule WHERE job_id = %s",
                        (job_id,),
                    )
                    rows = cur.fetchall()
                finally:
                    cur.close()
            applied_ids = [r[0] for r in rows] if rows else []
            if not applied_ids:
                return jsonify({
                    "job_id": job_id,
                    "job_title": job_offer.get("title") or job_offer.get("required_title") or "",
                    "candidates": [],
                    "message": "Aucun candidat n'a encore postulé à cette offre.",
                })
            df = df[df["candidate_id"].isin(applied_ids)]
            if df.empty:
                return jsonify({
                    "job_id": job_id,
                    "job_title": job_offer.get("title") or job_offer.get("required_title") or "",
                    "candidates": [],
                    "message": "Aucun candidat correspondant parmi ceux qui ont postulé.",
                })

        results_df = find_matching_candidates(job_offer, df, top_n=top_n)
        candidates_out = []
        for _, row in results_df.iterrows():
            cid = row.get("candidate_id")
            score_row = {k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in row.to_dict().items()}
            full_row = df[df["candidate_id"] == cid]
            candidate_info = full_row.iloc[0].to_dict() if len(full_row) else {}
            for k, v in list(candidate_info.items()):
                if hasattr(v, "isoformat"):
                    candidate_info[k] = v.isoformat()
                elif isinstance(v, float) and pd.isna(v):
                    candidate_info[k] = None
            candidates_out.append({
                "candidate_id": score_row.get("candidate_id"),
                "name": score_row.get("name"),
                "global_score": score_row.get("global_score"),
                "skill_score": score_row.get("skill_score"),
                "experience_score": score_row.get("experience_score"),
                "language_score": score_row.get("language_score"),
                "seniority_score": score_row.get("seniority_score"),
                "titre_profil_score": score_row.get("titre_profil_score"),
                "disponibilite_score": score_row.get("disponibilite_score"),
                "contract_score": score_row.get("contract_score"),
                "pret_a_relocater_score": score_row.get("pret_a_relocater_score"),
                "pays_cible_score": score_row.get("pays_cible_score"),
                "realisations_score": score_row.get("realisations_score"),
                "salaire_minimum_score": score_row.get("salaire_minimum_score"),
                "missing_skills": score_row.get("missing_skills"),
                "candidate": candidate_info,
            })
        return jsonify({
            "job_id": job_id,
            "job_title": (job_offer.get("title") or job_offer.get("required_title") or "").strip(),
            "candidates": candidates_out,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/recruteur/candidates', methods=['GET'])
def get_recruteur_candidates():
    """Liste des candidats pour le tri (optionnel: filtrer par domaine = DATA, DEV, DESIGN, VIDEO, AUTRE)."""
    domaine = (request.args.get('domaine') or '').strip().upper()
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cols = "c.id, c.id_agent, c.candidate_uuid, c.nom, c.prenom, c.titre_profil, c.categorie_profil, c.ville, c.pays, c.annees_experience, c.disponibilite, c.niveau_seniorite, (SELECT GROUP_CONCAT(s.skill_name) FROM skills s WHERE s.candidate_id = c.id) AS skills_csv"
            sql_base = f"SELECT {cols} FROM candidates c"
            if domaine:
                categorie = normalize_categorie_profil(domaine)
                sql = sql_base + " WHERE c.categorie_profil = %s ORDER BY c.id"
                try:
                    cursor.execute(sql, (categorie,))
                except Exception as col_err:
                    if "1054" in str(col_err) or "Unknown column" in str(col_err):
                        cols = "c.id, c.id_agent, c.nom, c.prenom, c.titre_profil, c.categorie_profil, c.ville, c.pays, c.annees_experience, c.disponibilite, c.niveau_seniorite, (SELECT GROUP_CONCAT(s.skill_name) FROM skills s WHERE s.candidate_id = c.id) AS skills_csv"
                        cursor.execute(f"SELECT {cols} FROM candidates c WHERE c.categorie_profil = %s ORDER BY c.id", (categorie,))
                    else:
                        raise
            else:
                try:
                    cursor.execute(sql_base + " ORDER BY c.id")
                except Exception as col_err:
                    if "1054" in str(col_err) or "Unknown column" in str(col_err):
                        cols = "c.id, c.id_agent, c.nom, c.prenom, c.titre_profil, c.categorie_profil, c.ville, c.pays, c.annees_experience, c.disponibilite, c.niveau_seniorite, (SELECT GROUP_CONCAT(s.skill_name) FROM skills s WHERE s.candidate_id = c.id) AS skills_csv"
                        cursor.execute(f"SELECT {cols} FROM candidates c ORDER BY c.id")
                    else:
                        raise
            rows = cursor.fetchall()
            cursor.close()
        out = []
        for row in rows:
            r = dict(row)
            for k, v in list(r.items()):
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
            if r.get('candidate_uuid') is None or r.get('candidate_uuid') == '':
                r['candidate_uuid'] = r.get('id_agent') or ''
            skills_list = (r.get('skills_csv') or '').split(',') if r.get('skills_csv') else []
            skills_list = [s.strip() for s in skills_list if s.strip()]
            r.pop('skills_csv', None)
            r['skills'] = skills_list
            out.append(r)
        return jsonify({"candidates": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recruteur/candidate-by-domaine', methods=['GET'])
def get_one_candidate_by_domaine():
    """Retourne 1 candidat dont le domaine d'activité correspond (DATA, DEV, DESIGN, VIDEO, AUTRE)."""
    domaine = (request.args.get('domaine') or '').strip().upper()
    if not domaine:
        return jsonify({"error": "Paramètre 'domaine' requis (DATA, DEV, DESIGN, VIDEO, AUTRE)"}), 400
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        categorie = normalize_categorie_profil(domaine)
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, id_agent, nom, prenom, titre_profil, categorie_profil, ville, pays, email, phone,
                       annees_experience, disponibilite, niveau_seniorite, talentcard_minio_url, talentcard_pdf_minio_url
                FROM candidates
                WHERE categorie_profil = %s
                LIMIT 1
                """,
                (categorie,),
            )
            row = cursor.fetchone()
            cursor.close()
        if not row:
            return jsonify({"error": f"Aucun candidat pour le domaine '{domaine}'", "candidate": None}), 404
        for k, v in list(row.items()):
            if hasattr(v, 'isoformat'):
                row[k] = v.isoformat()
        return jsonify({"candidate": row})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recruteur/match-candidates', methods=['POST'])
def match_candidates_weighted():
    """
    Niveau 2 — Matching pondéré intelligent.
    Body: { "job_id": int, "domaine_activite": "DEV" (optionnel), "top_n": 20 (optionnel) }.
    Retourne les candidats triés par score (skills obligatoires=3, optionnelles=1, expérience=poids variable, similarité sémantique TF-IDF).
    """
    data = request.get_json() or {}
    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "Le champ 'job_id' est requis"}), 400
    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        return jsonify({"error": "job_id doit être un entier"}), 400
    domaine_activite = (data.get("domaine_activite") or "").strip().upper() or None
    top_n = data.get("top_n", 20)
    try:
        top_n = min(max(1, int(top_n)), 100)
    except (TypeError, ValueError):
        top_n = 20
    try:
        from A4.weighted_matching import weighted_match
        results = weighted_match(
            domaine_activite=domaine_activite,
            job_id=job_id,
            top_n=top_n,
        )
        out = []
        for r in results:
            c = r["candidate"]
            for k, v in list(c.items()):
                if hasattr(v, "isoformat"):
                    c[k] = v.isoformat()
            out.append({
                "candidate": c,
                "score": r["score"],
                "detail": r["detail"],
            })
        return jsonify({"candidates": out})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/recruteur/match', methods=['POST'])
def match_agent():
    """
    Agent de matching sémantique (embeddings + justification LLM).
    Body: { "job_id": int, "top_n": 20 (optionnel), "with_explanation": true (optionnel) }.
    Retourne: [ { candidate_id, score, similarity_score, explanation, strengths, weaknesses } ].
    """
    data = request.get_json() or {}
    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "Le champ 'job_id' est requis"}), 400
    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        return jsonify({"error": "job_id doit être un entier"}), 400
    top_n = data.get("top_n", 20)
    try:
        top_n = min(max(1, int(top_n)), 100)
    except (TypeError, ValueError):
        top_n = 20
    with_explanation = data.get("with_explanation", True)
    try:
        from A4.agent.pipeline import MatchingPipeline
        from A4.agent.justification import JustificationService
        pipeline = MatchingPipeline()
        results = pipeline.run(job_id=job_id, top_n=top_n, apply_feedback=True)
        if with_explanation and results:
            justification = JustificationService()
            results = justification.explain_batch(job_id, results, with_explanation=True)
        return jsonify(results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/recruteur/match/feedback', methods=['POST'])
def match_feedback():
    """
    Enregistre une décision recruteur (sélectionné / rejeté) pour apprentissage.
    Body: { "job_id": int, "candidate_id": int, "decision": "selected" | "rejected" }.
    """
    data = request.get_json() or {}
    job_id = data.get("job_id")
    candidate_id = data.get("candidate_id")
    decision = (data.get("decision") or "").strip().lower()
    if not job_id or not candidate_id:
        return jsonify({"error": "job_id et candidate_id sont requis"}), 400
    if decision not in ("selected", "rejected"):
        return jsonify({"error": "decision doit être 'selected' ou 'rejected'"}), 400
    try:
        from A4.agent.feedback import record_feedback
        ok = record_feedback(int(job_id), int(candidate_id), decision)
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recruteur/validated-candidates', methods=['GET'])
def get_validated_candidates():
    """
    Liste des candidats validés par le recruteur pour une offre.
    Query: job_id (requis). Retourne: { validated_ids: [int], validated: [{ id, job_id, candidate_id, validated_at, note }] }.
    """
    job_id = request.args.get('job_id')
    if not job_id:
        return jsonify({"error": "job_id est requis"}), 400
    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        return jsonify({"error": "job_id doit être un entier"}), 400
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, job_id, candidate_id, validated_at, note, validate
                FROM candidate_postule
                WHERE job_id = %s
                ORDER BY validated_at DESC
                """,
                (job_id,),
            )
            rows = cursor.fetchall()
            cursor.close()
        out = []
        validated_ids = []
        for r in rows:
            row = dict(r)
            for k, v in list(row.items()):
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
            out.append(row)
            validated_ids.append(row["candidate_id"])
        return jsonify({"validated_ids": validated_ids, "validated": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recruteur/validated-candidates', methods=['POST'])
def add_validated_candidate():
    """
    Enregistre un candidat comme validé par le recruteur pour une offre.
    Body: { "job_id": int, "candidate_id": int }.
    """
    data = request.get_json() or {}
    job_id = data.get("job_id")
    candidate_id = data.get("candidate_id")
    if not job_id or not candidate_id:
        return jsonify({"error": "job_id et candidate_id sont requis"}), 400
    try:
        job_id, candidate_id = int(job_id), int(candidate_id)
    except (TypeError, ValueError):
        return jsonify({"error": "job_id et candidate_id doivent être des entiers"}), 400
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor()
            cursor.execute(
                """
                INSERT INTO candidate_postule (job_id, candidate_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE validated_at = CURRENT_TIMESTAMP
                """,
                (job_id, candidate_id),
            )
            db.commit()
            cursor.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recruteur/validated-candidates', methods=['DELETE'])
def remove_validated_candidate():
    """
    Retire un candidat des validés pour une offre.
    Body ou query: job_id, candidate_id.
    """
    data = request.get_json() or {}
    job_id = data.get("job_id") or request.args.get("job_id")
    candidate_id = data.get("candidate_id") or request.args.get("candidate_id")
    if not job_id or not candidate_id:
        return jsonify({"error": "job_id et candidate_id sont requis"}), 400
    try:
        job_id, candidate_id = int(job_id), int(candidate_id)
    except (TypeError, ValueError):
        return jsonify({"error": "job_id et candidate_id doivent être des entiers"}), 400
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor()
            cursor.execute(
                "DELETE FROM candidate_postule WHERE job_id = %s AND candidate_id = %s",
                (job_id, candidate_id),
            )
            db.commit()
            cursor.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recruteur/interview-questions', methods=['POST'])
def get_interview_questions_for_candidate():
    """
    Génère une liste de questions d'entretien à poser au candidat validé,
    à partir de son CV. Body: { "candidate_id": int, "job_id": int (optionnel) }.
    """
    data = request.get_json() or {}
    candidate_id = data.get("candidate_id")
    if candidate_id is None:
        return jsonify({"success": False, "questions": [], "error": "candidate_id requis"}), 400
    try:
        candidate_id = int(candidate_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "questions": [], "error": "candidate_id doit être un entier"}), 400

    job_title = None
    job_id = data.get("job_id")
    if job_id is not None:
        try:
            from database.connection import DatabaseConnection
            DatabaseConnection.initialize()
            with DatabaseConnection.get_connection() as db:
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT title FROM jobs WHERE id = %s", (int(job_id),))
                row = cursor.fetchone()
                cursor.close()
                if row and row.get("title"):
                    job_title = row["title"]
        except Exception:
            pass

    from A4.entretien_question import get_interview_questions_for_validated_candidate
    result = get_interview_questions_for_validated_candidate(
        candidate_id=candidate_id,
        job_title=job_title,
    )
    if not result.get("success"):
        return jsonify(result), 400
    return jsonify(result)


@app.route('/api/candidate/<int:db_candidate_id>/domaine', methods=['GET'])
def get_candidate_domaine(db_candidate_id):
    """Retourne le domaine d'activité du candidat (categorie_profil) pour filtrer les offres."""
    try:
        info = _get_candidate_info(db_candidate_id, ['categorie_profil'])
        return jsonify({
            "categorie_profil": (info.get('categorie_profil') or '').strip() or None,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """Liste les offres déjà saisies (pour l'espace recruteur). Optionnel: ?domaine=xxx pour filtrer par domaine d'activité.
    Utilise les colonnes réelles de la table jobs pour retourner toutes les infos saisies."""
    try:
        domaine_param = (request.args.get('domaine') or request.args.get('categorie_profil') or '').strip()
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            # Récupérer dynamiquement toutes les colonnes de la table jobs
            cursor.execute("""
                SELECT COLUMN_NAME FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'jobs'
                ORDER BY ORDINAL_POSITION
            """)
            columns_rows = cursor.fetchall()
            if columns_rows:
                col_list = ", ".join(f"`{r['COLUMN_NAME']}`" for r in columns_rows)
                cursor.execute(f"SELECT {col_list} FROM jobs ORDER BY created_at DESC")
                rows = cursor.fetchall()
            else:
                rows = []
            cursor.close()
        out = []
        json_keys = {"location_type", "tasks", "soft_skills", "skills", "languages"}
        for r in rows:
            row = dict(r)
            for k, v in list(row.items()):
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
                elif k in json_keys and isinstance(v, str) and v:
                    try:
                        row[k] = json.loads(v) if v.strip().startswith(("[", "{")) else v
                    except (ValueError, TypeError):
                        pass
            out.append(row)
        if domaine_param:
            dom_lower = domaine_param.lower()
            out = [
                r for r in out
                if (r.get('categorie_profil') or r.get('domaine_activite') or '').strip().lower() == dom_lower
            ]
        return jsonify({"jobs": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Enregistre une offre (Job Spec) en base et retourne job_id."""
    data = request.get_json() or {}
    if not data.get('title'):
        return jsonify({"error": "Le champ 'title' (poste) est requis"}), 400
    try:
        from database.connection import DatabaseConnection
        from candidate_minio_path import normalize_categorie_profil
        # Récupérer l'id du recruteur à partir du token JWT (si présent)
        recruiter_user_id = None
        try:
            from auth import _decode_token_from_request
            payload, _ = _decode_token_from_request()
            if payload:
                role = (payload.get("role") or "").strip().lower()
                if role == "recruteur":
                    recruiter_user_id = payload.get("sub")
        except Exception:
            recruiter_user_id = None

        DatabaseConnection.initialize()
        # La colonne en base est categorie_profil (pas domaine_activite) : on y stocke le domaine d'activité du formulaire
        dom = (data.get('domaine_activite') or '').strip() or ''
        categorie_profil_value = (normalize_categorie_profil(dom) or None) if dom else None
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        try:
            salary_min = float(salary_min) if salary_min not in (None, '') else None
        except (TypeError, ValueError):
            salary_min = None
        try:
            salary_max = float(salary_max) if salary_max not in (None, '') else None
        except (TypeError, ValueError):
            salary_max = None
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor()
            values_with_categorie = (
                data.get('title'),
                data.get('entreprise') or None,
                categorie_profil_value,
                data.get('niveau_attendu'),
                (data.get('niveau_seniorite') or '').strip() or None,
                data.get('experience_min'),
                data.get('presence_sur_site'),
                data.get('reason'),
                data.get('main_mission'),
                data.get('tasks_other') or None,
                data.get('disponibilite'),
                salary_min,
                salary_max,
                1 if data.get('urgent') else 0,
                json.dumps(data.get('location_type', [])),
                json.dumps(data.get('tasks', [])),
                json.dumps(data.get('soft_skills', [])),
                json.dumps(data.get('skills', [])),
                json.dumps(data.get('languages', [])),
                data.get('type_contrat') or None
            )
            values_without_niveau_seniorite = (
                data.get('title'), categorie_profil_value, data.get('niveau_attendu'), data.get('experience_min'),
                data.get('presence_sur_site'), data.get('reason'), data.get('main_mission'),
                data.get('tasks_other') or None, data.get('disponibilite'),
                salary_min, salary_max,
                1 if data.get('urgent') else 0,
                json.dumps(data.get('location_type', [])),
                json.dumps(data.get('tasks', [])),
                json.dumps(data.get('soft_skills', [])),
                json.dumps(data.get('skills', [])),
                json.dumps(data.get('languages', [])),
                data.get('type_contrat') or None
            )
            values_without_domaine_nor_niveau = (
                data.get('title'), data.get('niveau_attendu'), data.get('experience_min'),
                data.get('presence_sur_site'), data.get('reason'), data.get('main_mission'),
                data.get('tasks_other') or None, data.get('disponibilite'),
                salary_min, salary_max,
                1 if data.get('urgent') else 0,
                json.dumps(data.get('location_type', [])),
                json.dumps(data.get('tasks', [])),
                json.dumps(data.get('soft_skills', [])),
                json.dumps(data.get('skills', [])),
                json.dumps(data.get('languages', [])),
                data.get('type_contrat') or None
            )
            try:
                cursor.execute("""
                    INSERT INTO jobs (title, entreprise, categorie_profil, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site,
                        reason, main_mission, tasks_other, disponibilite, salary_min, salary_max, urgent,
                        location_type, tasks, soft_skills, skills, languages, contrat)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, values_with_categorie)
            except Exception as insert_err:
                if "1054" in str(insert_err) or "Unknown column" in str(insert_err):
                    try:
                        cursor.execute("""
                            INSERT INTO jobs (title, categorie_profil, niveau_attendu, niveau_seniorite, experience_min, presence_sur_site,
                                reason, main_mission, tasks_other, disponibilite, salary_min, salary_max, urgent,
                                location_type, tasks, soft_skills, skills, languages, contrat)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, values_with_categorie)
                    except Exception as insert_err2:
                        if "1054" in str(insert_err2) or "Unknown column" in str(insert_err2):
                            try:
                                cursor.execute("""
                                    INSERT INTO jobs (title, categorie_profil, niveau_attendu, experience_min, presence_sur_site,
                                        reason, main_mission, tasks_other, disponibilite, salary_min, salary_max, urgent,
                                        location_type, tasks, soft_skills, skills, languages, contrat)
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                """, values_without_niveau_seniorite)
                            except Exception as insert_err3:
                                if "1054" in str(insert_err3) or "Unknown column" in str(insert_err3):
                                    cursor.execute("""
                                        INSERT INTO jobs (title, niveau_attendu, experience_min, presence_sur_site,
                                            reason, main_mission, tasks_other, disponibilite, salary_min, salary_max, urgent,
                                            location_type, tasks, soft_skills, skills, languages, contrat)
                                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                    """, values_without_domaine_nor_niveau)
                                else:
                                    raise insert_err3
                        else:
                            raise insert_err2
                else:
                    raise insert_err
            job_id = cursor.lastrowid
            # Si un recruteur est connecté, associer son user_id à l'offre créée
            if recruiter_user_id:
                try:
                    cursor.execute(
                        "UPDATE jobs SET user_id = %s WHERE id = %s",
                        (recruiter_user_id, job_id),
                    )
                except Exception as e:
                    # Si la colonne user_id n'existe pas ou autre erreur, on n'empêche pas la création du job
                    if "1054" in str(e) or "Unknown column" in str(e):
                        pass
                    else:
                        raise
        return jsonify({"job_id": job_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500





@app.route('/api/scoring/<db_candidate_id>', methods=['GET', 'POST'])
def scoring_candidate(db_candidate_id):
    """
    Route pour le scoring et l'analyse A2 d'un candidat.
    POST: Construit le chemin MinIO vers le JSON via l'UUID et lance l'agent.
    """
    try:
        from database.connection import DatabaseConnection

        def _safe_float(value, default=0.0):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        def _extract_skills_payload(payload):
            if not isinstance(payload, dict):
                return []

            raw_skills = (
                payload.get('skills')
                or payload.get('competencies')
                or payload.get('competences')
                or []
            )
            if not isinstance(raw_skills, list):
                return []

            skills = []
            for item in raw_skills:
                if not isinstance(item, dict):
                    continue

                name = item.get('name') or item.get('original_name') or item.get('normalized_name')
                if not name:
                    continue

                scope = item.get('scope')
                if not scope and isinstance(item.get('exp_context'), dict):
                    scope = item['exp_context'].get('scope')

                skills.append({
                    'name': str(name),
                    'score': _safe_float(item.get('score')),
                    'status': str(item.get('status') or 'declare'),
                    'scope': str(scope or 'individuel')
                })

            skills.sort(key=lambda x: x.get('score', 0.0), reverse=True)
            return skills

        def _save_skills_score(cursor, skills, candidate_id=None, score_id=None):
            if not skills:
                return

            try:
                cursor.execute("SHOW COLUMNS FROM skills_score")
                col_rows = cursor.fetchall()
            except Exception as save_error:
                print(f"⚠️ skills_score indisponible, insertion ignorée: {save_error}")
                return

            available_cols = {
                row.get('Field') if isinstance(row, dict) else row[0]
                for row in col_rows
            }

            base_cols = ['name', 'score', 'status', 'scope']
            insert_cols = [c for c in base_cols if c in available_cols]
            if len(insert_cols) < 4:
                return

            if 'candidate_id' in available_cols:
                insert_cols.append('candidate_id')
            if 'score_id' in available_cols and score_id is not None:
                insert_cols.append('score_id')

            placeholders = ', '.join(['%s'] * len(insert_cols))
            query = f"INSERT INTO skills_score ({', '.join(insert_cols)}) VALUES ({placeholders})"

            values = []
            for skill in skills:
                row_values = [skill['name'], skill['score'], skill['status'], skill['scope']]
                if 'candidate_id' in insert_cols:
                    row_values.append(candidate_id)
                if 'score_id' in insert_cols and score_id is not None:
                    row_values.append(score_id)
                values.append(tuple(row_values))

            cursor.executemany(query, values)

        def _fetch_skills_score(cursor, candidate_id=None, score_id=None):
            try:
                cursor.execute("SHOW COLUMNS FROM skills_score")
                col_rows = cursor.fetchall()
            except Exception:
                return []

            available_cols = {
                row.get('Field') if isinstance(row, dict) else row[0]
                for row in col_rows
            }
            required = {'name', 'score', 'status', 'scope'}
            if not required.issubset(available_cols):
                return []

            query = "SELECT name, score, status, scope FROM skills_score"
            params = []
            if 'candidate_id' in available_cols and candidate_id is not None:
                query += " WHERE candidate_id = %s"
                params.append(candidate_id)
            elif 'score_id' in available_cols and score_id is not None:
                query += " WHERE score_id = %s"
                params.append(score_id)
            else:
                return []

            query += " ORDER BY score DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [
                {
                    'name': row.get('name'),
                    'score': _safe_float(row.get('score')),
                    'status': row.get('status') or 'declare',
                    'scope': row.get('scope') or 'individuel'
                }
                for row in rows
            ]

        if request.method == 'POST':
            # 1. Récupérer l'UUID du candidat en base
            candidate_uuid = None
            with DatabaseConnection.get_connection() as db:
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    "SELECT candidate_uuid FROM candidates WHERE id = %s",
                    (db_candidate_id,)
                )
                row = cursor.fetchone()
                cursor.close()
                
                if row:
                    candidate_uuid = row.get('candidate_uuid')

            if not candidate_uuid:
                return jsonify({'success': False, 'message': 'UUID du candidat introuvable en base'}), 404

            # 2. Construire le chemin du fichier JSON dans MinIO
            # Structure : candidates/{categorie_profil}/{id}/talentcard_{uuid}.json
            minio_prefix = get_candidate_minio_prefix(int(db_candidate_id))
            object_name = f"{minio_prefix}talentcard_{candidate_uuid}.json"
            
            print(f"🎯 Cible MinIO identifiée : {object_name}")

            # 3. Récupérer le contenu du fichier JSON depuis MinIO
            minio_storage = get_minio_storage()
            bucket_name = minio_storage.bucket_name # Devrait être 'tap-files' selon ton URL
            
            talentcard_data = None
            try:
                # On récupère l'objet (le fichier)
                response = minio_storage.client.get_object(bucket_name, object_name)
                # On lit les bytes et on parse le JSON
                file_content = response.read()
                talentcard_data = json.loads(file_content)
                response.close()
                response.release_conn()
                print("✅ JSON TalentCard chargé avec succès depuis MinIO.")
            except Exception as e:
                print(f"❌ Erreur lors de la récupération MinIO : {e}")
                return jsonify({
                    'success': False, 
                    'message': f"Impossible de lire le fichier JSON : {object_name}"
                }), 404

            # 3b. Récupérer la dernière réponse du chatbot (soft skills déclarés par le candidat) pour enrichir le scoring
            chat_soft_skills_text = None
            try:
                from B2.chat.save_responses import get_chat_responses_from_minio
                success, chat_data, _ = get_chat_responses_from_minio(int(db_candidate_id))
                if success and isinstance(chat_data, dict):
                    answers = chat_data.get("answers") or {}
                    if not isinstance(answers, dict):
                        answers = {}
                    # Clé attendue (question soft skills en dernier)
                    chat_soft_skills_text = (answers.get("soft_skills_8_examples") or "").strip()
                    if not chat_soft_skills_text:
                        # Fallback: toute clé contenant "soft_skills"
                        for k, v in (answers or {}).items():
                            if v and isinstance(v, str) and "soft_skills" in (k or "").lower():
                                chat_soft_skills_text = v.strip()
                                break
                    if not chat_soft_skills_text and answers:
                        # Fallback: dernière réponse = question soft skills (toujours en dernier dans le flux)
                        last_key = list(answers.keys())[-1]
                        chat_soft_skills_text = (answers.get(last_key) or "").strip()
                    if chat_soft_skills_text:
                        print("✅ Soft skills du chatbot (réponse candidat) récupérés pour l'évaluation A2.")
                    else:
                        print("⚠️ Aucune réponse soft skills trouvée dans chat_responses (scoring sans soft skills chatbot).")
                        chat_soft_skills_text = None
            except Exception as e:
                print(f"⚠️ Chat responses non disponibles (scoring sans soft skills chatbot): {e}")
                chat_soft_skills_text = None

            # 4. Lancer l'Agent Scoring V2
            try:
                with DatabaseConnection.get_connection() as db:
                    # Initialisation de l'agent V2
                    agent = AgentScoringV2(db)
                    
                    # Exécution de l'analyse (avec soft skills chatbot si présents)
                    print("🚀 Lancement de l'agent AI V2...")
                    analyse = agent.evaluate_candidate(talentcard_data, db_candidate_id, chat_soft_skills_text=chat_soft_skills_text)
                    
                    # Mini-agent compétences (A2 bis)
                    agent2 = A2BisDynamicAgent()
                    data_process = {
                        'skills': talentcard_data.get('skills', []),
                        'experience': talentcard_data.get('experience', []),
                        'realisations': talentcard_data.get('realisations', []),
                        'scores': analyse.get('scores', {})
                    }
                    skills_result = agent2.process_competencies(data_process)
                    skills_payload = _extract_skills_payload(skills_result)
                    analyse['skills'] = skills_payload

                    score_id = analyse.get('metadata', {}).get('score_id')
                    insert_cursor = db.cursor()
                    try:
                        _save_skills_score(insert_cursor, skills_payload, candidate_id=db_candidate_id, score_id=score_id)
                    finally:
                        insert_cursor.close()
                    db.commit()

                    # (Optionnel) Sauvegarde locale pour debug
                    output_path = f"A2/analyse_{db_candidate_id}.json"
                    agent.export_json(analyse, output_path)

                    # Préparer la réponse pour l'interface: score global + 6 métriques
                    response_data = {
                        'success': True,
                        'message': 'Analyse générée avec succès',
                        'scores': {
                            'score_global': analyse['scores']['score_global'],
                            'decision': analyse['scores']['decision'],
                            'dimensions': {
                                'impact': analyse['scores']['dimensions']['impact']['score'],
                                'hard_skills_depth': analyse['scores']['dimensions']['hard_skills_depth']['score'],
                                'coherence': analyse['scores']['dimensions']['coherence']['score'],
                                'rarete_marche': analyse['scores']['dimensions']['rarete_marche']['score'],
                                'stabilite': analyse['scores']['dimensions']['stabilite']['score'],
                                'communication': analyse['scores']['dimensions']['communication']['score']
                            }
                        },
                        'skills': skills_payload,
                        'metadata': analyse['metadata']
                    }

                return jsonify(response_data)
            except Exception as agent_error:
                print(f"❌ Erreur interne de l'agent : {agent_error}")
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(agent_error)}), 500

        else:  # GET request (inchangée)
            from database.connection import DatabaseConnection
            with DatabaseConnection.get_connection() as db:
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT * FROM score 
                    WHERE candidate_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                    """,
                    (db_candidate_id,)
                )
                score_data = cursor.fetchone()
                projection_data = None
                if score_data and score_data.get('id'):
                    cursor.execute(
                        """
                        SELECT famille_dominante
                        FROM score_family_projection
                        WHERE score_id = %s
                        LIMIT 1
                        """,
                        (score_data.get('id'),)
                    )
                    projection_data = cursor.fetchone()
                # Récupérer aussi les infos du candidat
                cursor.execute(
                    """
                    SELECT nom, prenom, email, phone, ville 
                    FROM candidates 
                    WHERE id = %s
                    """,
                    (db_candidate_id,)
                )
                candidate_info = cursor.fetchone()
                skills_data = _fetch_skills_score(
                    cursor,
                    candidate_id=db_candidate_id,
                    score_id=score_data.get('id') if score_data else None
                )

                evaluation_soft_skills_declares = []
                analyse_path = os.path.join("A2", f"analyse_{db_candidate_id}.json")
                if os.path.exists(analyse_path):
                    try:
                        with open(analyse_path, 'r', encoding='utf-8') as f:
                            cached_analyse = json.load(f)
                        if not skills_data:
                            skills_data = _extract_skills_payload(cached_analyse)
                        ev = cached_analyse.get("evaluation_soft_skills_declares")
                        if isinstance(ev, list):
                            evaluation_soft_skills_declares = ev
                    except Exception as cache_error:
                        print(f"⚠️ Impossible de relire depuis {analyse_path}: {cache_error}")
                cursor.close()

            if not score_data:
                return jsonify({'success': False, 'message': 'Analyse non trouvée.'}), 404

            def _score_val(*keys):
                for key in keys:
                    value = score_data.get(key)
                    if value is not None:
                        try:
                            return float(value)
                        except (TypeError, ValueError):
                            pass
                return 0.0

            analyse = {
                'metadata': {
                    'candidate_id': db_candidate_id,
                    'timestamp': score_data['created_at'].isoformat() if score_data['created_at'] else None,
                    'sector_detected': score_data.get('sector_detected'),
                    'module_used': score_data.get('module_used'),
                    'famille_dominante': projection_data.get('famille_dominante') if projection_data else None
                },
                'scores': {
                    'score_global': float(score_data.get('score_global') or 0),
                    'famille_dominante': projection_data.get('famille_dominante') if projection_data else None,
                    'dimensions': {
                        'hard_skills_fit': {
                            'score': _score_val('dim_hard_skills_depth', 'hard_skills_fit'),
                            'poids': 25,
                            'sous_scores': {
                                'nombre_competences': score_data.get('hsf_nombre_competences'),
                                'competences_core_maitrisees': score_data.get('hsf_competences_core_maitrisees'),
                                'coefficients_moyens': float(score_data.get('hsf_coefficients_moyens') or 0)
                            }
                        },
                        'preuves_impact': {
                            'score': _score_val('dim_impact', 'preuves_impact'),
                            'poids': 25,
                            'sous_scores': {
                                'qualite_metriques': float(score_data.get('impact_qualite_metriques') or 0),
                                'quantite_preuves': float(score_data.get('impact_quantite_preuves') or 0),
                                'pertinence_business': float(score_data.get('impact_pertinence_business') or 0)
                            }
                        },
                        'rarete_marche': {
                            'score': _score_val('dim_rarete_marche', 'rarete_marche'),
                            'poids': 20
                        },
                        'coherence_parcours': {
                            'score': _score_val('dim_coherence', 'coherence_parcours'),
                            'poids': 15
                        },
                        'stabilite_risque': {
                            'score': _score_val('dim_stabilite', 'stabilite_risque'),
                            'poids': 10
                        },
                        'communication_clarte': {
                            'score': _score_val('dim_communication', 'communication_clarte'),
                            'poids': 5
                        }
                    }
                },
                'commentaire_recruteur': "Analyse générée avec succès. Consultez les scores ci-dessus.",
                'questions_entretien': [],
                'decision': score_data.get('decision'),
                'skills': skills_data,
                'evaluation_soft_skills_declares': evaluation_soft_skills_declares
            }

            # Récupérer les soft skills déclarés par le candidat (chatbot) pour affichage
            try:
                from B2.chat.save_responses import get_chat_responses_from_minio
                success, chat_data, _ = get_chat_responses_from_minio(int(db_candidate_id))
                soft_skills_text = None
                if success and isinstance(chat_data, dict):
                    answers = chat_data.get("answers") or {}
                    if isinstance(answers, dict):
                        soft_skills_text = (answers.get("soft_skills_8_examples") or "").strip()
                        if not soft_skills_text:
                            for k, v in answers.items():
                                if v and isinstance(v, str) and "soft_skills" in (k or "").lower():
                                    soft_skills_text = v.strip()
                                    break
                        if not soft_skills_text and answers:
                            last_key = list(answers.keys())[-1]
                            soft_skills_text = (answers.get(last_key) or "").strip()
                analyse['soft_skills_declared'] = soft_skills_text or None

                # Fallback : si on a le texte mais pas d'évaluation LLM, extraire les noms des soft skills pour l'affichage
                if (soft_skills_text and (not evaluation_soft_skills_declares or len(evaluation_soft_skills_declares) == 0)):
                    import re
                    parsed = []
                    seen = set()
                    for line in soft_skills_text.split('\n'):
                        line = line.strip()
                        if not line or ':' not in line:
                            continue
                        # Partie avant le premier ":" = libellé (ex: "**Autonomie**" ou "**Pensée Analytique (Analytical Thinking)**")
                        raw_nom = line.split(':', 1)[0].strip()
                        nom = re.sub(r'^\*+|\*+$', '', raw_nom).strip()
                        # Garder uniquement les libellés courts (titres de soft skill), pas une phrase
                        if 2 < len(nom) <= 100 and nom.lower() not in seen:
                            seen.add(nom.lower())
                            parsed.append({'nom': nom, 'niveau': 'MOYEN'})
                    if parsed:
                        evaluation_soft_skills_declares = parsed
                        analyse['evaluation_soft_skills_declares'] = parsed
            except Exception:
                analyse['soft_skills_declared'] = None

            return jsonify({
                'success': True,
                'analyse': analyse,
                'candidate_info': candidate_info
            })

    except Exception as e:
        print(f"❌ Erreur dans le scoring_candidate endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == "__main__":
    # Écouter sur 0.0.0.0 pour être accessible depuis d'autres conteneurs Docker
    app.run(debug=True, host='0.0.0.0', port=5002)
