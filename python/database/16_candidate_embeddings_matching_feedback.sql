-- Embeddings candidats (vecteurs sémantiques pour matching)
-- Stockage JSON (MySQL) ; si passage à PostgreSQL, migrer vers pgvector.
CREATE TABLE IF NOT EXISTS candidate_embeddings (
    candidate_id INT NOT NULL PRIMARY KEY,
    embedding JSON NOT NULL COMMENT 'Vecteur [float, ...] du modèle sentence-transformers',
    model_version VARCHAR(128) NOT NULL DEFAULT 'paraphrase-multilingual-MiniLM-L12-v2',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Feedback recruteur (sélectionné / rejeté) pour apprentissage
CREATE TABLE IF NOT EXISTS matching_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    candidate_id INT NOT NULL,
    decision VARCHAR(20) NOT NULL COMMENT 'selected | rejected',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_job (job_id),
    INDEX idx_candidate (candidate_id),
    INDEX idx_decision (decision),
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'Tables candidate_embeddings et matching_feedback créées.' AS status;
