-- Ajouter la colonne Behance à la table candidates (lien portfolio design, affiché sur la Talent Card si pas de GitHub)
USE tap_db;

-- Exécuter une seule fois. Si la colonne existe déjà, ignorer l'erreur.
ALTER TABLE candidates
ADD COLUMN behance VARCHAR(255) NULL COMMENT 'URL Behance du candidat' AFTER github;

SELECT 'Colonne behance ajoutée à candidates (si elle n''existait pas).' AS status;
