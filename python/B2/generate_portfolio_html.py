"""
Agent de génération de portfolios HTML
Génère automatiquement les versions HTML (longue et one-page) à partir des données JSON du portfolio
"""

import os
import json
from typing import Dict, Optional, Tuple, List, Any
from jinja2 import Template, Environment, FileSystemLoader
from B2.agent_portfolio import generate_portfolio_content, transform_portfolio_data_for_template


def _dim_score(dims: Dict, key: str) -> Optional[float]:
    v = dims.get(key)
    if isinstance(v, dict) and "score" in v:
        return v.get("score")
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _inject_scoring_into_candidate(candidate: Dict, candidate_id: int) -> None:
    """
    Remplace le score global et les détails (compétences techniques, comportementales, etc.)
    par ceux de l'agent A2 (scoring). La justification reste basée sur les 5 dimensions
    (technique, comportemental, autonomie, apprentissage, comportement pro), pas sur les soft skills déclarés.
    """
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    analyse_path = os.path.join(backend_root, "A2", f"analyse_{candidate_id}.json")
    if not os.path.isfile(analyse_path):
        return
    try:
        with open(analyse_path, "r", encoding="utf-8") as f:
            analyse = json.load(f)
    except Exception as e:
        print(f"⚠️ Impossible de charger A2 analyse pour scoring: {e}")
        return
    scores = analyse.get("scores") or {}
    score_global = scores.get("score_global")
    if score_global is None:
        return
    dims = scores.get("dimensions") or {}
    # Mapping des 6 dimensions A2 vers les 5 dimensions du template (technique, comportemental, autonomie, apprentissage, pro)
    hard_skills = _dim_score(dims, "hard_skills_depth")
    soft_skills = _dim_score(dims, "communication")  # compétences comportementales
    autonomy = _dim_score(dims, "coherence")  # autonomie / cohérence parcours
    learning_ability = _dim_score(dims, "rarete_marche")  # capacité à se différencier
    professional_behavior = _dim_score(dims, "stabilite")  # stabilité / comportement pro
    score_details = {
        "hard_skills": hard_skills,
        "soft_skills": soft_skills,
        "autonomy": autonomy,
        "autonomie": autonomy,
        "learning_ability": learning_ability,
        "professional_behavior": professional_behavior,
    }
    candidate["score_global"] = score_global
    candidate["global_score"] = score_global
    if candidate.get("readiness_score") is None:
        candidate["readiness_score"] = {}
    candidate["readiness_score"]["global_score"] = score_global
    candidate["score_details"] = score_details
    print("✅ Scores A2 injectés (score global + 5 dimensions technique/comportemental)")


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
                     "frontend", "src", "portfolio html", template_name),
        # Depuis le conteneur Docker
        f"/app/frontend/src/portfolio html/{template_name}",
        # Depuis le volume monté
        f"/frontend/src/portfolio html/{template_name}",
        # Depuis le répertoire courant
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "portfolio html", template_name),
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


