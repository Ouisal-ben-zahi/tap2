#!/usr/bin/env python3
"""
Script d'initialisation de la base de données pour une instance MySQL externe.
Ce script exécute tous les fichiers SQL de migration dans l'ordre.

Usage:
    python init_external_mysql.py

Ou depuis le conteneur Docker:
    docker-compose exec backend python database/init_external_mysql.py
"""

import os
import sys
import mysql.connector
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration depuis les variables d'environnement
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', '') or os.getenv('DB_ROOT_PASSWORD', ''),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

DB_NAME = os.getenv('DB_NAME', 'tap_db')

# Ordre d'exécution des fichiers SQL
SQL_FILES = [
    '01_create.sql',
    '02_add_projects_table.sql',
    '03_add_projects_table_columns.sql',
    '04_add_pdf_columns.sql',
    '05_add_minio_columns.sql',
    '06_create_portfolio_sessions_table.sql',
    '07_add_github_to_candidates.sql',
    '09_add_niveau_seniorite_to_candidates.sql',
    '10_add_behance_to_candidates.sql',
    '11_add_pays_cible_to_candidates.sql',
    '12_create_jobs_table.sql',
    '13_add_categorie_profil_to_candidates.sql',
    '14_add_constraints_search_criteria_to_candidates.sql',
    '15_add_domaine_activite_to_jobs.sql',
    '16_candidate_embeddings_matching_feedback.sql',
    '17_add_niveau_seniorite_to_jobs.sql',
    '18_add_categorie_profil_to_jobs.sql',
    '19_create_candidate_postule.sql',
    '20_add_salaire_minimum_to_candidates.sql',
]


def create_database_if_not_exists(conn, db_name):
    """Crée la base de données si elle n'existe pas."""
    cursor = conn.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        print(f"✅ Base de données '{db_name}' créée ou déjà existante")
    except Exception as e:
        print(f"❌ Erreur lors de la création de la base de données: {e}")
        raise
    finally:
        cursor.close()


def execute_sql_file(conn, file_path):
    """Exécute un fichier SQL."""
    print(f"\n📄 Exécution de {file_path.name}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Séparer les commandes SQL (séparées par ';')
        commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
        
        cursor = conn.cursor()
        executed = 0
        
        for command in commands:
            # Ignorer les commentaires seuls
            if command and not command.startswith('--'):
                try:
                    cursor.execute(command)
                    executed += 1
                except mysql.connector.Error as e:
                    # Ignorer certaines erreurs (ex: colonne déjà existante)
                    if 'Duplicate column name' in str(e) or 'already exists' in str(e).lower():
                        print(f"  ⚠️  Avertissement (ignoré): {e}")
                    else:
                        print(f"  ❌ Erreur SQL: {e}")
                        print(f"  Commande: {command[:100]}...")
                        raise
        
        conn.commit()
        cursor.close()
        print(f"  ✅ {executed} commande(s) exécutée(s) avec succès")
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur lors de l'exécution de {file_path.name}: {e}")
        conn.rollback()
        return False


def main():
    """Fonction principale."""
    print("🚀 Initialisation de la base de données TAP dans MySQL externe")
    print("=" * 60)
    print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"User: {DB_CONFIG['user']}")
    print(f"Database: {DB_NAME}")
    print("=" * 60)
    
    # Chemin du répertoire des scripts SQL
    script_dir = Path(__file__).parent
    
    # Se connecter à MySQL (sans spécifier la base de données)
    try:
        print("\n🔌 Connexion à MySQL...")
        conn = mysql.connector.connect(**DB_CONFIG)
        print("✅ Connexion réussie")
    except mysql.connector.Error as e:
        print(f"❌ Erreur de connexion à MySQL: {e}")
        print(f"\nVérifiez vos paramètres dans .env:")
        print(f"  DB_HOST={DB_CONFIG['host']}")
        print(f"  DB_PORT={DB_CONFIG['port']}")
        print(f"  DB_USER={DB_CONFIG['user']}")
        print(f"  DB_PASSWORD={'*' * len(DB_CONFIG['password']) if DB_CONFIG['password'] else '(vide)'}")
        sys.exit(1)
    
    try:
        # Créer la base de données si elle n'existe pas
        create_database_if_not_exists(conn, DB_NAME)
        
        # Sélectionner la base de données
        conn.database = DB_NAME
        
        # Exécuter les fichiers SQL dans l'ordre
        print(f"\n📝 Exécution des scripts de migration...")
        success_count = 0
        
        for sql_file in SQL_FILES:
            file_path = script_dir / sql_file
            
            if not file_path.exists():
                print(f"⚠️  Fichier non trouvé: {sql_file} (ignoré)")
                continue
            
            if execute_sql_file(conn, file_path):
                success_count += 1
            else:
                print(f"\n❌ Échec lors de l'exécution de {sql_file}")
                print("Arrêt de l'initialisation.")
                sys.exit(1)
        
        print("\n" + "=" * 60)
        print(f"✅ Initialisation terminée avec succès!")
        print(f"   {success_count}/{len(SQL_FILES)} fichier(s) exécuté(s)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        sys.exit(1)
    finally:
        conn.close()
        print("\n🔌 Connexion fermée")


if __name__ == '__main__':
    main()
