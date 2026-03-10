"""
Agent de génération de portfolios HTML
Génère automatiquement les versions HTML (longue et one-page) à partir des données JSON du portfolio
"""

import base64
import os
import random
import re
import tempfile
import threading
from typing import Dict, Optional, Tuple, Any
from jinja2 import Template


def _load_talentcard_from_db(candidate_id: int) -> Optional[Dict[str, Any]]:
    """
    Reconstruit les données talent card depuis la base (candidates + skills + experiences + realisations).
    Évite la dépendance circulaire avec app.py.
    """
    try:
        from database.connection import DatabaseConnection

        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM candidates WHERE id = %s", (candidate_id,))
            candidate = cursor.fetchone()
            if not candidate:
                return None

            cursor.execute(
                """
                SELECT c.*,
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
                (candidate_id,),
            )
            candidate_full = cursor.fetchone() or {}
            cursor.execute("SELECT * FROM experiences WHERE candidate_id = %s", (candidate_id,))
            experiences = cursor.fetchall() or []
            cursor.execute("SELECT * FROM realisations WHERE candidate_id = %s", (candidate_id,))
            realisations = cursor.fetchall() or []
            cursor.close()

        skills_raw = candidate_full.get("skills") or ""
        languages_raw = candidate_full.get("languages") or ""
        contract_types_raw = candidate_full.get("contract_types") or ""

        return {
            "id_agent": candidate.get("id_agent"),
            "nom": candidate.get("nom", "") or "",
            "prenom": candidate.get("prenom", "") or "",
            "Titre de profil": candidate.get("titre_profil", "") or "",
            "ville": candidate.get("ville", "") or "",
            "pays": candidate.get("pays", "") or "",
            "linkedin": candidate.get("linkedin", "") or "",
            "github": candidate.get("github", "") or "",
            "behance": candidate.get("behance", "") or "",
            "email": candidate.get("email", "") or "",
            "phone": candidate.get("phone", "") or "",
            "annees_experience": candidate.get("annees_experience"),
            "disponibilite": candidate.get("disponibilite", "") or "",
            "pret_a_relocater": candidate.get("pret_a_relocater", "") or "",
            "niveau_seniorite": candidate.get("niveau_seniorite", "") or "",
            "pays_cible": (candidate.get("pays_cible") or candidate.get("target_country") or "").strip() or "",
            "salaire_minimum": candidate.get("salaire_minimum", "") or "",
            "resume_bref": candidate.get("resume_bref", "") or "",
            "skills": [s.strip() for s in skills_raw.split(",") if s.strip()] if skills_raw else [],
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
            "langues_parlees": [l.strip() for l in languages_raw.split(",") if l.strip()] if languages_raw else [],
            "type_contrat": [c.strip() for c in contract_types_raw.split(",") if c.strip()] if contract_types_raw else [],
            "analyse": candidate.get("analyse", "") or "",
        }
    except Exception as e:
        print(f"❌ Erreur chargement talentcard depuis DB: {e}")
        return None


def transform_talent_card_data_for_template(
    talent_card_data: Dict,
    candidate_image_url: Optional[str] = None,
    candidate_job_title: Optional[str] = None,
    candidate_years_experience: Optional[int] = None,
    candidate_email: Optional[str] = None,
    candidate_phone: Optional[str] = None,
) -> Dict:
    """
    Transforme les données talent card (DB ou JSON) en format attendu par le template Jinja2.
    """
    c = talent_card_data
    candidate = {
        "nom": c.get("nom", "") or "",
        "prenom": c.get("prenom", "") or "",
        "Titre de profil": c.get("Titre de profil", "") or c.get("titre_profil", "") or "",
        "titre_profil": c.get("Titre de profil", "") or c.get("titre_profil", "") or "",
        "ville": c.get("ville", "") or "",
        "pays": c.get("pays", "") or "",
        "email": (candidate_email or c.get("email", "") or "").strip(),
        "phone": (candidate_phone or c.get("phone", "") or "").strip(),
        "annees_experience": candidate_years_experience if candidate_years_experience is not None else c.get("annees_experience"),
        "disponibilite": c.get("disponibilite", "") or "",
        "type_contrat": c.get("type_contrat") if isinstance(c.get("type_contrat"), list) else ([c.get("type_contrat")] if c.get("type_contrat") else []),
        "skills": c.get("skills") or [],
        "profile_image_url": candidate_image_url or "",
        "qr_code_url": "",  # Sera rempli dans generate_talent_card_html si cv_download_url disponible
        "linkedin_url": (c.get("linkedin") or "").strip() or "",
        "github_url": (c.get("github") or "").strip() or "",
        "behance_url": (c.get("behance") or "").strip() or "",
        "cv_download_url": "",  # Sera rempli dans generate_talent_card_html
        "pret_a_relocater": (c.get("pret_a_relocater") or c.get("prêt à relocaliser") or c.get("ready_to_relocate") or "").strip() or "",
        "niveau_seniorite": (c.get("niveau_seniorite") or c.get("niveau de seniorite") or "").strip() or "",
        "pays_cible": (c.get("pays_cible") or c.get("target_country") or c.get("pays cible") or "").strip() or "",
        "salaire_minimum": (c.get("salaire_minimum") or "").strip() or "",
    }
    return {"candidate": candidate}


def _minio_url_to_proxy(url: Optional[str], flask_base_url: str = "http://localhost:5002") -> str:
    """Convertit une URL MinIO en URL proxy Flask pour que l'image soit accessible dans le HTML."""
    if not url or not url.strip():
        return url or ""
    try:
        parts = url.split("/", 4)
        if len(parts) >= 5:
            return f"{flask_base_url.rstrip('/')}/minio-proxy/{parts[4]}"
    except Exception:
        pass
    return url


def get_template_path(template_name: str) -> Optional[str]:
    """
    Trouve le chemin du template HTML.
    
    Args:
        template_name: Nom du template (ex: "portfolio_1page_template.html")
    
    Returns:
        Chemin absolu du template ou None si introuvable
    """
    # Chemins possibles (dans l'ordre de priorité)
    possible_paths = [
        # Depuis le backend (si le frontend est monté)
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                     "frontend", "src", "talent card html", template_name),
        # Depuis le conteneur Docker
        f"/app/frontend/src/talent card html/{template_name}",
        # Depuis le volume monté
        f"/frontend/src/talent card html/{template_name}",
        # Depuis le répertoire courant
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "talent card html", template_name),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def convert_project_images_to_proxy(projects: list, flask_base_url: str = "http://localhost:5002") -> list:
    """
    Convertit toutes les URLs MinIO des images de projets en URLs proxy.
    Fonction utilitaire pour éviter la dépendance circulaire avec app.py
    
    Args:
        projects: Liste des projets avec leurs images
        flask_base_url: URL de base du serveur Flask
    
    Returns:
        Liste des projets avec URLs converties
    """
    if not projects or not isinstance(projects, list):
        return projects
    
    def convert_minio_url(minio_url: str) -> str:
        """Convertit une URL MinIO en URL proxy"""
        if not minio_url:
            return minio_url
        try:
            parts = minio_url.split('/', 4)
            if len(parts) >= 5:
                object_path = parts[4]
                return f"{flask_base_url}/minio-proxy/{object_path}"
            return minio_url
        except Exception:
            return minio_url
    
    for project in projects:
        if not isinstance(project, dict):
            continue
        
        # Convertir main_image_url
        if project.get("main_image_url"):
            project["main_image_url"] = convert_minio_url(project["main_image_url"])
        
        # Convertir preview_images
        if project.get("preview_images") and isinstance(project["preview_images"], list):
            for img in project["preview_images"]:
                if isinstance(img, dict) and img.get("url"):
                    img["url"] = convert_minio_url(img["url"])
        
        # Convertir images (si présent)
        if project.get("images") and isinstance(project["images"], list):
            converted_images = []
            for img in project["images"]:
                if isinstance(img, str):
                    converted_images.append(convert_minio_url(img))
                elif isinstance(img, dict) and img.get("url"):
                    img["url"] = convert_minio_url(img["url"])
                    converted_images.append(img)
                else:
                    converted_images.append(img)
            project["images"] = converted_images
    
    return projects


