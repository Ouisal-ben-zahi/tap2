-- Migration: Ajouter les colonnes pour les URLs MinIO
-- À exécuter si la table candidates existe déjà

USE tap_db;

ALTER TABLE candidates 
ADD COLUMN IF NOT EXISTS cv_minio_url VARCHAR(500) NULL COMMENT 'URL du CV dans MinIO',
ADD COLUMN IF NOT EXISTS image_minio_url VARCHAR(500) NULL COMMENT 'URL de l\'image dans MinIO',
ADD COLUMN IF NOT EXISTS talentcard_minio_url VARCHAR(500) NULL COMMENT 'URL de la Talent Card dans MinIO';
