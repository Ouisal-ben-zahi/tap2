# Migrations Base de Données

## Migration : Ajout des colonnes PDF MinIO

### Date : 2026-01-21

### Fichier : `add_pdf_columns.sql`

### Description
Cette migration ajoute les colonnes nécessaires pour stocker les URLs des fichiers PDF dans MinIO :

1. **Table `candidates`** :
   - `talentcard_pdf_minio_url` : URL du PDF de la Talent Card dans MinIO

2. **Table `corrected_cv_versions`** :
   - Création de la table si elle n'existe pas
   - `corrected_pdf_minio_url` : URL du PDF du CV corrigé dans MinIO

### Instructions d'exécution

```bash
# Se connecter à MySQL
mysql -u root -p

# Exécuter le script de migration
source /chemin/vers/add_pdf_columns.sql

# OU depuis la ligne de commande :
mysql -u root -p tap_db < backend/database/add_pdf_columns.sql
```

### Vérification

```sql
-- Vérifier que les colonnes ont été ajoutées
DESCRIBE candidates;
DESCRIBE corrected_cv_versions;
```

### Rollback

Si vous devez annuler cette migration :

```sql
USE tap_db;

-- Supprimer les colonnes ajoutées
ALTER TABLE candidates DROP COLUMN IF EXISTS talentcard_pdf_minio_url;
ALTER TABLE corrected_cv_versions DROP COLUMN IF EXISTS corrected_pdf_minio_url;
```

## Migration : Mémoire des validations agents (`08_agent_validation_memory.sql`)

### Description
Table `agent_validation_memory` pour que les agents (B1, B2, B3) puissent **apprendre à partir des validations utilisateur** :
- Chaque validation (approved / rejected / needs_revision) avec commentaire est enregistrée
- Lors des prochaines générations, le prompt de l’agent inclut un résumé des retours récents
- Permet l’option « l’agent corrige ses problèmes lui-même » à partir des retours utilisateur

### Exécution

```bash
mysql -u root -p tap_db < backend/database/08_agent_validation_memory.sql
```

### Vérification

```sql
DESCRIBE agent_validation_memory;
```

---

## Notes importantes

- Les colonnes sont créées avec `IF NOT EXISTS` pour éviter les erreurs si elles existent déjà
- Les colonnes acceptent NULL pour la compatibilité avec les enregistrements existants
- La longueur maximale des URLs est de 500 caractères
