-- Niveau de séniorité attendu pour l'offre (Junior, Intermédiaire, Senior, Lead, Expert)
ALTER TABLE jobs
ADD COLUMN niveau_seniorite VARCHAR(50) NULL DEFAULT NULL
COMMENT 'Junior, Intermédiaire, Senior, Lead, Expert'
AFTER niveau_attendu;
