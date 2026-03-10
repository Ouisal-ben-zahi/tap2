-- Table des offres / Job Spec (formulaire recruteur)
CREATE TABLE IF NOT EXISTS jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    niveau_attendu VARCHAR(50) NULL,
    experience_min VARCHAR(50) NULL,
    presence_sur_site VARCHAR(100) NULL,
    reason TEXT NULL,
    main_mission TEXT NULL,
    tasks_other VARCHAR(500) NULL,
    disponibilite VARCHAR(50) NULL,
    salary_min DECIMAL(12,2) NULL,
    salary_max DECIMAL(12,2) NULL,
    urgent TINYINT(1) DEFAULT 0,
    location_type JSON NULL COMMENT '["Casablanca","Rabat",...]',
    tasks JSON NULL COMMENT '["Analyse de données",...]',
    soft_skills JSON NULL COMMENT '["Autonomie","Communication",...]',
    skills JSON NULL COMMENT '[{"name":"Python","level":"Avancé","priority":"Indispensable"},...]',
    languages JSON NULL COMMENT '[{"name":"Français","level":"Courant","importance":"Indispensable"},...]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
