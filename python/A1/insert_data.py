import json
import os
import uuid
from database.connection import DatabaseConnection
from dotenv import load_dotenv

load_dotenv()


def _clean_annees_experience(value):
    if value is None or value == '':
        return None
    
    # Si c'est déjà un entier
    if isinstance(value, int):
        return value
    
    if isinstance(value, str):
        value = value.strip()
        
        if not value:
            return None
        
        try:
            return int(float(value))  # Convertir via float d'abord pour gérer "5.5" -> 5
        except (ValueError, TypeError):
            import re
            numbers = re.findall(r'\d+\.?\d*', value)
            if numbers:
                try:
                    return int(float(numbers[0]))
                except (ValueError, TypeError):
                    pass
    
    return None


def _clean_string_value(value, max_length=None):
    """
    Nettoie une valeur string et la tronque si nécessaire.
    
    Args:
        value: Valeur à nettoyer
        max_length: Longueur maximale (None = pas de limite)
        
    Returns:
        str ou None
    """
    if value is None:
        return None
    
    if not isinstance(value, str):
        value = str(value)
    
    value = value.strip()
    
    if not value:
        return None
    
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    return value


def generate_unique_id_agent():
    """
    Génère un ID agent unique au format A1-XXXXXX (6 caractères alphanumériques).
    Vérifie dans la base de données qu'il n'existe pas déjà.
    
    Returns:
        str: ID agent unique au format A1-XXXXXX
    """
    DatabaseConnection.initialize()
    
    max_attempts = 100  # Limite de tentatives pour éviter une boucle infinie
    
    for _ in range(max_attempts):
        # Générer un ID au format A1-XXXXXX (6 caractères alphanumériques)
        random_part = str(uuid.uuid4()).replace('-', '')[:6].upper()
        id_agent = f"A1-{random_part}"
        
        # Vérifier si l'ID existe déjà dans la base
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT id FROM candidates WHERE id_agent = %s", (id_agent,))
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                # ID unique trouvé
                return id_agent
    
    # Si on n'a pas trouvé d'ID unique après max_attempts tentatives (très improbable)
    raise Exception("Impossible de générer un ID agent unique après plusieurs tentatives")


def create_candidate_record(id_agent: str, user_id: int = None):
    """
    Crée un enregistrement minimal dans la base de données avec l'ID agent généré.
    Si user_id est fourni (candidat connecté), il est enregistré dès le début.

    Args:
        id_agent: ID agent unique au format A1-XXXXXX
        user_id: ID de l'utilisateur connecté (users.id), optionnel

    Returns:
        int: L'ID (candidate_id) du candidat créé
    """
    DatabaseConnection.initialize()

    with DatabaseConnection.get_connection() as db:
        cursor = db.cursor()

        try:
            if user_id is not None:
                sql = """
                    INSERT INTO candidates (id_agent, nom, prenom, user_id)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (id_agent, "À compléter", "À compléter", user_id))
                print(f"✅ Enregistrement candidat créé avec ID agent: {id_agent}, user_id: {user_id} (DB ID: {cursor.lastrowid})")
            else:
                sql = """
                    INSERT INTO candidates (id_agent, nom, prenom)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (id_agent, "À compléter", "À compléter"))
                print(f"✅ Enregistrement candidat créé avec ID agent: {id_agent} (DB ID: {cursor.lastrowid})")

            candidate_id = cursor.lastrowid
            return candidate_id

        except Exception as e:
            print(f"❌ Erreur lors de la création de l'enregistrement candidat: {e}")
            raise
        finally:
            cursor.close()


