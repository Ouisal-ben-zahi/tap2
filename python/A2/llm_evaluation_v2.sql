-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Hôte : 127.0.0.1
-- Généré le : mer. 18 fév. 2026 à 13:10
-- Version du serveur : 10.4.32-MariaDB
-- Version de PHP : 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de données : `tap_db`
--

-- --------------------------------------------------------

--
-- Structure de la table `llm_evaluation_v2`
--

CREATE TABLE `llm_evaluation_v2` (
  `id` int(11) NOT NULL,
  `candidate_id` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `niveau_profil` enum('ETUDIANT','JUNIOR','INTERMEDIAIRE','SENIOR','LEAD') NOT NULL,
  `type_parcours` enum('ACADEMIQUE','CORPORATE','ENTREPRENEURIAL','FREELANCE','MIXTE') NOT NULL,
  `mobilite_geographique` enum('LOCALE','NATIONALE','INTERNATIONALE') NOT NULL,
  `impact_preuve_precision` enum('AUCUNE','QUALITATIVE','CHIFFREE') NOT NULL,
  `impact_ampleur` enum('FAIBLE','MODEREE','MAJEURE') NOT NULL,
  `impact_portee` enum('LOCALE','EQUIPE','ORGANISATION','MARCHE') NOT NULL,
  `impact_nature` enum('TECHNIQUE','BUSINESS','ORGANISATIONNEL','SCIENTIFIQUE','REGLEMENTAIRE','CREATIF','OPERATIONNEL') NOT NULL,
  `impact_maturite_relative` enum('ATTENDU_NIVEAU','AU_DESSUS_NIVEAU','EXCEPTIONNEL') NOT NULL,
  `impact_repetition` enum('ISOLE','REPETE','STRUCTUREL') NOT NULL,
  `complexite_niveau_max` enum('STANDARD','AVANCE','CRITIQUE') NOT NULL,
  `complexite_type_problemes` enum('EXECUTION','OPTIMISATION','ARCHITECTURE','RECHERCHE','STRATEGIE') NOT NULL,
  `complexite_environnement` enum('ACADEMIQUE','STARTUP','ENTREPRISE','REGLEMENTE','INDUSTRIEL') NOT NULL,
  `hs_niveau_maitrise_global` enum('ACADEMIQUE','OPERATIONNEL','AVANCE','EXPERTISE') NOT NULL,
  `hs_transversalite_competences` enum('FAIBLE','MOYENNE','FORTE') NOT NULL,
  `hs_autonomie_technique` enum('ASSISTE','SEMI_AUTONOME','AUTONOME','REFERENT') NOT NULL,
  `progression_technique` enum('AUCUNE','MODEREE','FORTE') NOT NULL,
  `progression_hierarchique` enum('AUCUNE','MODEREE','FORTE') NOT NULL,
  `progression_vitesse_relative` enum('LENTE','NORMALE','RAPIDE') NOT NULL,
  `coherence_continuite_thematique` enum('FAIBLE','MOYENNE','FORTE') NOT NULL,
  `coherence_logique_sectorielle` enum('RUPTURE_FORTE','TRANSITION_PARTIELLE','COHERENTE') NOT NULL,
  `coherence_narratif_professionnel` enum('CONFUS','LOGIQUE','TRES_STRUCTURE') NOT NULL,
  `rarete_densite_competences_rares` enum('AUCUNE','QUELQUES','PLUSIEURS') NOT NULL,
  `rarete_combinaison_atypique` tinyint(1) NOT NULL DEFAULT 0,
  `rarete_exposition_internationale` tinyint(1) NOT NULL DEFAULT 0,
  `rarete_contribution_reconnue` enum('AUCUNE','INTERNE','EXTERNE','PUBLIQUE') NOT NULL,
  `stabilite_coherence_parcours` enum('ERRATIQUE','LOGIQUE','TRES_LOGIQUE') NOT NULL,
  `stabilite_duree_typique_poste` enum('COURTE','NORMALE','LONGUE') NOT NULL,
  `stabilite_engagement_long_terme` enum('FAIBLE','MOYEN','ELEVE') NOT NULL,
  `communication_clarte` enum('FAIBLE','CORRECTE','EXCELLENTE') NOT NULL,
  `communication_structure` enum('DESORGANISEE','ORGANISEE','TRES_STRUCTUREE') NOT NULL,
  `communication_precision_vocabulaire` enum('VAGUE','TECHNIQUE','TRES_PRECISE') NOT NULL,
  `communication_densite_informationnelle` enum('SUPERFICIELLE','STRUCTUREE','PROFONDE') NOT NULL,
  `signal_publication_scientifique` tinyint(1) NOT NULL DEFAULT 0,
  `signal_responsabilite_budget` tinyint(1) NOT NULL DEFAULT 0,
  `signal_responsabilite_equipe` tinyint(1) NOT NULL DEFAULT 0,
  `signal_gestion_risque_critique` tinyint(1) NOT NULL DEFAULT 0,
  `signal_impact_marche_direct` tinyint(1) NOT NULL DEFAULT 0,
  `signal_experience_reglementee` tinyint(1) NOT NULL DEFAULT 0,
  `anomalie_surdeclaration_seniority` tinyint(1) NOT NULL DEFAULT 0,
  `anomalie_competences_sans_preuves` tinyint(1) NOT NULL DEFAULT 0,
  `anomalie_absence_metriques_chiffrees` tinyint(1) NOT NULL DEFAULT 0,
  `anomalie_incoherence_majeure_parcours` tinyint(1) NOT NULL DEFAULT 0,
  `anomalie_keyword_stuffing_probable` tinyint(1) NOT NULL DEFAULT 0,
  `llm_model_version` varchar(50) DEFAULT 'gemini-2.5-flash',
  `contract_version` varchar(50) DEFAULT 'LLM_PROFILE_EVAL_V2_DISCRETE'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `llm_evaluation_v2`
--
ALTER TABLE `llm_evaluation_v2`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_candidate_created` (`candidate_id`,`created_at`),
  ADD KEY `idx_niveau_profil` (`niveau_profil`),
  ADD KEY `idx_anomalies` (`anomalie_surdeclaration_seniority`,`anomalie_competences_sans_preuves`);

--
-- AUTO_INCREMENT pour les tables déchargées
--

--
-- AUTO_INCREMENT pour la table `llm_evaluation_v2`
--
ALTER TABLE `llm_evaluation_v2`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Contraintes pour les tables déchargées
--

--
-- Contraintes pour la table `llm_evaluation_v2`
--
ALTER TABLE `llm_evaluation_v2`
  ADD CONSTRAINT `llm_evaluation_v2_ibfk_1` FOREIGN KEY (`candidate_id`) REFERENCES `candidates` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
