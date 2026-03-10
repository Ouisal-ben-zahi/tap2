-- Table des candidats validés par le recruteur (par offre)
-- Permet de sauvegarder quels candidats ont été retenus pour chaque job.
CREATE TABLE IF NOT EXISTS recruiter_validated_candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    candidate_id INT NOT NULL,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note TEXT NULL COMMENT 'Note optionnelle du recruteur',
    UNIQUE KEY uk_job_candidate (job_id, candidate_id),
    INDEX idx_job (job_id),
    INDEX idx_candidate (candidate_id),
    INDEX idx_validated_at (validated_at),
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT 'Candidats validés par le recruteur pour chaque offre';

SELECT 'Table recruiter_validated_candidates créée.' AS status;
