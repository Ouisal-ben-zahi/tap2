-- Catégorie profil de l'offre (dev, data, design, video, autre) pour matching exact avec candidats.categorie_profil
ALTER TABLE jobs
ADD COLUMN categorie_profil VARCHAR(50) NULL DEFAULT NULL
COMMENT 'dev, data, data_analyst, design, video, autre - même valeurs que candidates'
AFTER domaine_activite;
