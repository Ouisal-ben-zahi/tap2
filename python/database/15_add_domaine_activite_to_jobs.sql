-- Domaine d'activité de l'offre (DATA, DEV, DESIGN, VIDEO, AUTRE) pour filtrer les candidats au matching
ALTER TABLE jobs
ADD COLUMN domaine_activite VARCHAR(20) NULL DEFAULT NULL
COMMENT 'Domaine: DATA, DEV, DESIGN, VIDEO, AUTRE'
AFTER title;