def _merge_one_page_bilingual(template_data_fr: Dict, template_data_en: Dict, flask_base_url: str, candidate_id: int, candidate_uuid: Optional[str], candidate_image_url: Optional[str], candidate_email: Optional[str], candidate_phone: Optional[str], candidate_job_title: Optional[str], candidate_years_experience: Optional[int], candidate_linkedin_url: Optional[str], candidate_github_url: Optional[str], lang: str) -> Dict:
    """Fusionne les données FR et EN pour la one-page afin que le sélecteur de langue change tout le contenu."""
    c_fr = template_data_fr.get("candidate") or {}
    c_en = template_data_en.get("candidate") or {}
    # Base = langue demandée
    candidate = dict(c_fr if lang == "fr" else c_en)
    candidate["about_text_fr"] = (c_fr.get("about_text") or "").strip()
    candidate["about_text_en"] = (c_en.get("about_text") or "").strip()
    if not candidate.get("about_text"):
        candidate["about_text"] = candidate["about_text_fr"] if lang == "fr" else candidate["about_text_en"]

    def _merge_list(key: str, title_keys: Tuple[str, ...], desc_key: Optional[str] = None):
        list_fr = c_fr.get(key) or []
        list_en = c_en.get(key) or []
        merged = []
        for i in range(max(len(list_fr), len(list_en))):
            a = list_fr[i] if i < len(list_fr) else {}
            b = list_en[i] if i < len(list_en) else {}
            if not isinstance(a, dict):
                a = {}
            if not isinstance(b, dict):
                b = {}
            item = dict(a if lang == "fr" else b)
            for k in title_keys:
                v_fr = a.get(k, a.get("title", a.get("name", a.get("role", ""))))
                v_en = b.get(k, b.get("title", b.get("name", b.get("role", ""))))
                if isinstance(v_fr, dict):
                    v_fr = v_fr.get("name", "") or v_fr.get("title", "")
                if isinstance(v_en, dict):
                    v_en = v_en.get("name", "") or v_en.get("title", "")
                item[k + "_fr"] = (v_fr or "").strip() if v_fr is not None else ""
                item[k + "_en"] = (v_en or "").strip() if v_en is not None else ""
            if desc_key:
                item["description_fr"] = (a.get(desc_key, a.get("description", a.get("context", ""))) or "").strip()
                item["description_en"] = (b.get(desc_key, b.get("description", b.get("context", ""))) or "").strip()
            merged.append(item)
        return merged

    # Formations (learning_growth)
    lg_fr = c_fr.get("learning_growth") or {}
    lg_en = c_en.get("learning_growth") or {}
    formations_fr = lg_fr.get("certifications", []) or lg_fr.get("self_learning", []) or []
    formations_en = lg_en.get("certifications", []) or lg_en.get("self_learning", []) or []
    merged_formations = []
    for i in range(max(len(formations_fr), len(formations_en))):
        a = formations_fr[i] if i < len(formations_fr) else {}
        b = formations_en[i] if i < len(formations_en) else {}
        if not isinstance(a, dict):
            a = {}
        if not isinstance(b, dict):
            b = {}
        name_fr = (a.get("name", a.get("title", "")) or "").strip()
        name_en = (b.get("name", b.get("title", "")) or "").strip()
        org_fr = (a.get("organization", a.get("institution", "")) or "").strip()
        org_en = (b.get("organization", b.get("institution", "")) or "").strip()
        # Fallback : si la version EN est vide, utiliser la FR pour éviter contenu vide au switcher
        if not name_en and name_fr:
            name_en = name_fr
        if not org_en and org_fr:
            org_en = org_fr
        year = a.get("year", b.get("year", ""))
        merged_formations.append({
            "name": name_fr if lang == "fr" else name_en,
            "name_fr": name_fr,
            "name_en": name_en,
            "organization": org_fr if lang == "fr" else org_en,
            "organization_fr": org_fr,
            "organization_en": org_en,
            "year": year,
            "title": name_fr if lang == "fr" else name_en,
            "institution": org_fr if lang == "fr" else org_en,
        })
    candidate["learning_growth"] = {
        "certifications": merged_formations,
        "self_learning": merged_formations,
    }

    # Langues (pour switcher FR/EN : name et level en français et en anglais)
    lang_fr = c_fr.get("languages") or []
    lang_en = c_en.get("languages") or []
    merged_languages = []
    for i in range(max(len(lang_fr), len(lang_en))):
        a = lang_fr[i] if i < len(lang_fr) else {}
        b = lang_en[i] if i < len(lang_en) else {}
        if not isinstance(a, dict):
            a = {}
        if not isinstance(b, dict):
            b = {}
        name_fr = (a.get("name", a.get("language", "")) or "").strip()
        name_en = (b.get("name", b.get("language", "")) or "").strip()
        level_fr = (a.get("level", "") or "").strip()
        level_en = (b.get("level", "") or "").strip()
        if not name_en and name_fr:
            name_en = name_fr
        if not level_en and level_fr:
            level_en = level_fr
        merged_languages.append({
            "name": name_fr if lang == "fr" else name_en,
            "name_fr": name_fr,
            "name_en": name_en,
            "level": level_fr if lang == "fr" else level_en,
            "level_fr": level_fr,
            "level_en": level_en,
        })
    candidate["languages"] = merged_languages

    # Expériences
    exp_fr = c_fr.get("experiences") or []
    exp_en = c_en.get("experiences") or []
    merged_exp = []
    for i in range(max(len(exp_fr), len(exp_en))):
        a = exp_fr[i] if i < len(exp_fr) else {}
        b = exp_en[i] if i < len(exp_en) else {}
        if not isinstance(a, dict):
            a = {}
        if not isinstance(b, dict):
            b = {}
        item = dict(a if lang == "fr" else b)
        item["title_fr"] = (a.get("title", a.get("role", "")) or "").strip()
        item["title_en"] = (b.get("title", b.get("role", "")) or "").strip()
        item["company_fr"] = (a.get("company", a.get("organization", "")) or "").strip()
        item["company_en"] = (b.get("company", b.get("organization", "")) or "").strip()
        item["description_fr"] = (a.get("description", a.get("value_brought", "")) or "").strip()
        item["description_en"] = (b.get("description", b.get("value_brought", "")) or "").strip()
        merged_exp.append(item)
    candidate["experiences"] = merged_exp

    # Projets
    proj_fr = c_fr.get("projects") or []
    proj_en = c_en.get("projects") or []
    merged_proj = []
    for i in range(max(len(proj_fr), len(proj_en))):
        a = proj_fr[i] if i < len(proj_fr) else {}
        b = proj_en[i] if i < len(proj_en) else {}
        if not isinstance(a, dict):
            a = {}
        if not isinstance(b, dict):
            b = {}
        item = dict(a if lang == "fr" else b)
        item["title_fr"] = (a.get("title", a.get("name", "")) or "").strip()
        item["title_en"] = (b.get("title", b.get("name", "")) or "").strip()
        item["description_fr"] = (a.get("description", a.get("context", a.get("value_brought", ""))) or "").strip()
        item["description_en"] = (b.get("description", b.get("context", b.get("value_brought", ""))) or "").strip()
        merged_proj.append(item)
    candidate["projects"] = merged_proj

    # Skill categories : exactement 6 catégories, avec version FR et EN pour le switcher de langue
    skill_categories_fr = (c_fr.get("skill_categories") or [])[:6]
    skill_categories_en = (c_en.get("skill_categories") or [])[:6]
    
    merged_skill_categories = []
    for i in range(6):
        fr_val = skill_categories_fr[i] if i < len(skill_categories_fr) and skill_categories_fr[i] else ""
        en_val = skill_categories_en[i] if i < len(skill_categories_en) and skill_categories_en[i] else ""
        if not en_val and fr_val:
            en_val = fr_val  # fallback: réutiliser le libellé FR si EN vide
        if not fr_val and en_val:
            fr_val = en_val
        merged_skill_categories.append({"fr": fr_val or "", "en": en_val or ""})
    
    if merged_skill_categories:
        candidate["skill_categories"] = merged_skill_categories
    else:
        # Fallback : créer depuis hard_skills si disponible
        hard_skills_fr = c_fr.get("hard_skills") or []
        hard_skills_en = c_en.get("hard_skills") or []
        categories_fr = list({s.get("category", "") for s in hard_skills_fr if isinstance(s, dict) and s.get("category")})[:6]
        categories_en = list({s.get("category", "") for s in hard_skills_en if isinstance(s, dict) and s.get("category")})[:6]
        merged_skill_categories = []
        for i in range(6):
            fr_val = categories_fr[i] if i < len(categories_fr) else ""
            en_val = categories_en[i] if i < len(categories_en) else fr_val
            merged_skill_categories.append({"fr": fr_val, "en": en_val or fr_val})
        candidate["skill_categories"] = merged_skill_categories

    return {"candidate": candidate, "portfolio": template_data_fr.get("portfolio", {})}


