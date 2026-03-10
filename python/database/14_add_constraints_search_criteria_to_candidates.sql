-- Ajouter les colonnes exigences/pré-requis et critères de recherche à la table candidates (formulaire HomePage)
USE tap_db;

ALTER TABLE candidates
ADD COLUMN constraints TEXT NULL COMMENT 'Exigences / pré-requis (salaire, télétravail, localisation...)';

ALTER TABLE candidates
ADD COLUMN search_criteria TEXT NULL COMMENT 'Ce que le candidat recherche (croissance, startup, projets IA...)';

SELECT 'Colonnes constraints et search_criteria ajoutées à candidates.' AS status;
