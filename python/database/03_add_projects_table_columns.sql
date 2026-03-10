-- Migration: Ajouter les colonnes manquantes pour le chatbot intelligent
-- À exécuter après add_projects_table.sql

USE tap_db;

-- Ajouter les colonnes pour stocker les technologies, description détaillée et infos additionnelles
ALTER TABLE candidate_projects
ADD COLUMN IF NOT EXISTS technologies JSON NULL COMMENT 'Liste des technologies/outils utilisés (JSON array)',
ADD COLUMN IF NOT EXISTS detailed_description TEXT NULL COMMENT 'Description détaillée du projet collectée via le chatbot',
ADD COLUMN IF NOT EXISTS additional_info JSON NULL COMMENT 'Informations additionnelles collectées (JSON object)';

-- Mettre à jour le statut pour inclure 'in_progress'
ALTER TABLE candidate_projects
MODIFY COLUMN status ENUM('pending', 'in_progress', 'completed', 'skipped') DEFAULT 'pending';