def generate_talent_card_html(
    candidate_id: int,
    candidate_image_url: Optional[str] = None,
    candidate_email: Optional[str] = None,
    candidate_phone: Optional[str] = None,
    candidate_job_title: Optional[str] = None,
    candidate_years_experience: Optional[int] = None,
    flask_base_url: str = "http://localhost:5002",
    candidate_uuid: Optional[str] = None,
    candidate_linkedin_url: Optional[str] = None,
    candidate_github_url: Optional[str] = None,
    candidate_behance_url: Optional[str] = None,
    lang: str = "fr",
    extra_candidate_data: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Génère le HTML de la Talent Card à partir des données du candidat.
    
    Args:
        candidate_id: ID du candidat en base de données
        candidate_image_url: URL de l'image du candidat (optionnel)
        candidate_email: Email du candidat (optionnel)
        candidate_phone: Téléphone du candidat (optionnel)
        candidate_job_title: Titre du poste (optionnel)
        candidate_years_experience: Années d'expérience (optionnel)
        flask_base_url: URL de base du serveur Flask pour les proxies
        candidate_uuid: UUID du candidat pour le lien de téléchargement du CV (optionnel)
    
    Returns:
        Tuple (success, html_content, error_message)
    """
    try:
        print(f"🔄 Génération de la Talent Card HTML pour candidate_id={candidate_id}")

        # 1. Charger les données talent card depuis la base
        talent_card_data = _load_talentcard_from_db(candidate_id)
        if not talent_card_data:
            return False, None, "Données talent card introuvables pour ce candidat (base de données)"

        print("✅ Données Talent Card chargées depuis la base")
        
        # Photo candidat : convertir URL MinIO en proxy pour affichage dans le HTML
        profile_image_url = _minio_url_to_proxy(candidate_image_url, flask_base_url) if candidate_image_url else ""

        # 2. Transformer les données pour le template (champs attendus par talent_card_template.html)
        template_data = transform_talent_card_data_for_template(
            talent_card_data,
            candidate_image_url=profile_image_url,
            candidate_job_title=candidate_job_title,
            candidate_years_experience=candidate_years_experience,
            candidate_email=candidate_email,
            candidate_phone=candidate_phone,
        )

        # 2.1 Lien de téléchargement du CV (pour le template) et QR code pointant vers la page recruteur (valide dès le début)
        cv_download_url = ""
        if candidate_uuid:
            cv_download_url = (
                f"{flask_base_url.rstrip('/')}/correctedcv/{candidate_uuid}/download?db_candidate_id={candidate_id}"
            )
        recruit_landing_url = f"{flask_base_url.rstrip('/')}/recruit/{candidate_id}"
        if template_data.get("candidate"):
            template_data["candidate"]["cv_download_url"] = cv_download_url
            # QR code : pointe vers la page recruteur (tous les fichiers) pour être valide dès la génération de la talent card
            try:
                from A1.generate_talent import _make_qr_image_bytes
                qr_bytes = _make_qr_image_bytes(recruit_landing_url, box_size=4)
                if qr_bytes:
                    template_data["candidate"]["qr_code_url"] = (
                        "data:image/png;base64," + base64.b64encode(qr_bytes).decode("ascii")
                    )
                else:
                    template_data["candidate"]["qr_code_url"] = ""
            except Exception as e:
                print(f"⚠️ QR code non généré: {e}")
                template_data["candidate"]["qr_code_url"] = ""

        # 2.2 LinkedIn / GitHub / Behance depuis la base ou formulaire (priorité sur les données générées)
        if template_data.get("candidate"):
            if candidate_linkedin_url:
                template_data["candidate"]["linkedin_url"] = candidate_linkedin_url.strip()
            if candidate_github_url:
                template_data["candidate"]["github_url"] = candidate_github_url.strip()
            if candidate_behance_url:
                template_data["candidate"]["behance_url"] = candidate_behance_url.strip()
        # 2.3 Données supplémentaires (ex: pays_cible depuis le formulaire à la création)
        if extra_candidate_data and template_data.get("candidate"):
            for key, value in extra_candidate_data.items():
                if value is not None and (value if isinstance(value, str) else str(value)).strip():
                    template_data["candidate"][key] = value
        
        print("✅ Données transformées pour le template")
        
        # 3. Sélectionner le template selon la version
        template_name = "talent_card_template2.html"
        
        # 4. Charger le template
        template_path = get_template_path(template_name)
        
        if not template_path:
            return False, None, f"Template introuvable: {template_name}"
        
        print(f"✅ Template trouvé: {template_path}")
        
        # 5. Lire le template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 6. URL de base pour les assets (images de fond) — le HTML est servi sans chemin de fichier
        assets_base_url = (flask_base_url or "http://localhost:5002").rstrip("/") + "/talent/static/"
        lang = (lang or "fr").lower() if lang else "fr"
        if lang not in ("fr", "en"):
            lang = "fr"
        # 7. Rendre le template avec Jinja2
        try:
            jinja_template = Template(template_content)
            html_content = jinja_template.render(
                candidate=template_data.get('candidate', {}),
                candidate_id=candidate_id,
                assets_base_url=assets_base_url,
                portfolio_lang=lang,
            )
            print("✅ Template rendu avec succès (talent-card)")
            return True, html_content, None
        except Exception as e:
            error_msg = f"Erreur lors du rendu Jinja2: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, None, error_msg
        
    except Exception as e:
        error_msg = f"Erreur lors de la génération du portfolio HTML: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, None, error_msg


def save_portfolio_html(
    html_content: str,
    candidate_id: int,
    candidate_uuid: str,
    version: str = "one-page",
    lang: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Sauvegarde le HTML généré dans MinIO.
    
    Args:
        html_content: Contenu HTML généré
        candidate_id: ID du candidat
        candidate_uuid: UUID du candidat
        version: Version ("one-page", "long", "talent-card")
        lang: Langue ("fr" ou "en"). Si fourni, suffixe ajouté au nom du fichier.
    
    Returns:
        Tuple (success, url, error_message)
    """
    try:
        from minio_storage import get_minio_storage
        from candidate_minio_path import get_candidate_minio_prefix

        minio_storage = get_minio_storage()
        minio_prefix = get_candidate_minio_prefix(candidate_id)
        if lang and lang in ("fr", "en"):
            object_name = f"{minio_prefix}portfolio_{candidate_uuid}_{version}_{lang}.html"
        else:
            object_name = f"{minio_prefix}portfolio_{candidate_uuid}_{version}.html"
        
        # Convertir en bytes
        html_bytes = html_content.encode('utf-8')
        
        success, url, error = minio_storage.upload_file(
            html_bytes,
            object_name,
            content_type="text/html"
        )
        
        if success:
            print(f"✅ Portfolio HTML sauvegardé dans MinIO: {url}")
            return True, url, None
        else:
            return False, None, f"Erreur upload HTML vers MinIO: {error}"
            
    except Exception as e:
        error_msg = f"Erreur lors de la sauvegarde du portfolio HTML: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, None, error_msg


def _get_talent_card_assets_dir() -> Optional[str]:
    """Retourne le chemin du dossier des assets (Modif-2.jpeg, Background-3.png) pour la Talent Card."""
    _here = os.path.dirname(os.path.abspath(__file__))
    _backend = os.path.dirname(_here)
    _root = os.path.dirname(_backend)
    for base in [
        os.path.join(_root, "frontend", "src", "talent card html"),
        os.path.join(_backend, "..", "frontend", "src", "talent card html"),
        "/app/frontend/src/talent card html",
        "/frontend/src/talent card html",
        os.path.join(os.getcwd(), "frontend", "src", "talent card html"),
    ]:
        base = os.path.normpath(os.path.abspath(base))
        modif = os.path.join(base, "Modif-2.jpeg")
        bg3 = os.path.join(base, "Background-3.png")
        if os.path.isfile(modif) and os.path.isfile(bg3):
            return base
    return None


def convert_talent_card_html_to_pdf(
    html_content: str,
    candidate_id: int,
    candidate_uuid: str,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Convertit le HTML de la Talent Card en PDF (Playwright), puis uploade dans MinIO.

    Dimensions de la carte : 16,8 cm × 12,3349 cm (template talent_card_template2.html).

    Returns:
        Tuple (success, pdf_minio_url, error_message)
    """
    try:
        from playwright.sync_api import sync_playwright
        import http.server
        import socketserver

        print(f"🔄 Conversion Talent Card HTML → PDF pour candidate_id={candidate_id}")

        # Intégrer les images de fond en base64 pour le PDF
        assets_dir = _get_talent_card_assets_dir()
        if assets_dir:
            try:
                with open(os.path.join(assets_dir, "Modif-2.jpeg"), "rb") as f:
                    b64_modif = base64.b64encode(f.read()).decode("ascii")
                with open(os.path.join(assets_dir, "Background-3.png"), "rb") as f:
                    b64_bg3 = base64.b64encode(f.read()).decode("ascii")
                data_modif = f"data:image/jpeg;base64,{b64_modif}"
                data_bg3 = f"data:image/png;base64,{b64_bg3}"
                html_content = re.sub(
                    r"url\s*\(\s*['\"]?[^'\"]*Modif-2\.jpeg['\"]?\s*\)",
                    f"url('{data_modif}')",
                    html_content,
                )
                html_content = re.sub(
                    r"url\s*\(\s*['\"]?[^'\"]*Background-3\.png['\"]?\s*\)",
                    f"url('{data_bg3}')",
                    html_content,
                )
                print("✅ Images de fond Talent Card intégrées en base64 pour le PDF")
            except Exception as e:
                print(f"⚠️ Images de fond Talent Card non intégrées: {e}")

        # Règles @media print : couleurs et alignement identiques au HTML (barre contact)
        _exact = "-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important;"

        
        pdf_print_style = (
            " @media print { * { " + _exact + " } "
            " body { background: #0d0d0d !important; " + _exact + " } "
            " .talent-card { " + _exact + " } "
            " .name-bar, .qr-box, .expertise-bar .left, .expertise-bar .right { " + _exact + " } "
            " .block-header { " + _exact + " } "
            " .contact-bar { height: 1cm !important; " + _exact + " } "
            " .contact-bar .icon-btn, .contact-bar .icon-btn .material-symbols-sharp, .contact-bar .deco-block { "
            "   " + _exact + " background: #C1121F !important; color: #fff !important; "
            " } "
            " .contact-bar .icon-btn { width: 1.2cm !important; height: 1.2cm !important; min-height: 1.2cm !important; margin-top: -4px !important; } "
            " .contact-bar .deco-block { width: 1.3cm !important; height: 1.3cm !important; min-height: 1cm !important; margin-top: -5px !important; } "
            " .contact-bar .cta-box { height: 1cm !important; min-height: 1cm !important; background: #fff !important; color: #1a1a1a !important; " + _exact + " } "
            " .contact-bar .separator { width: 0.15cm !important; min-width: 0.15cm !important; height: 1cm !important; min-height: 1cm !important; display: block !important; flex-shrink: 0 !important; background: #fff !important; " + _exact + " } "
            " } "
        )


        html_content = html_content.replace("</style>", pdf_print_style + "\n    </style>", 1)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(html_content)
            temp_html_path = f.name

        temp_dir = os.path.dirname(temp_html_path)
        html_filename = os.path.basename(temp_html_path)

        class _Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=temp_dir, **kwargs)

            def log_message(self, format, *args):
                pass

        class _Reusable(socketserver.TCPServer):
            allow_reuse_address = True

        httpd = None
        for _ in range(10):
            try:
                port = random.randint(8000, 9000)
                httpd = _Reusable(("", port), _Handler)
                break
            except OSError:
                continue
        if not httpd:
            raise RuntimeError("Aucun port disponible pour le serveur HTTP")

        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        pdf_path = None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Dimensions Talent Card : 16,8 cm × 12,3349 cm (template2)
                cm_w, cm_h = 16.8, 14.3349
                inch_w = cm_w / 2.54
                inch_h = cm_h / 2.54
                viewport_w = int(round(inch_w * 96))
                viewport_h = int(round(inch_h * 96))
                page.set_viewport_size({"width": viewport_w, "height": viewport_h})

                local_url = f"http://localhost:{port}/{html_filename}"
                page.goto(local_url, wait_until="networkidle", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=10000)
                page.wait_for_timeout(2000)

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pf:
                    pdf_path = pf.name

                pdf_width_in = f"{inch_w:.3f}in"
                pdf_height_in = f"{inch_h:.3f}in"
                page.pdf(
                    path=pdf_path,
                    print_background=True,
                    width=pdf_width_in,
                    height=pdf_height_in,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                )
                browser.close()

            httpd.shutdown()
            server_thread.join(timeout=2)

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            print(f"✅ PDF Talent Card généré: {len(pdf_bytes)} bytes")

            from minio_storage import get_minio_storage
            from candidate_minio_path import get_candidate_minio_prefix
            minio_storage = get_minio_storage()
            object_name = f"{get_candidate_minio_prefix(candidate_id)}talentcard_html_{candidate_uuid}.pdf"
            success, url, err = minio_storage.upload_file(
                pdf_bytes,
                object_name,
                content_type="application/pdf",
            )
            for path in (temp_html_path, pdf_path):
                try:
                    os.unlink(path)
                except Exception:
                    pass
            if success:
                print(f"✅ PDF Talent Card uploadé vers MinIO: {url}")
                return True, url, None
            return False, None, err or "Erreur upload PDF"

        except Exception as e:
            try:
                httpd.shutdown()
                server_thread.join(timeout=1)
            except Exception:
                pass
            for path in (temp_html_path, pdf_path or ""):
                if path and os.path.isfile(path):
                    try:
                        os.unlink(path)
                    except Exception:
                        pass
            raise e

    except Exception as e:
        error_msg = f"Erreur conversion Talent Card HTML → PDF: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, None, error_msg


def generate_and_save_talent_card_html(
    candidate_id: int,
    candidate_uuid: str,
    candidate_image_url: Optional[str] = None,
    candidate_email: Optional[str] = None,
    candidate_phone: Optional[str] = None,
    candidate_job_title: Optional[str] = None,
    candidate_years_experience: Optional[int] = None,
    candidate_linkedin_url: Optional[str] = None,
    candidate_github_url: Optional[str] = None,
    candidate_behance_url: Optional[str] = None,
    flask_base_url: Optional[str] = None,
    save_to_minio: bool = True,
    generate_pdf: bool = True,
    lang: str = "fr",
    extra_candidate_data: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Génère la Talent Card HTML, la sauvegarde dans MinIO, puis la convertit en PDF et uploade le PDF.

    Args:
        candidate_id: ID du candidat en base de données
        candidate_uuid: UUID du candidat (id_agent)
        candidate_image_url: URL de l'image du candidat (optionnel)
        candidate_email: Email du candidat (optionnel)
        candidate_phone: Téléphone du candidat (optionnel)
        candidate_job_title: Titre du poste (optionnel)
        candidate_years_experience: Années d'expérience (optionnel)
        candidate_linkedin_url: LinkedIn (optionnel)
        candidate_github_url: GitHub (optionnel)
        candidate_behance_url: Behance (optionnel, affiché si pas de GitHub)
        flask_base_url: URL de base du serveur Flask (optionnel)
        save_to_minio: Si True, sauvegarde le HTML dans MinIO
        generate_pdf: Si True, convertit le HTML en PDF et uploade le PDF dans MinIO

    Returns:
        Tuple (success, html_content, minio_html_url, minio_pdf_url, error_message)
    """
    lang = (lang or "fr").lower() if lang else "fr"
    if lang not in ("fr", "en"):
        lang = "fr"
    success, html_content, error = generate_talent_card_html(
        candidate_id=candidate_id,
        candidate_image_url=candidate_image_url,
        candidate_email=candidate_email,
        candidate_phone=candidate_phone,
        candidate_job_title=candidate_job_title,
        candidate_years_experience=candidate_years_experience,
        candidate_uuid=candidate_uuid,
        candidate_linkedin_url=candidate_linkedin_url,
        candidate_github_url=candidate_github_url,
        candidate_behance_url=candidate_behance_url,
        flask_base_url=flask_base_url or "http://localhost:5002",
        lang=lang,
        extra_candidate_data=extra_candidate_data,
    )
    if not success:
        return False, None, None, None, error

    minio_html_url = None
    if save_to_minio:
        save_ok, minio_html_url, save_err = save_portfolio_html(
            html_content,
            candidate_id,
            candidate_uuid,
            version="talent-card",
            lang=lang,
        )
        if not save_ok:
            print(f"⚠️  Erreur sauvegarde HTML Talent Card dans MinIO: {save_err}")

    minio_pdf_url = None
    if generate_pdf and html_content:
        pdf_ok, minio_pdf_url, pdf_err = convert_talent_card_html_to_pdf(
            html_content,
            candidate_id,
            candidate_uuid,
        )
        if not pdf_ok:
            print(f"⚠️  Erreur conversion Talent Card HTML → PDF: {pdf_err}")

    return True, html_content, minio_html_url, minio_pdf_url, None
