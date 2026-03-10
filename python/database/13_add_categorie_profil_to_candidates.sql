-- Ajouter la colonne categorie_profil à la table candidates.
-- Valeurs attendues: dev, data, data_analyst, design, video, autre (pour regroupement logique et dossiers MinIO).

USE tap_db;

ALTER TABLE candidates
ADD COLUMN categorie_profil VARCHAR(50) NULL
COMMENT 'Catégorie de profil: dev, data, data_analyst, design, video, autre'
AFTER titre_profil;

SELECT 'Colonne categorie_profil ajoutée à candidates.' AS status;
