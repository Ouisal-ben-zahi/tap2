-- Script pour ajouter les colonnes PDF dans MinIO
USE tap_db;

-- Ajouter la colonne pour le PDF de la Talent Card
ALTER TABLE candidates 
ADD COLUMN IF NOT EXISTS talentcard_pdf_minio_url VARCHAR(500) NULL COMMENT 'URL du PDF de la Talent Card dans MinIO' AFTER talentcard_minio_url;

-- Créer la table corrected_cv_versions si elle n'existe pas
CREATE TABLE IF NOT EXISTS corrected_cv_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    candidate_uuid VARCHAR(50) NOT NULL,
    corrected_cv_minio_url VARCHAR(500) NULL COMMENT 'URL du CV corrigé DOCX dans MinIO',
    corrected_json_minio_url VARCHAR(500) NULL COMMENT 'URL des données JSON dans MinIO',
    corrected_pdf_minio_url VARCHAR(500) NULL COMMENT 'URL du CV corrigé PDF dans MinIO',
    validation_status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending, approved, rejected',
    feedback_comment TEXT NULL,
    version_number INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    INDEX idx_candidate_uuid (candidate_uuid),
    INDEX idx_version (candidate_id, version_number)
) ENGINE=InnoDB;

-- Ajouter la colonne corrected_pdf_minio_url si la table existe déjà
ALTER TABLE corrected_cv_versions 
ADD COLUMN IF NOT EXISTS corrected_pdf_minio_url VARCHAR(500) NULL COMMENT 'URL du CV corrigé PDF dans MinIO' AFTER corrected_json_minio_url;

SELECT 'Colonnes PDF ajoutées avec succès!' AS status;
