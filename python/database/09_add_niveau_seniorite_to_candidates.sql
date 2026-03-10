-- Ajouter la colonne niveau_seniorite à la table candidates (Junior, Mid, Senior, Lead, etc.)
-- À exécuter une fois si la table candidates n'a pas encore cette colonne.

USE tap_db;

ALTER TABLE candidates
ADD COLUMN niveau_seniorite VARCHAR(100) NULL
COMMENT 'Niveau de séniorité (formulaire ou extrait du CV)'
AFTER pret_a_relocater;

SELECT 'Colonne niveau_seniorite ajoutée à candidates.' AS status;
