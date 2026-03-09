-- ============================================
-- TAP_DB - Supabase PostgreSQL Migration
-- Converted from MariaDB
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLE: users
-- ============================================
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL CHECK (role IN ('candidat', 'recruteur')),
  is_verified BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLE: candidates
-- ============================================
CREATE TABLE candidates (
  id SERIAL PRIMARY KEY,
  id_agent VARCHAR(9) NOT NULL UNIQUE,
  nom VARCHAR(100) NOT NULL,
  prenom VARCHAR(100) NOT NULL,
  titre_profil VARCHAR(255),
  categorie_profil VARCHAR(50),
  ville VARCHAR(100),
  pays VARCHAR(100),
  linkedin VARCHAR(255),
  github VARCHAR(255),
  behance VARCHAR(255),
  email VARCHAR(255),
  phone VARCHAR(20),
  annees_experience INT,
  disponibilite VARCHAR(50),
  pret_a_relocater VARCHAR(10),
  niveau_seniorite TEXT,
  resume_bref TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cv_minio_url VARCHAR(500),
  image_minio_url VARCHAR(500),
  talentcard_minio_url VARCHAR(500),
  talentcard_pdf_minio_url VARCHAR(500),
  portfolio_url_json VARCHAR(500),
  candidate_uuid VARCHAR(36) DEFAULT NULL,
  portfolio_json_minio_url VARCHAR(500),
  portfolio_pdf_minio_url VARCHAR(500),
  pays_cible VARCHAR(255),
  constraints TEXT,
  search_criteria TEXT,
  salaire_minimum VARCHAR(50),
  user_id INT REFERENCES users(id)
);

-- ============================================
-- TABLE: jobs
-- ============================================
CREATE TABLE jobs (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  categorie_profil VARCHAR(50),
  niveau_attendu VARCHAR(50),
  experience_min VARCHAR(50),
  presence_sur_site VARCHAR(100),
  reason TEXT,
  main_mission TEXT,
  tasks_other VARCHAR(500),
  disponibilite VARCHAR(50),
  salary_min NUMERIC(12, 2),
  salary_max NUMERIC(12, 2),
  urgent BOOLEAN DEFAULT FALSE,
  location_type JSONB,
  tasks JSONB,
  soft_skills JSONB,
  skills JSONB,
  languages JSONB,
  contrat VARCHAR(20) DEFAULT 'stage',
  niveau_seniorite VARCHAR(20),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  entreprise VARCHAR(50),
  user_id INT REFERENCES users(id)
);

