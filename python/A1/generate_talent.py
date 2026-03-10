from A1.ocr import extract_text_from_pdf_bytes
import os
import json
import re
import google.generativeai as genai
import uuid
from io import BytesIO

try:
    import qrcode
    _QR_AVAILABLE = True
except ImportError:
    _QR_AVAILABLE = False


def _make_qr_image_bytes(url: str, box_size: int = 4) -> bytes | None:
    """Génère une image QR code en PNG (bytes) pour l'URL donnée. Retourne None si échec."""
    if not url or not _QR_AVAILABLE:
        return None
    try:
        qr = qrcode.QRCode(version=1, box_size=box_size, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"⚠️ Génération QR code échouée: {e}")
        return None


def safe_json_load(text: str) -> dict:
    """
    Nettoie la réponse Gemini et extrait le JSON proprement
    """
    text = text.strip()
    text = re.sub(r"^```json", "", text)
    text = re.sub(r"```$", "", text)
    return json.loads(text)


def is_internship_or_stage(exp: dict) -> bool:
    """
    Détermine si une expérience est un stage (internship) et doit être exclue du calcul.
    
    Args:
        exp: Dictionnaire d'expérience avec clés 'Role', 'role', 'entreprise', 'description'
    
    Returns:
        True si c'est un stage, False sinon
    """
    if not isinstance(exp, dict):
        return False
    
    # Mots-clés indiquant un stage (en français et anglais)
    stage_keywords = [
        'stage', 'stages', 'stagiaire', 'stagiaires',
        'internship', 'intern', 'interns', 'internship program',
        'alternance', 'alternant', 'alternante',
        'apprenti', 'apprentie', 'apprentissage',
        'pfe', 'projet de fin d\'études', 'mémoire',
        'trainee', 'traineeship'
    ]
    
    # Vérifier dans le rôle
    role = (exp.get('Role', '') or exp.get('role', '') or '').lower()
    if any(keyword in role for keyword in stage_keywords):
        return True
    
    # Vérifier dans l'entreprise (certaines entreprises sont connues pour les stages)
    entreprise = (exp.get('entreprise', '') or exp.get('company', '') or '').lower()
    if any(keyword in entreprise for keyword in stage_keywords):
        return True
    
    # Vérifier dans la description
    description = (exp.get('description', '') or exp.get('Description', '') or '').lower()
    if any(keyword in description for keyword in stage_keywords):
        return True
    
    # Vérifier la durée : si moins de 6 mois, c'est probablement un stage
    periode = (exp.get('periode', '') or exp.get('period', '') or '').strip()
    if periode:
        # Essayer d'extraire les dates pour vérifier la durée
        match = re.search(r'(\d{4})[\s\-/]+(\d{4})', periode)
        if match:
            try:
                start_year = int(match.group(1))
                end_year = int(match.group(2))
                # Si moins de 6 mois d'écart, probablement un stage
                if end_year == start_year:
                    # Même année, vérifier si c'est un stage court
                    # On considère que si c'est moins de 6 mois, c'est suspect
                    # Mais on ne peut pas le déterminer sans les mois, donc on garde
                    pass
            except:
                pass
    
    return False


