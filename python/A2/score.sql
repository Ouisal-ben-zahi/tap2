-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Hôte : 127.0.0.1
-- Généré le : mer. 18 fév. 2026 à 13:12
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
-- Structure de la table `score`
--

CREATE TABLE `score` (
  `id` int(11) NOT NULL,
  `candidate_id` int(11) NOT NULL,
  `llm_evaluation_id` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `engine_version` varchar(50) DEFAULT 'CORE_V1_STABLE',
  `sector_detected` varchar(100) DEFAULT NULL,
  `score_global` decimal(5,2) NOT NULL,
  `dim_impact` decimal(5,2) NOT NULL,
  `dim_impact_base` decimal(5,2) NOT NULL,
  `dim_impact_bonus_maturite` decimal(5,2) DEFAULT 0.00,
  `dim_impact_penalite` decimal(5,2) DEFAULT 0.00,
  `impact_precision_score` decimal(5,2) NOT NULL,
  `impact_ampleur_score` decimal(5,2) NOT NULL,
  `impact_portee_score` decimal(5,2) NOT NULL,
  `impact_repetition_score` decimal(5,2) NOT NULL,
  `impact_nature_coeff` decimal(5,2) NOT NULL,
  `dim_hard_skills_depth` decimal(5,2) NOT NULL,
  `hs_complexite_score` decimal(5,2) NOT NULL,
  `hs_maitrise_score` decimal(5,2) NOT NULL,
  `hs_autonomie_score` decimal(5,2) NOT NULL,
  `hs_type_problemes_score` decimal(5,2) NOT NULL,
  `hs_transversalite_score` decimal(5,2) NOT NULL,
  `dim_coherence` decimal(5,2) NOT NULL,
  `coherence_progression_score` decimal(5,2) NOT NULL,
  `coherence_continuite_score` decimal(5,2) NOT NULL,
  `coherence_logique_sectorielle_score` decimal(5,2) NOT NULL,
  `dim_rarete_marche` decimal(5,2) NOT NULL,
  `rarete_densite_score` decimal(5,2) NOT NULL,
  `rarete_combinaison_score` decimal(5,2) NOT NULL,
  `rarete_contribution_score` decimal(5,2) NOT NULL,
  `dim_stabilite` decimal(5,2) NOT NULL,
  `stabilite_coherence_parcours_score` decimal(5,2) NOT NULL,
  `stabilite_duree_score` decimal(5,2) NOT NULL,
  `stabilite_engagement_score` decimal(5,2) NOT NULL,
  `dim_communication` decimal(5,2) NOT NULL,
  `communication_clarte_score` decimal(5,2) NOT NULL,
  `communication_structure_score` decimal(5,2) NOT NULL,
  `communication_precision_score` decimal(5,2) NOT NULL,
  `communication_densite_score` decimal(5,2) NOT NULL,
  `decision` enum('EXCELLENT','BON','MOYEN','FAIBLE') DEFAULT NULL,
  `commentaire` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `score`
--
ALTER TABLE `score`
  ADD PRIMARY KEY (`id`),
  ADD KEY `llm_evaluation_id` (`llm_evaluation_id`),
  ADD KEY `idx_candidate_score` (`candidate_id`,`score_global`),
  ADD KEY `idx_created` (`created_at`);

--
-- AUTO_INCREMENT pour les tables déchargées
--

--
-- AUTO_INCREMENT pour la table `score`
--
ALTER TABLE `score`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Contraintes pour les tables déchargées
--

--
-- Contraintes pour la table `score`
--
ALTER TABLE `score`
  ADD CONSTRAINT `score_ibfk_1` FOREIGN KEY (`candidate_id`) REFERENCES `candidates` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `score_ibfk_2` FOREIGN KEY (`llm_evaluation_id`) REFERENCES `llm_evaluation_v2` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
