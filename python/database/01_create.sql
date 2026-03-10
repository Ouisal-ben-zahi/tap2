-- Script d'initialisation principal de la base de données TAP
-- Ce fichier est exécuté en premier par MySQL

CREATE DATABASE IF NOT EXISTS tap_db;
USE tap_db;

-- 1. Table principale des candidats
CREATE TABLE candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_agent VARCHAR(9) NOT NULL UNIQUE, -- Format A1-XXXXXX
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    titre_profil VARCHAR(255),
    ville VARCHAR(100),
    pays VARCHAR(100),
    linkedin VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(20),
    annees_experience INT,
    disponibilite VARCHAR(50),
    pret_a_relocater VARCHAR(10), -- "Oui", "Non", "À discuter"
    resume_bref TEXT,
    cv_minio_url VARCHAR(500) NULL COMMENT 'URL du CV dans MinIO',
    image_minio_url VARCHAR(500) NULL COMMENT 'URL de l\'image dans MinIO',
    talentcard_minio_url VARCHAR(500) NULL COMMENT 'URL de la Talent Card dans MinIO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. Table des expériences (Relation One-to-Many)
CREATE TABLE experiences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    role VARCHAR(255),
    entreprise VARCHAR(255),
    periode VARCHAR(100),
    description TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 3. Table des compétences (Tags)
CREATE TABLE skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    skill_name VARCHAR(50),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. Table des réalisations
CREATE TABLE realisations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    description TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. Table des langues parlées
CREATE TABLE languages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    language_name VARCHAR(50),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 6. Table des types de contrats (car un candidat peut en accepter plusieurs)
CREATE TABLE contract_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    type_name VARCHAR(50), -- CDI, Freelance, Mission
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB;