def calculate_years_experience_from_dates(experiences: list) -> int:
    """
    Calcule automatiquement les années d'expérience totales à partir des dates des expériences.
    Gère les chevauchements et calcule la durée totale réelle.
    EXCLUT les stages (internships) du calcul.
    
    Args:
        experiences: Liste de dictionnaires avec clés 'periode' ou 'date_start'/'date_end'
    
    Returns:
        Nombre total d'années d'expérience (entier), excluant les stages
    """
    if not experiences or not isinstance(experiences, list):
        return 0
    
    # Filtrer les stages
    professional_experiences = []
    for exp in experiences:
        if not isinstance(exp, dict):
            continue
        # Exclure les stages
        if not is_internship_or_stage(exp):
            professional_experiences.append(exp)
    
    # Si toutes les expériences sont des stages, retourner 0
    if not professional_experiences:
        return 0
    
    periods = []
    
    for exp in professional_experiences:
        # Essayer de récupérer la période depuis 'periode' ou 'date_start'/'date_end'
        periode = exp.get('periode', '') or exp.get('period', '') or ''
        date_start = exp.get('date_start', '') or exp.get('start_date', '')
        date_end = exp.get('date_end', '') or exp.get('end_date', '') or ''
        
        start_date = None
        end_date = None
        
        # Si on a date_start et date_end directement
        if date_start and date_end:
            try:
                # Essayer différents formats de date
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%Y', '%Y-%m', '%Y']:
                    try:
                        start_date = datetime.strptime(str(date_start).strip(), fmt)
                        break
                    except:
                        continue
                
                if date_end.lower() not in ['présent', 'present', 'now', 'actuel', 'current', '']:
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%Y', '%Y-%m', '%Y']:
                        try:
                            end_date = datetime.strptime(str(date_end).strip(), fmt)
                            break
                        except:
                            continue
                else:
                    end_date = datetime.now()
            except:
                pass
        
        # Sinon, parser depuis 'periode' (ex: "2014-2016", "Jan 2018 - Dec 2023")
        if not start_date and periode:
            # Patterns communs: "2014-2016", "2018-2023", "Jan 2018 - Dec 2023", "2014/2016"
            periode_clean = periode.strip()
            
            # Pattern: "YYYY-YYYY" ou "YYYY/YYYY"
            match = re.search(r'(\d{4})[\s\-/]+(\d{4})', periode_clean)
            if match:
                try:
                    start_year = int(match.group(1))
                    end_year = int(match.group(2))
                    start_date = datetime(start_year, 1, 1)
                    end_date = datetime(end_year, 12, 31)
                except:
                    pass
            
            # Pattern: "YYYY - présent" ou "YYYY - present"
            if not start_date:
                match = re.search(r'(\d{4})[\s\-]+(présent|present|now|actuel|current)', periode_clean, re.IGNORECASE)
                if match:
                    try:
                        start_year = int(match.group(1))
                        start_date = datetime(start_year, 1, 1)
                        end_date = datetime.now()
                    except:
                        pass
            
            # Pattern: année seule "2016"
            if not start_date:
                match = re.search(r'\b(\d{4})\b', periode_clean)
                if match:
                    try:
                        year = int(match.group(1))
                        start_date = datetime(year, 1, 1)
                        end_date = datetime(year, 12, 31)
                    except:
                        pass
        
        if start_date:
            if not end_date:
                end_date = datetime.now()
            periods.append((start_date, end_date))
    
    if not periods:
        return 0
    
    # Fusionner les périodes qui se chevauchent
    periods.sort(key=lambda x: x[0])
    merged = []
    
    for start, end in periods:
        if not merged:
            merged.append((start, end))
        else:
            last_start, last_end = merged[-1]
            if start <= last_end:
                # Chevauchement: fusionner
                merged[-1] = (last_start, max(last_end, end))
            else:
                # Pas de chevauchement: ajouter
                merged.append((start, end))
    
    # Calculer la durée totale en années
    total_days = 0
    for start, end in merged:
        delta = end - start
        total_days += delta.days
    
    # Convertir en années (approximation: 365.25 jours/an pour tenir compte des années bissextiles)
    total_years = total_days / 365.25
    
    # Arrondir à l'entier le plus proche
    return max(0, int(round(total_years)))


