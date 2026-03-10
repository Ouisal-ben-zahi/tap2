-- Migration: Ajouter la table pour stocker les projets et leurs liens/images
-- À exécuter si la table candidates existe déjà

USE tap_db;

-- Table pour stocker les projets identifiés depuis le CV
CREATE TABLE IF NOT EXISTS candidate_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    project_name VARCHAR(255) NOT NULL COMMENT 'Nom du projet identifié',
    project_description TEXT COMMENT 'Description du projet extraite du CV',
    github_url VARCHAR(500) NULL COMMENT 'Lien GitHub du projet',
    demo_url VARCHAR(500) NULL COMMENT 'Lien de démo/live du projet',
    image_urls JSON NULL COMMENT 'Tableau JSON des URLs des images du projet',
    additional_links JSON NULL COMMENT 'Tableau JSON des liens supplémentaires',
    status ENUM('pending', 'completed', 'skipped') DEFAULT 'pending' COMMENT 'Statut de collecte',
    notes TEXT NULL COMMENT 'Notes additionnelles du candidat',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    INDEX idx_candidate_id (candidate_id),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- Table pour stocker l'historique de conversation du chatbot
CREATE TABLE IF NOT EXISTS chatbot_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    session_id VARCHAR(36) NOT NULL COMMENT 'UUID de la session de conversation',
    message_type ENUM('question', 'answer', 'system') NOT NULL,
    message_content TEXT NOT NULL,
    project_id INT NULL COMMENT 'ID du projet concerné si applicable',
    metadata JSON NULL COMMENT 'Métadonnées additionnelles (liens extraits, etc.)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES candidate_projects(id) ON DELETE SET NULL,
    INDEX idx_candidate_id (candidate_id),
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;