def generate_portfolio_html(
    candidate_id: int,
    version: str = "one-page",
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
    candidate_availability: Optional[str] = None,
    candidate_contract_type: Optional[str] = None,
    long_template_path: Optional[str] = None,
    lang: str = "fr"
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Génère le HTML du portfolio à partir des données du candidat.
    
    Args:
        candidate_id: ID du candidat en base de données
        version: Version du portfolio ("one-page" ou "long")
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
        print(f"🔄 Génération du portfolio HTML (version: {version}) pour candidate_id={candidate_id}")
        
        # 1. Générer le contenu du portfolio (JSON brut)
        # one-page : pas besoin de chat_responses (détails projets), CV seul suffit
        require_chat = version != "one-page"
        lang = (lang or "fr").lower() if lang else "fr"
        if lang not in ("fr", "en"):
            lang = "fr"
        template_data_fr: Optional[Dict] = None
        template_data_en: Optional[Dict] = None
        if version == "one-page":
            # One-page : générer FR et EN pour que le sélecteur change tout le contenu
            success_fr, data_fr, err_fr = generate_portfolio_content(
                candidate_id, output_json_path=None, require_chat_responses=False, lang="fr"
            )
            success_en, data_en, err_en = generate_portfolio_content(
                candidate_id, output_json_path=None, require_chat_responses=False, lang="en"
            )
            if not success_fr and not success_en:
                return False, None, f"Erreur génération contenu: {err_fr or err_en}"
            if success_fr:
                template_data_fr = transform_portfolio_data_for_template(
                    data_fr, candidate_image_url=candidate_image_url, candidate_job_title=candidate_job_title,
                    candidate_years_experience=candidate_years_experience, candidate_email=candidate_email,
                    candidate_phone=candidate_phone
                )
            if success_en:
                template_data_en = transform_portfolio_data_for_template(
                    data_en, candidate_image_url=candidate_image_url, candidate_job_title=candidate_job_title,
                    candidate_years_experience=candidate_years_experience, candidate_email=candidate_email,
                    candidate_phone=candidate_phone
                )
            if template_data_fr and template_data_en:
                template_data = _merge_one_page_bilingual(
                    template_data_fr, template_data_en,
                    flask_base_url=flask_base_url or "http://localhost:5002",
                    candidate_id=candidate_id, candidate_uuid=candidate_uuid,
                    candidate_image_url=candidate_image_url, candidate_email=candidate_email,
                    candidate_phone=candidate_phone, candidate_job_title=candidate_job_title,
                    candidate_years_experience=candidate_years_experience,
                    candidate_linkedin_url=candidate_linkedin_url or "",
                    candidate_github_url=candidate_github_url or "",
                    lang=lang
                )
            else:
                template_data = template_data_fr or template_data_en
            print("✅ Contenu du portfolio one-page (FR+EN) généré avec succès")
        else:
            success, portfolio_data, error = generate_portfolio_content(
                candidate_id,
                output_json_path=None,
                require_chat_responses=require_chat,
                use_original_cv=(version == "long"),
                lang=lang
            )
            if not success:
                return False, None, f"Erreur lors de la génération du contenu: {error}"
            print("✅ Contenu du portfolio généré avec succès")
            template_data = transform_portfolio_data_for_template(
                portfolio_data,
                candidate_image_url=candidate_image_url,
                candidate_job_title=candidate_job_title,
                candidate_years_experience=candidate_years_experience,
                candidate_email=candidate_email,
                candidate_phone=candidate_phone
            )
        
        # 2.1 Convertir les URLs MinIO des images de projets en URLs proxy
        if template_data.get("candidate") and template_data["candidate"].get("projects"):
            print(f"🔄 Conversion des URLs d'images pour {len(template_data['candidate']['projects'])} projets...")
            template_data["candidate"]["projects"] = convert_project_images_to_proxy(
                template_data["candidate"]["projects"],
                flask_base_url
            )
        
        # 2.2 Lien de téléchargement du CV (nouveau / corrigé)
        if template_data.get("candidate") and candidate_uuid:
            template_data["candidate"]["cv_download_url"] = (
                f"{flask_base_url.rstrip('/')}/correctedcv/{candidate_uuid}/download?db_candidate_id={candidate_id}"
            )
        elif template_data.get("candidate"):
            template_data["candidate"]["cv_download_url"] = ""
        
        # 2.3 LinkedIn / GitHub / Behance depuis la base (priorité sur les données générées)
        if template_data.get("candidate"):
            if candidate_linkedin_url:
                template_data["candidate"]["linkedin_url"] = candidate_linkedin_url
            if candidate_github_url:
                template_data["candidate"]["github_url"] = candidate_github_url
            if candidate_behance_url:
                template_data["candidate"]["behance_url"] = candidate_behance_url
            # 2.4 Poste cible : disponibilité et type de contrat (choix du candidat au début)
            if candidate_availability:
                template_data["candidate"]["availability"] = candidate_availability
                template_data["candidate"]["disponibilite"] = candidate_availability
            if candidate_contract_type:
                template_data["candidate"]["contract_type"] = candidate_contract_type
                template_data["candidate"]["type_contrat"] = [s.strip() for s in candidate_contract_type.split(",") if s.strip()]
        
        # 2.5 Portfolio long : score global et justification (5 dimensions) issus de l'agent A2
        if version == "long" and template_data.get("candidate"):
            _inject_scoring_into_candidate(template_data["candidate"], candidate_id)
        
        print("✅ Données transformées pour le template")
        
        # 3. Sélectionner le template selon la version
        if version == "one-page":
            template_name = "template_one_page2.html"
        elif version == "long":
            template_name = "portfolio_long_template.html"
        else:
            return False, None, f"Version inconnue: {version}. Utilisez 'one-page' ou 'long'"
        
        # 4. Charger le template (pour "long", privilégier long_template_path si fourni = même fichier que la vue)
        if version == "long" and long_template_path and os.path.isfile(long_template_path):
            template_path = long_template_path
            print(f"✅ Template long explicite utilisé: {template_path}")
        else:
            template_path = get_template_path(template_name)
        
        if not template_path:
            return False, None, f"Template introuvable: {template_name}"
        
        print(f"✅ Template trouvé: {template_path}")
        
        # 5. Lire le template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 6. URL de base pour les assets (images de fond) — le HTML est servi sans chemin de fichier
        assets_base_url = (flask_base_url or "http://localhost:5002").rstrip("/") + "/portfolio/static/"
        # 7. Rendre le template avec Jinja2
        try:
            jinja_template = Template(template_content)
            html_content = jinja_template.render(
                candidate=template_data.get('candidate', {}),
                portfolio=template_data.get('portfolio', {}),
                candidate_id=candidate_id,
                assets_base_url=assets_base_url,
                portfolio_lang=lang
            )
            print(f"✅ Template rendu avec succès (version: {version})")
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
    lang: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Sauvegarde le HTML généré dans MinIO.
    
    Args:
        html_content: Contenu HTML généré
        candidate_id: ID du candidat
        candidate_uuid: UUID du candidat
        version: Version du portfolio ("one-page" ou "long")
        lang: Langue du portfolio ("fr" ou "en"). Si fourni, le fichier est sauvegardé avec ce suffixe.
    
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


def generate_and_save_portfolio_html(
    candidate_id: int,
    candidate_uuid: str,
    version: str = "one-page",
    candidate_image_url: Optional[str] = None,
    candidate_email: Optional[str] = None,
    candidate_phone: Optional[str] = None,
    candidate_job_title: Optional[str] = None,
    candidate_years_experience: Optional[int] = None,
    save_to_minio: bool = True,
    lang: str = "fr"
) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Génère et sauvegarde le portfolio HTML en une seule opération.
    
    Args:
        candidate_id: ID du candidat en base de données
        candidate_uuid: UUID du candidat
        version: Version du portfolio ("one-page" ou "long")
        candidate_image_url: URL de l'image du candidat (optionnel)
        candidate_email: Email du candidat (optionnel)
        candidate_phone: Téléphone du candidat (optionnel)
        candidate_job_title: Titre du poste (optionnel)
        candidate_years_experience: Années d'expérience (optionnel)
        save_to_minio: Si True, sauvegarde dans MinIO
    
    Returns:
        Tuple (success, html_content, minio_url, error_message)
    """
    lang = (lang or "fr").lower() if lang else "fr"
    if lang not in ("fr", "en"):
        lang = "fr"

    # Générer le HTML
    success, html_content, error = generate_portfolio_html(
        candidate_id=candidate_id,
        version=version,
        candidate_image_url=candidate_image_url,
        candidate_email=candidate_email,
        candidate_phone=candidate_phone,
        candidate_job_title=candidate_job_title,
        candidate_years_experience=candidate_years_experience,
        candidate_uuid=candidate_uuid,
        lang=lang
    )
    
    if not success:
        return False, None, None, error
    
    # Sauvegarder dans MinIO si demandé
    minio_url = None
    if save_to_minio:
        save_success, minio_url, save_error = save_portfolio_html(
            html_content,
            candidate_id,
            candidate_uuid,
            version,
            lang=lang
        )
        
        if not save_success:
            print(f"⚠️  Erreur lors de la sauvegarde dans MinIO: {save_error}")
            # On retourne quand même le HTML même si la sauvegarde a échoué
    
    return True, html_content, minio_url, None