def insert_talent_card(data: dict, minio_urls: dict = None, candidate_id: int = None):
    """
    Met à jour une Talent Card dans la base de données.
    Si candidate_id est fourni, met à jour l'enregistrement existant.
    Sinon, crée un nouvel enregistrement (comportement de compatibilité).
    
    Args:
        data: Dictionnaire contenant les données de la Talent Card
        minio_urls: Dictionnaire avec les URLs MinIO (cv_url, image_url, talentcard_url)
        candidate_id: ID du candidat à mettre à jour (si None, crée un nouvel enregistrement)
        
    Returns:
        int: L'ID du candidat mis à jour ou inséré, ou None en cas d'erreur
        
    Raises:
        Exception: En cas d'erreur lors de l'insertion/mise à jour
    """
    if minio_urls is None:
        minio_urls = {}
    try:
        # Initialiser la connexion si nécessaire
        DatabaseConnection.initialize()
        
        # Utiliser une connexion pour toute la transaction
        with DatabaseConnection.get_connection() as db:
            cursor = db.cursor()

            try:
                # Nettoyer et convertir les valeurs
                annees_exp = _clean_annees_experience(data.get('annees_experience'))
                print("[DB] Data keys:", list(data.keys()))

                
                if candidate_id:
                    print(f"[DB] Updating candidate {candidate_id} with values:")
                    # Préserver les URLs MinIO existantes si elles ne sont pas fournies dans `minio_urls`.
                    # (Important: certains endpoints ne renvoient que talentcard_url et on ne veut pas écraser cv/image)
                    existing_urls = {"cv_minio_url": None, "image_minio_url": None, "talentcard_minio_url": None, "talentcard_pdf_minio_url": None}
                    try:
                        cursor.execute(
                            "SELECT cv_minio_url, image_minio_url, talentcard_minio_url, talentcard_pdf_minio_url FROM candidates WHERE id = %s",
                            (candidate_id,),
                        )
                        row = cursor.fetchone()
                        if row:
                            existing_urls = {
                                "cv_minio_url": row[0],
                                "image_minio_url": row[1],
                                "talentcard_minio_url": row[2],
                                "talentcard_pdf_minio_url": row[3] if len(row) > 3 else None,
                            }
                    except Exception as e:
                        print(f"⚠️  Impossible de charger les URLs MinIO existantes (candidate_id={candidate_id}): {e}")

                    cv_url_to_save = (
                        _clean_string_value(minio_urls.get("cv_url"), max_length=500)
                        if "cv_url" in minio_urls
                        else _clean_string_value(existing_urls.get("cv_minio_url"), max_length=500)
                    )
                    image_url_to_save = (
                        _clean_string_value(minio_urls.get("image_url"), max_length=500)
                        if "image_url" in minio_urls
                        else _clean_string_value(existing_urls.get("image_minio_url"), max_length=500)
                    )
                    talentcard_url_to_save = (
                        _clean_string_value(minio_urls.get("talentcard_url"), max_length=500)
                        if "talentcard_url" in minio_urls
                        else _clean_string_value(existing_urls.get("talentcard_minio_url"), max_length=500)
                    )
                    talentcard_pdf_url_to_save = (
                        _clean_string_value(minio_urls.get("talentcard_pdf_url"), max_length=500)
                        if "talentcard_pdf_url" in minio_urls
                        else _clean_string_value(existing_urls.get("talentcard_pdf_minio_url"), max_length=500)
                    )

                    categorie = _clean_string_value(data.get('categorie_profil'), max_length=50) or "autre"
                    sql_candidate = """
                        UPDATE candidates
                        SET nom = %s,
                            prenom = %s,
                            titre_profil = %s,
                            categorie_profil = %s,
                            ville = %s,
                            pays = %s,
                            linkedin = %s,
                            github = %s,
                            behance = %s,
                            email = %s,
                            phone = %s,
                            annees_experience = %s,
                            disponibilite = %s,
                            pret_a_relocater = %s,
                            niveau_seniorite = %s,
                            pays_cible = %s,
                            resume_bref = %s,
                            constraints = %s,
                            search_criteria = %s,
                            salaire_minimum = %s,
                            cv_minio_url = %s,
                            image_minio_url = %s,
                            talentcard_minio_url = %s,
                            talentcard_pdf_minio_url = %s
                        WHERE id = %s
                    """

                    val_candidate = (
                        _clean_string_value(data.get('nom'), max_length=100),
                        _clean_string_value(data.get('prenom'), max_length=100),
                        _clean_string_value(data.get('Titre de profil'), max_length=255),
                        categorie,
                        _clean_string_value(data.get('ville'), max_length=100),
                        _clean_string_value(data.get('pays'), max_length=100),
                        _clean_string_value(data.get('linkedin'), max_length=255),
                        _clean_string_value(data.get('github'), max_length=255),
                        _clean_string_value(data.get('behance'), max_length=255),
                        _clean_string_value(data.get('email'), max_length=255),
                        _clean_string_value(data.get('phone'), max_length=20),
                        annees_exp,
                        _clean_string_value(data.get('disponibilite'), max_length=50),
                        _clean_string_value(data.get('pret_a_relocater'), max_length=10),
                        _clean_string_value(data.get('niveau_seniorite') or data.get('niveau de seniorite'), max_length=100),
                        _clean_string_value(data.get('pays_cible') or data.get('target_country'), max_length=255),
                        data.get('resume_bref'),
                        _clean_string_value(data.get('constraints'), max_length=10000),
                        _clean_string_value(data.get('search_criteria'), max_length=10000),
                        _clean_string_value(data.get('salaire_minimum'), max_length=50),
                        cv_url_to_save,
                        image_url_to_save,
                        talentcard_url_to_save,
                        talentcard_pdf_url_to_save,
                        candidate_id
                    )
                    print("[DB] val_candidate:", val_candidate)
                    cursor.execute(sql_candidate, val_candidate)
                    print("[DB] Candidate UPDATE executed, rowcount:", cursor.rowcount)

                    # Suppression des anciennes relations (uniquement si la clé est fournie dans le payload)
                    # Objectif: éviter de "vider" des relations lors d'un update partiel (payload sans skills/experience/etc.)
                    if "skills" in data:
                        cursor.execute("DELETE FROM skills WHERE candidate_id = %s", (candidate_id,))
                        print("[DB] Deleted skills, rowcount:", cursor.rowcount)
                    if "experience" in data:
                        cursor.execute("DELETE FROM experiences WHERE candidate_id = %s", (candidate_id,))
                        print("[DB] Deleted experiences, rowcount:", cursor.rowcount)
                    if "realisations" in data:
                        cursor.execute("DELETE FROM realisations WHERE candidate_id = %s", (candidate_id,))
                        print("[DB] Deleted realisations, rowcount:", cursor.rowcount)
                    if "langues_parlees" in data:
                        cursor.execute("DELETE FROM languages WHERE candidate_id = %s", (candidate_id,))
                        print("[DB] Deleted languages, rowcount:", cursor.rowcount)
                    if "type_contrat" in data:
                        cursor.execute("DELETE FROM contract_types WHERE candidate_id = %s", (candidate_id,))
                        print("[DB] Deleted contract_types, rowcount:", cursor.rowcount)
                
                else:
                    # Comportement de compatibilité : insertion d'un nouvel enregistrement
                    categorie = _clean_string_value(data.get('categorie_profil'), max_length=50) or "autre"
                    sql_candidate = """
                        INSERT INTO candidates 
                        (id_agent, nom, prenom, titre_profil, categorie_profil, ville, pays, linkedin, github, behance, email, phone, annees_experience, disponibilite, pret_a_relocater, niveau_seniorite, pays_cible, resume_bref, constraints, search_criteria, salaire_minimum, cv_minio_url, image_minio_url, talentcard_minio_url, talentcard_pdf_minio_url)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    val_candidate = (
                        _clean_string_value(data.get('id_agent'), max_length=9),
                        _clean_string_value(data.get('nom'), max_length=100),
                        _clean_string_value(data.get('prenom'), max_length=100),
                        _clean_string_value(data.get('Titre de profil'), max_length=255),
                        categorie,
                        _clean_string_value(data.get('ville'), max_length=100),
                        _clean_string_value(data.get('pays'), max_length=100),
                        _clean_string_value(data.get('linkedin'), max_length=255),
                        _clean_string_value(data.get('github'), max_length=255),
                        _clean_string_value(data.get('behance'), max_length=255),
                        _clean_string_value(data.get('email'), max_length=255),
                        _clean_string_value(data.get('phone'), max_length=20),
                        annees_exp,  # INT ou None
                        _clean_string_value(data.get('disponibilite'), max_length=50),
                        _clean_string_value(data.get('pret_a_relocater'), max_length=10),
                        _clean_string_value(data.get('niveau_seniorite') or data.get('niveau de seniorite'), max_length=100),
                        _clean_string_value(data.get('pays_cible') or data.get('target_country'), max_length=255),
                        _clean_string_value(data.get('resume_bref'), max_length=10000),  # TEXT, pas de limite de longueur
                        _clean_string_value(data.get('constraints'), max_length=10000),
                        _clean_string_value(data.get('search_criteria'), max_length=10000),
                        _clean_string_value(data.get('salaire_minimum'), max_length=50),
                        _clean_string_value(minio_urls.get('cv_url'), max_length=500),
                        _clean_string_value(minio_urls.get('image_url'), max_length=500),
                        _clean_string_value(minio_urls.get('talentcard_url'), max_length=500),
                        _clean_string_value(minio_urls.get('talentcard_pdf_url'), max_length=500)
                    )
                    cursor.execute(sql_candidate, val_candidate)
                    
                    # Récupération de l'ID généré pour le candidat
                    candidate_id = cursor.lastrowid

                # 2. Insertion des compétences (Skills)
                if "skills" in data and data['skills']:
                    for skill in data['skills']:
                        if skill:  # Ignorer les compétences vides
                            cursor.execute(
                                "INSERT INTO skills (candidate_id, skill_name) VALUES (%s, %s)", 
                                (candidate_id, skill)
                            )

                # 3. Insertion des expériences
                if "experience" in data and data['experience']:
                    for exp in data['experience']:
                        sql_exp = """
                            INSERT INTO experiences (candidate_id, role, entreprise, periode, description) 
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        cursor.execute(
                            sql_exp, 
                            (
                                candidate_id, 
                                exp.get('Role', ''), 
                                exp.get('entreprise', ''), 
                                exp.get('periode', ''), 
                                exp.get('description', '')
                            )
                        )

                # 4. Insertion des réalisations
                if "realisations" in data and data['realisations']:
                    for real in data['realisations']:
                        if real:  # Ignorer les réalisations vides
                            cursor.execute(
                                "INSERT INTO realisations (candidate_id, description) VALUES (%s, %s)", 
                                (candidate_id, real if isinstance(real, str) else str(real))
                            )

                # 5. Insertion des langues
                if "langues_parlees" in data and data['langues_parlees']:
                    for lang in data['langues_parlees']:
                        if lang:  # Ignorer les langues vides
                            cursor.execute(
                                "INSERT INTO languages (candidate_id, language_name) VALUES (%s, %s)", 
                                (candidate_id, lang)
                            )

                # 6. Insertion des types de contrat
                # Gère si c'est une liste ou une chaîne unique
                contrats = data.get('type_contrat', [])
                if isinstance(contrats, str):
                    contrats = [contrats] if contrats else []
                for c_type in contrats:
                    if c_type:  # Ignorer les types vides
                        cursor.execute(
                            "INSERT INTO contract_types (candidate_id, type_name) VALUES (%s, %s)", 
                            (candidate_id, c_type)
                        )

                # Validation finale (commit automatique via context manager)
                print(f"✅ Candidat {data.get('nom', 'N/A')} inséré avec succès (ID DB: {candidate_id})")
                return candidate_id

            except Exception as err:
                # Rollback automatique via context manager
                print(f"❌ Erreur lors de l'insertion : {err}")
                raise
            finally:
                cursor.close()
                
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données : {e}")
        raise


def insert_talent_card_from_file(json_file_path: str):
    """
    Fonction de compatibilité : charge un fichier JSON et l'insère.
    
    Args:
        json_file_path: Chemin vers le fichier JSON
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return insert_talent_card(data)


# Pour utilisation en ligne de commande
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        insert_talent_card_from_file(json_file)
    else:
        print("Usage: python insert_data.py <path_to_json_file>")