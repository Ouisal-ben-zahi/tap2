-- Ajouter la colonne salaire_minimum à la table candidates (souhait du candidat, formulaire HomePage)
-- À exécuter une fois. Si la colonne existe déjà, ignorer l'erreur ou commenter ce script.
USE tap_db;

ALTER TABLE candidates
ADD COLUMN salaire_minimum VARCHAR(50) NULL COMMENT 'Salaire minimum souhaité (ex: 50000, 50k, À discuter)';

SELECT 'Colonne salaire_minimum ajoutée à candidates.' AS status;
