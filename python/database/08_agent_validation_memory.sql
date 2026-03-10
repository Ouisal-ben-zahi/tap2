-- Mémoire des validations utilisateur pour que les agents puissent apprendre
-- (option : l'agent corrige ses problèmes à partir des retours utilisateur)
-- Usage : B1 (CV corrigé), puis B2/B3 si besoin

USE tap_db;

CREATE TABLE IF NOT EXISTS agent_validation_memory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_id VARCHAR(20) NOT NULL COMMENT 'Ex: B1, B2, B3',
    validation_status VARCHAR(30) NOT NULL COMMENT 'approved, rejected, needs_revision',
    feedback_comment TEXT NULL COMMENT 'Commentaire de l''utilisateur pour amélioration',
    candidate_id INT NULL COMMENT 'Optionnel : candidat concerné',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_agent_id (agent_id),
    INDEX idx_created_at (created_at),
    INDEX idx_agent_created (agent_id, created_at)
) ENGINE=InnoDB;

SELECT 'Table agent_validation_memory créée.' AS status;
