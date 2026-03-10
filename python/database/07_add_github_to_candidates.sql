-- Ajouter la colonne GitHub à la table candidates (saisie formulaire initial)
USE tap_db;

-- Exécuter une seule fois. Si la colonne existe déjà, ignorer l'erreur.
ALTER TABLE candidates
ADD COLUMN github VARCHAR(255) NULL COMMENT 'URL GitHub du candidat' AFTER linkedin;

SELECT 'Colonne github ajoutée à candidates (si elle n''existait pas).' AS status;
