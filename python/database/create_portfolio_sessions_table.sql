-- Table pour stocker les sessions de chatbot portfolio
-- Structure simple pour gérer l'état de la conversation

USE tap_db;

CREATE TABLE IF NOT EXISTS portfolio_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL UNIQUE COMMENT 'UUID de la session',
    candidate_id INT NOT NULL COMMENT 'ID du candidat',
    profile JSON NOT NULL COMMENT 'Profil portfolio en cours de construction',
    missing_fields JSON NOT NULL COMMENT 'Liste des champs manquants',
    current_question_key VARCHAR(100) NULL COMMENT 'Clé du champ en cours de collecte',
    current_question TEXT NULL COMMENT 'Question actuelle posée au candidat',
    asked_questions JSON NOT NULL COMMENT 'Historique des questions posées (clés)',
    is_complete BOOLEAN DEFAULT FALSE COMMENT 'True si tous les champs sont remplis',
    extracted_data JSON NULL COMMENT 'Données extraites du CV + Talent Card',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_candidate_id (candidate_id),
    INDEX idx_is_complete (is_complete)
) ENGINE=InnoDB;