-- ============================================
-- TABLE: agent_validation_memory
-- ============================================
CREATE TABLE agent_validation_memory (
  id SERIAL PRIMARY KEY,
  agent_id VARCHAR(20) NOT NULL,
  validation_status VARCHAR(30) NOT NULL,
  feedback_comment TEXT,
  candidate_id INT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_id ON agent_validation_memory(agent_id);
CREATE INDEX idx_avm_created_at ON agent_validation_memory(created_at);
CREATE INDEX idx_agent_created ON agent_validation_memory(agent_id, created_at);

-- ============================================
-- TABLE: candidate_postule
-- ============================================
CREATE TABLE candidate_postule (
  id SERIAL PRIMARY KEY,
  job_id INT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  validated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  note TEXT,
  validate BOOLEAN DEFAULT FALSE,
  UNIQUE (job_id, candidate_id)
);

CREATE INDEX idx_cp_job ON candidate_postule(job_id);
CREATE INDEX idx_cp_candidate ON candidate_postule(candidate_id);
CREATE INDEX idx_cp_validated_at ON candidate_postule(validated_at);

-- ============================================
-- TABLE: candidate_projects
-- ============================================
CREATE TABLE candidate_projects (
  id SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  project_name VARCHAR(255) NOT NULL,
  project_description TEXT,
  github_url VARCHAR(500),
  demo_url VARCHAR(500),
  image_urls JSONB,
  additional_links JSONB,
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped')),
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  technologies JSONB,
  detailed_description TEXT,
  additional_info JSONB
);

CREATE INDEX idx_cproj_candidate_id ON candidate_projects(candidate_id);
CREATE INDEX idx_cproj_status ON candidate_projects(status);

-- ============================================
-- TABLE: chatbot_conversations
-- ============================================
CREATE TABLE chatbot_conversations (
  id SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  session_id VARCHAR(36) NOT NULL,
  message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('question', 'answer', 'system')),
  message_content TEXT NOT NULL,
  project_id INT REFERENCES candidate_projects(id) ON DELETE SET NULL,
  metadata JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cc_candidate_id ON chatbot_conversations(candidate_id);
CREATE INDEX idx_cc_session_id ON chatbot_conversations(session_id);
CREATE INDEX idx_cc_created_at ON chatbot_conversations(created_at);

-- ============================================
-- TABLE: contract_types
-- ============================================
CREATE TABLE contract_types (
  id SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  type_name VARCHAR(50)
);

-- ============================================
-- TABLE: corrected_cv_versions
-- ============================================
CREATE TABLE corrected_cv_versions (
  id SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  candidate_uuid VARCHAR(36) NOT NULL,
  corrected_cv_minio_url VARCHAR(500),
  corrected_json_minio_url VARCHAR(500),
  corrected_pdf_minio_url VARCHAR(500),
  validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('pending', 'approved', 'rejected', 'needs_revision')),
  feedback_comment TEXT,
  version_number INT DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ccv_candidate_uuid ON corrected_cv_versions(candidate_uuid);
CREATE INDEX idx_ccv_candidate_id ON corrected_cv_versions(candidate_id);
CREATE INDEX idx_ccv_validation_status ON corrected_cv_versions(validation_status);

-- ============================================
-- TABLE: email_verification_tokens
-- ============================================
CREATE TABLE email_verification_tokens (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  code VARCHAR(10) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  used BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evt_user ON email_verification_tokens(user_id);
CREATE INDEX idx_evt_code ON email_verification_tokens(code);

-- ============================================
-- TABLE: experiences
-- ============================================
CREATE TABLE experiences (
  id SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  role VARCHAR(255),
  entreprise VARCHAR(255),
  periode VARCHAR(100),
  description TEXT
);

-- ============================================
-- TABLE: languages
-- ============================================
CREATE TABLE languages (
  id SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  language_name VARCHAR(50)
);

-- ============================================
-- TABLE: llm_evaluation_v2
-- ============================================
CREATE TABLE llm_evaluation_v2 (
  id SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  niveau_profil VARCHAR(20) NOT NULL CHECK (niveau_profil IN ('ETUDIANT','JUNIOR','INTERMEDIAIRE','SENIOR','LEAD')),
  type_parcours VARCHAR(20) NOT NULL CHECK (type_parcours IN ('ACADEMIQUE','CORPORATE','ENTREPRENEURIAL','FREELANCE','MIXTE')),
  mobilite_geographique VARCHAR(15) NOT NULL CHECK (mobilite_geographique IN ('LOCALE','NATIONALE','INTERNATIONALE')),
  impact_preuve_precision VARCHAR(15) NOT NULL CHECK (impact_preuve_precision IN ('AUCUNE','QUALITATIVE','CHIFFREE')),
  impact_ampleur VARCHAR(10) NOT NULL CHECK (impact_ampleur IN ('FAIBLE','MODEREE','MAJEURE')),
  impact_portee VARCHAR(15) NOT NULL CHECK (impact_portee IN ('LOCALE','EQUIPE','ORGANISATION','MARCHE')),
  impact_nature VARCHAR(20) NOT NULL CHECK (impact_nature IN ('TECHNIQUE','BUSINESS','ORGANISATIONNEL','SCIENTIFIQUE','REGLEMENTAIRE','CREATIF','OPERATIONNEL')),
  impact_maturite_relative VARCHAR(20) NOT NULL CHECK (impact_maturite_relative IN ('ATTENDU_NIVEAU','AU_DESSUS_NIVEAU','EXCEPTIONNEL')),
  impact_repetition VARCHAR(15) NOT NULL CHECK (impact_repetition IN ('ISOLE','REPETE','STRUCTUREL')),
  complexite_niveau_max VARCHAR(10) NOT NULL CHECK (complexite_niveau_max IN ('STANDARD','AVANCE','CRITIQUE')),
  complexite_type_problemes VARCHAR(15) NOT NULL CHECK (complexite_type_problemes IN ('EXECUTION','OPTIMISATION','ARCHITECTURE','RECHERCHE','STRATEGIE')),
  complexite_environnement VARCHAR(15) NOT NULL CHECK (complexite_environnement IN ('ACADEMIQUE','STARTUP','ENTREPRISE','REGLEMENTE','INDUSTRIEL')),
  hs_niveau_maitrise_global VARCHAR(15) NOT NULL CHECK (hs_niveau_maitrise_global IN ('ACADEMIQUE','OPERATIONNEL','AVANCE','EXPERTISE')),
  hs_transversalite_competences VARCHAR(10) NOT NULL CHECK (hs_transversalite_competences IN ('FAIBLE','MOYENNE','FORTE')),
  hs_autonomie_technique VARCHAR(15) NOT NULL CHECK (hs_autonomie_technique IN ('ASSISTE','SEMI_AUTONOME','AUTONOME','REFERENT')),
  progression_technique VARCHAR(10) NOT NULL CHECK (progression_technique IN ('AUCUNE','MODEREE','FORTE')),
  progression_hierarchique VARCHAR(10) NOT NULL CHECK (progression_hierarchique IN ('AUCUNE','MODEREE','FORTE')),
  progression_vitesse_relative VARCHAR(10) NOT NULL CHECK (progression_vitesse_relative IN ('LENTE','NORMALE','RAPIDE')),
  coherence_continuite_thematique VARCHAR(10) NOT NULL CHECK (coherence_continuite_thematique IN ('FAIBLE','MOYENNE','FORTE')),
  coherence_logique_sectorielle VARCHAR(20) NOT NULL CHECK (coherence_logique_sectorielle IN ('RUPTURE_FORTE','TRANSITION_PARTIELLE','COHERENTE')),
  coherence_narratif_professionnel VARCHAR(15) NOT NULL CHECK (coherence_narratif_professionnel IN ('CONFUS','LOGIQUE','TRES_STRUCTURE')),
  rarete_densite_competences_rares VARCHAR(10) NOT NULL CHECK (rarete_densite_competences_rares IN ('AUCUNE','QUELQUES','PLUSIEURS')),
  rarete_combinaison_atypique BOOLEAN NOT NULL DEFAULT FALSE,
  rarete_exposition_internationale BOOLEAN NOT NULL DEFAULT FALSE,
  rarete_contribution_reconnue VARCHAR(10) NOT NULL CHECK (rarete_contribution_reconnue IN ('AUCUNE','INTERNE','EXTERNE','PUBLIQUE')),
  stabilite_coherence_parcours VARCHAR(15) NOT NULL CHECK (stabilite_coherence_parcours IN ('ERRATIQUE','LOGIQUE','TRES_LOGIQUE')),
  stabilite_duree_typique_poste VARCHAR(10) NOT NULL CHECK (stabilite_duree_typique_poste IN ('COURTE','NORMALE','LONGUE')),
  stabilite_engagement_long_terme VARCHAR(10) NOT NULL CHECK (stabilite_engagement_long_terme IN ('FAIBLE','MOYEN','ELEVE')),
  communication_clarte VARCHAR(10) NOT NULL CHECK (communication_clarte IN ('FAIBLE','CORRECTE','EXCELLENTE')),
  communication_structure VARCHAR(15) NOT NULL CHECK (communication_structure IN ('DESORGANISEE','ORGANISEE','TRES_STRUCTUREE')),
  communication_precision_vocabulaire VARCHAR(12) NOT NULL CHECK (communication_precision_vocabulaire IN ('VAGUE','TECHNIQUE','TRES_PRECISE')),
  communication_densite_informationnelle VARCHAR(15) NOT NULL CHECK (communication_densite_informationnelle IN ('SUPERFICIELLE','STRUCTUREE','PROFONDE')),
  signal_publication_scientifique BOOLEAN NOT NULL DEFAULT FALSE,
  signal_responsabilite_budget BOOLEAN NOT NULL DEFAULT FALSE,
  signal_responsabilite_equipe BOOLEAN NOT NULL DEFAULT FALSE,
  signal_gestion_risque_critique BOOLEAN NOT NULL DEFAULT FALSE,
  signal_impact_marche_direct BOOLEAN NOT NULL DEFAULT FALSE,
  signal_experience_reglementee BOOLEAN NOT NULL DEFAULT FALSE,
  anomalie_surdeclaration_seniority BOOLEAN NOT NULL DEFAULT FALSE,
  anomalie_competences_sans_preuves BOOLEAN NOT NULL DEFAULT FALSE,
  anomalie_absence_metriques_chiffrees BOOLEAN NOT NULL DEFAULT FALSE,
  anomalie_incoherence_majeure_parcours BOOLEAN NOT NULL DEFAULT FALSE,
  anomalie_keyword_stuffing_probable BOOLEAN NOT NULL DEFAULT FALSE,
  llm_model_version VARCHAR(50) DEFAULT 'gemini-2.5-flash',
  contract_version VARCHAR(50) DEFAULT 'LLM_PROFILE_EVAL_V2_DISCRETE'
);

CREATE INDEX idx_llm_candidate_created ON llm_evaluation_v2(candidate_id, created_at);
CREATE INDEX idx_llm_niveau_profil ON llm_evaluation_v2(niveau_profil);
CREATE INDEX idx_llm_anomalies ON llm_evaluation_v2(anomalie_surdeclaration_seniority, anomalie_competences_sans_preuves);

-- ============================================
-- TABLE: orchestration_map
-- ============================================
CREATE TABLE orchestration_map (
  db_candidate_id INT PRIMARY KEY,
  candidate_uuid VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLE: portfolio_sessions
-- ============================================
CREATE TABLE portfolio_sessions (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(36) NOT NULL UNIQUE,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  profile JSONB NOT NULL,
  missing_fields JSONB NOT NULL,
  current_question_key VARCHAR(100),
  current_question TEXT,
  asked_questions JSONB NOT NULL,
  is_complete BOOLEAN DEFAULT FALSE,
  extracted_data JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ps_session_id ON portfolio_sessions(session_id);
CREATE INDEX idx_ps_candidate_id ON portfolio_sessions(candidate_id);
CREATE INDEX idx_ps_is_complete ON portfolio_sessions(is_complete);

-- ============================================
-- TABLE: realisations
-- ============================================
CREATE TABLE realisations (
  id SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  description TEXT
);

-- ============================================
-- TABLE: score
-- ============================================
CREATE TABLE score (
  id SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  llm_evaluation_id INT NOT NULL REFERENCES llm_evaluation_v2(id),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  engine_version VARCHAR(50) DEFAULT 'CORE_V1_STABLE',
  sector_detected VARCHAR(100),
  score_global NUMERIC(5, 2) NOT NULL,
  dim_impact NUMERIC(5, 2) NOT NULL,
  dim_impact_base NUMERIC(5, 2) NOT NULL,
  dim_impact_bonus_maturite NUMERIC(5, 2) DEFAULT 0.00,
  dim_impact_penalite NUMERIC(5, 2) DEFAULT 0.00,
  impact_precision_score NUMERIC(5, 2) NOT NULL,
  impact_ampleur_score NUMERIC(5, 2) NOT NULL,
  impact_portee_score NUMERIC(5, 2) NOT NULL,
  impact_repetition_score NUMERIC(5, 2) NOT NULL,
  impact_nature_coeff NUMERIC(5, 2) NOT NULL,
  dim_hard_skills_depth NUMERIC(5, 2) NOT NULL,
  hs_complexite_score NUMERIC(5, 2) NOT NULL,
  hs_maitrise_score NUMERIC(5, 2) NOT NULL,
  hs_autonomie_score NUMERIC(5, 2) NOT NULL,
  hs_type_problemes_score NUMERIC(5, 2) NOT NULL,
  hs_transversalite_score NUMERIC(5, 2) NOT NULL,
  dim_coherence NUMERIC(5, 2) NOT NULL,
  coherence_progression_score NUMERIC(5, 2) NOT NULL,
  coherence_continuite_score NUMERIC(5, 2) NOT NULL,
  coherence_logique_sectorielle_score NUMERIC(5, 2) NOT NULL,
  dim_rarete_marche NUMERIC(5, 2) NOT NULL,
  rarete_densite_score NUMERIC(5, 2) NOT NULL,
  rarete_combinaison_score NUMERIC(5, 2) NOT NULL,
  rarete_contribution_score NUMERIC(5, 2) NOT NULL,
  dim_stabilite NUMERIC(5, 2) NOT NULL,
  stabilite_coherence_parcours_score NUMERIC(5, 2) NOT NULL,
  stabilite_duree_score NUMERIC(5, 2) NOT NULL,
  stabilite_engagement_score NUMERIC(5, 2) NOT NULL,
  dim_communication NUMERIC(5, 2) NOT NULL,
  communication_clarte_score NUMERIC(5, 2) NOT NULL,
  communication_structure_score NUMERIC(5, 2) NOT NULL,
  communication_precision_score NUMERIC(5, 2) NOT NULL,
  communication_densite_score NUMERIC(5, 2) NOT NULL,
  decision VARCHAR(10) CHECK (decision IN ('EXCELLENT', 'BON', 'MOYEN', 'FAIBLE')),
  commentaire TEXT
);

CREATE INDEX idx_score_candidate ON score(candidate_id, score_global);
CREATE INDEX idx_score_created ON score(created_at);

-- ============================================
-- TABLE: score_family_projection
-- ============================================
CREATE TABLE score_family_projection (
  id SERIAL PRIMARY KEY,
  score_id INT NOT NULL REFERENCES score(id) ON DELETE CASCADE,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  c_tech NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
  c_business NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
  c_science NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
  c_org NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
  c_health NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
  c_legal NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
  c_creative NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
  c_ops NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
  v_tech NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
  v_business NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
  v_science NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
  v_org NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
  v_health NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
  v_legal NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
  v_creative NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
  v_ops NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
  dominance_index NUMERIC(5, 2) NOT NULL,
  famille_dominante VARCHAR(50) NOT NULL,
  UNIQUE (score_id, candidate_id)
);

-- ============================================
-- TABLE: skills
-- ============================================
CREATE TABLE skills (
  id SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  skill_name VARCHAR(50)
);

-- ============================================
-- TABLE: skills_score
-- ============================================
CREATE TABLE skills_score (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  score NUMERIC(4, 2) NOT NULL,
  status VARCHAR(50) NOT NULL,
  scope VARCHAR(50) NOT NULL
);

-- ============================================
-- TRIGGER: auto-update updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_corrected_cv_updated_at
  BEFORE UPDATE ON corrected_cv_versions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_candidate_projects_updated_at
  BEFORE UPDATE ON candidate_projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_portfolio_sessions_updated_at
  BEFORE UPDATE ON portfolio_sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();