def generate_talent_card(
    form_info: dict,
    cv_bytes: bytes,
    img_bytes: bytes = None,
    id_agent: str = None,
    recruit_url: str = None,
    lang: str = "fr",
):
    # Utiliser cv_bytes si fourni, sinon utiliser le fichier par défaut (pour compatibilité)
    if cv_bytes:
        pdf_bytes = cv_bytes
    else:
        print(f"❌ Fichier introuvable : {cv_bytes}")
        return None

    # Extraction avec fallback OCR pour les PDFs Canva ou images
    text = ""
    warnings = []
    try:
        text, warnings = extract_text_from_pdf_bytes(pdf_bytes)
        if warnings:
            print(f"⚠️  Extraction PDF warnings: {warnings}")
    except Exception as e:
        print(f"⚠️  Extraction texte PDF échouée: {e}")
    
    # Fallback OCR si pas assez de texte (PDFs Canva, images scannées, etc.)
    # Utiliser OCR si le texte extrait est vide ou très court (< 200 caractères)
    text_stripped = text.strip() if text else ""
    if not text_stripped or len(text_stripped) < 200:
        print(f"📸 Texte extrait insuffisant ({len(text_stripped)} chars), utilisation de l'OCR...")
        try:
            from A1.ocr import ocr_pdf_bytes
            ocr_res = ocr_pdf_bytes(pdf_bytes, lang="fra+eng")
            if ocr_res.warnings:
                print(f"⚠️  OCR PDF warnings: {ocr_res.warnings}")
            ocr_text = (ocr_res.text or "").strip()
            if ocr_text:
                # Utiliser le texte OCR si il est meilleur que l'extraction normale
                if len(ocr_text) > len(text_stripped):
                    text = ocr_text
                    print(f"✅ OCR réussi: {len(ocr_text)} caractères extraits (vs {len(text_stripped)} avec extraction normale)")
                else:
                    print(f"✅ OCR a extrait {len(ocr_text)} caractères")
                    # Utiliser OCR même si moins de caractères car peut être de meilleure qualité
                    if not text_stripped:
                        text = ocr_text
        except Exception as e:
            print(f"⚠️  OCR PDF échoué (fallback): {e}")
            if not text_stripped:
                raise RuntimeError(f"Impossible d'extraire le texte du CV: extraction normale et OCR ont échoué. Erreur OCR: {e}")
    
    text = text.strip() if text else ""
    
    if not text:
        raise RuntimeError("Impossible d'extraire le texte du CV. Le fichier peut être corrompu ou être une image sans texte.")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY manquant")
        return None

    genai.configure(api_key=api_key)

    lang = (lang or "fr").lower()
    if lang not in ("fr", "en"):
        lang = "fr"
    lang_instruction_fr = "LANGUE DE SORTIE : Tu dois écrire TOUT le contenu de la Talent Card (nom, titre, skills, expériences, réalisations, resume_bref, analyse, etc.) en FRANÇAIS.\n\n"
    lang_instruction_en = "OUTPUT LANGUAGE: You must write ALL Talent Card content (name, title, skills, experiences, achievements, resume_bref, analysis, etc.) in ENGLISH.\n\n"
    lang_instruction = lang_instruction_en if lang == "en" else lang_instruction_fr

    # Modèle depuis .env : GOOGLE_MODEL
    model_name = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
    model = genai.GenerativeModel(model_name)

    prompt = f"""
        {lang_instruction}Tu es un expert Tech Recruiter IA.

        Analyse le CV ci-dessous et les reponse donnees par le candidat génère UNE Talent Card STRICTEMENT en JSON.

        ### CV
        {text}

        ### INFOS FORMULAIRES
        {form_info}

        ### FORMAT JSON OBLIGATOIRE
        {{
        "nom": "",
        "prenom": "",
        "Titre de profil": "",
        "ville": "",
        "pays": "",
        "linkedin": "",
        "skills": ["", "", "", "", "", ""],
        "experience": [
            {{
            "Role": "",
            "entreprise": "",
            "periode": "",
            "description": "1 ligne maximum de contexte"
            }}
        ],
        "realisations": ["2 à 3 réalisations maximum avec résultats chiffrés si possible"],
        "type_contrat": ["CDI", "CDD", "Stage", "Freelance", "Mission"] ou "CDI" (peut être une liste ou une chaîne unique),
        "annees_experience": 0 (UNIQUEMENT un nombre entier, pas de texte. Ex: 0, 1, 2, 3, 5, 10),
        "langues_parlees": [],
        "disponibilite": "immédiate / X semaines",
        "pret_a_relocater": "",
        "niveau de seniorite": "",
        "email": "",
        "phone": "",
        "resume_bref": "1 phrase unique: Rôle + spécialité principale + secteur + valeur apportée (2 lignes max)",
        "analyse": "Analyse complète du CV : points forts du profil, lacunes/points d'amélioration, informations manquantes ou à compléter, recommandations pour améliorer le CV. Format : texte structuré en 2-3 paragraphes (5-10 lignes maximum)",
        }}

      
        RÈGLES STRICTES:
        - skills (OBLIGATOIRE): EXACTEMENT 6 catégories (domaines) de compétences. Ces valeurs sont insérées en base sous forme de catégories. Chaque élément du tableau doit être un NOM DE DOMAINE GÉNÉRAL (catégorie), pas une compétence technique précise. Tu DOIS retourner exactement 6 catégories dans le tableau "skills", pas plus, pas moins. Rédige les libellés dans la langue de sortie (FR ou EN). Exemples en français : "Analyse de données", "Machine Learning", "Frontend", "Backend", "Base de données", "Cloud". Exemples en anglais : "Data Analysis", "Machine Learning", "Frontend", "Backend", "Databases", "Cloud Computing".
        - experience: 2 à 4 expériences maximum
        - realisations: 2 à 3 maximum, uniquement si données disponibles (sinon tableau vide)
        - resume_bref: 1 phrase structurée, maximum 2 lignes
        - Aucun champ vide ne doit être affiché dans le rendu final
        - annees_experience: UNIQUEMENT un nombre entier (0, 1, 2, 3, etc.). 
        IMPORTANT: N'inclus PAS les stages (stages, internships, alternances, apprentissages, PFE) dans le calcul.
        Analyse chaque période (periode) dans chaque expérience PROFESSIONNELLE (hors stages) et additionne les durées. 
        Si une période dit "présent" ou "now", utilise la date actuelle comme fin.
        Si le candidat n'a QUE des stages, mettre 0. JAMAIS de texte descriptif.
        - disponibilite: Utiliser la valeur fournie dans les INFOS FORMULAIRES si disponible, sinon extraire du CV ou mettre "Non spécifiée"
        - type_contrat: Utiliser la valeur fournie dans les INFOS FORMULAIRES si disponible
        - niveau de seniorite: Utiliser la valeur fournie dans les INFOS FORMULAIRES si disponible

        NE RÉPONDS QU'EN JSON.
        """

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    )



    try:
        parsed = safe_json_load(response.text)
    except Exception as e:
        print("❌ JSON invalide généré par Gemini")
        print(response.text)
        return None

    # Compétences : en base on stocke "skills" (catégories). Accepter "skill" ou "skills" du modèle.
    if "skill" in parsed and "skills" not in parsed:
        parsed["skills"] = parsed.pop("skill", []) or []
    if "skills" not in parsed:
        parsed["skills"] = []
    if not isinstance(parsed["skills"], list):
        parsed["skills"] = [s for s in (parsed["skills"] or "").split(",") if s.strip()] if parsed["skills"] else []
    # Limiter à 6 catégories pour cohérence avec le prompt
    parsed["skills"] = [str(s).strip() for s in parsed["skills"] if s][:6]

    # VALIDATION ET CORRECTION AUTOMATIQUE DES ANNÉES D'EXPÉRIENCE
    # Calculer automatiquement depuis les dates des expériences (en excluant les stages)
    experiences = parsed.get('experience', [])
    
    # Compter les stages exclus
    stages_count = sum(1 for exp in experiences if isinstance(exp, dict) and is_internship_or_stage(exp))
    professional_count = len(experiences) - stages_count
    
    calculated_years = calculate_years_experience_from_dates(experiences)
    ai_years = parsed.get('annees_experience', 0)
    
    # Nettoyer la valeur de l'IA (peut être string, float, etc.)
    try:
        if isinstance(ai_years, str):
            ai_years = int(re.search(r'\d+', str(ai_years)).group()) if re.search(r'\d+', str(ai_years)) else 0
        else:
            ai_years = int(float(ai_years)) if ai_years else 0
    except:
        ai_years = 0
    
    # Log des stages exclus
    if stages_count > 0:
        print(f"ℹ️  Stages exclus du calcul: {stages_count} stage(s) détecté(s) et exclu(s)")
        print(f"   - Expériences professionnelles comptées: {professional_count}")
    
    # Utiliser la valeur de l'IA (pas de correction automatique par le calcul des dates)
    parsed['annees_experience'] = ai_years
    if stages_count > 0 and professional_count == 0:
        print(f"ℹ️  Aucune expérience professionnelle: {stages_count} stage(s) détecté(s) mais non compté(s) dans les années d'expérience")
    print(f"✅ Années d'expérience (valeur IA): {ai_years} ans (calcul depuis dates: {calculated_years} ans, {len(experiences)} exp. dont {stages_count} stage(s) exclu(s))")

    if id_agent:
        parsed['id_agent'] = id_agent

    # Normaliser categorie_profil (valeurs: dev, data, data_analyst, design, video, autre)
    from candidate_minio_path import normalize_categorie_profil
    parsed['categorie_profil'] = normalize_categorie_profil(parsed.get('categorie_profil'))

    agent_explanation = """🤖 Agent A1 - Génération de la Talent Card

1️⃣ Analyse de ton CV : Extraction des informations (identité, domaine, compétences, disponibilité).
2️⃣ Talent Card : Carte synthétique (HTML puis PDF) pour le recruteur : nom, expertise, années d'expérience, compétences, contact.
3️⃣ Sauvegarde : Ta Talent Card est prête à être révisée et validée."""

    return {
        "talentcard": parsed,
        "agent_explanation": agent_explanation,
    }

