#!/bin/bash
# Script d'initialisation de la base de données
# Ce script est exécuté automatiquement par MySQL au démarrage
# Les fichiers SQL dans /docker-entrypoint-initdb.d/ sont exécutés dans l'ordre alphabétique

echo "🚀 Initialisation de la base de données TAP..."

# Attendre que MySQL soit prêt
until mysqladmin ping -h localhost --silent; do
  echo "⏳ En attente de MySQL..."
  sleep 2
done

echo "✅ MySQL est prêt!"

# Les fichiers SQL seront exécutés automatiquement par MySQL
# Ordre d'exécution:
# 1. create.sql
# 2. add_projects_table.sql
# 3. add_projects_table_columns.sql
# 4. add_pdf_columns.sql
# 5. add_minio_columns.sql
# 6. create_portfolio_sessions_table.sql

echo "📝 Exécution des scripts SQL d'initialisation..."
