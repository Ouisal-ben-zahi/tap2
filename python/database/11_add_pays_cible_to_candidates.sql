-- Ajouter la colonne pays_cible à la table candidates (pays cible pour la recherche, depuis le formulaire)
USE tap_db;

ALTER TABLE candidates
ADD COLUMN pays_cible VARCHAR(255) NULL COMMENT 'Pays cible pour la recherche (formulaire)';

SELECT 'Colonne pays_cible ajoutée à candidates.' AS status;
