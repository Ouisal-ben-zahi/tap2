"""
Moteur de Scoring Déterministe CORE_V1_STABLE
==============================================

Ce moteur calcule les scores à partir des évaluations qualitatives du LLM.
Architecture en 3 couches:
1. LLM → Évaluation qualitative (valeurs discrètes)
2. Moteur → Calcul déterministe (ce fichier)
3. DB → Stockage des scores

Principe: Même input qualitatif = Même score numérique (100% reproductible)
"""

import json
import os
from typing import Dict, Any, Tuple


class ScoringEngine:
    """
    Moteur de calcul déterministe des scores professionnels.
    
    Responsabilités:
    - Charger la configuration CORE_V1_STABLE
    - Mapper les valeurs qualitatives → scores numériques
    - Calculer les 6 dimensions
    - Calculer le score global
    - Projeter vers les 8 familles professionnelles
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialise le moteur avec la configuration.
        
        Args:
            config_path: Chemin vers core_v1_stable.json
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                './core_v1_stable.json'
            )
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.version = self.config['engine_version']
        self.dimensions_config = self.config['dimensions']
        self.mappings = self.config['mappings']
        self.penalites = self.config['penalites']
        self.familles = self.config['familles_professionnelles']
    
    def map_value(self, field_name: str, value: Any) -> float:
        """
        Mappe une valeur qualitative vers un score numérique.
        
        Args:
            field_name: Nom du champ (ex: 'ampleur', 'preuve_precision')
            value: Valeur qualitative (ex: 'MAJEURE', 'CHIFFREE')
        
        Returns:
            Score numérique (0-100)
        """
        if field_name not in self.mappings:
            raise ValueError(f"Champ {field_name} non trouvé dans les mappings")
        
        # Pour les booléens
        if isinstance(value, bool):
            value = str(value).lower()
        
        mapping = self.mappings[field_name]
        
        if value not in mapping:
            raise ValueError(
                f"Valeur '{value}' invalide pour {field_name}. "
                f"Valeurs attendues: {list(mapping.keys())}"
            )
        
        return float(mapping[value])
    
    def calculate_impact(self, llm_eval: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcule la dimension IMPACT.
        
        Formule:
        Impact_base = 0.30 × precision + 0.25 × ampleur + 0.20 × portee 
                    + 0.15 × repetition + 0.10 × nature_coeff
        Impact = min(100, Impact_base + bonus_maturite)
        
        Pénalité si absence_metriques_chiffrees: × 0.85
        """
        weights = self.dimensions_config['impact']['composantes']
        
        # Mapping des valeurs
        precision = self.map_value('preuve_precision', llm_eval['impact_preuve_precision'])
        ampleur = self.map_value('ampleur', llm_eval['impact_ampleur'])
        portee = self.map_value('portee', llm_eval['impact_portee'])
        repetition = self.map_value('repetition_impact', llm_eval['impact_repetition'])
        nature_coeff = self.map_value('nature_impact', llm_eval['impact_nature'])
        
        # Calcul de base
        impact_base = (
            weights['precision'] * precision +
            weights['ampleur'] * ampleur +
            weights['portee'] * portee +
            weights['repetition'] * repetition +
            weights['nature'] * nature_coeff
        )
        
        # Bonus maturité (additif, capé)
        bonus_maturite = self.map_value(
            'maturite_relative', 
            llm_eval['impact_maturite_relative']
        )
        
        # Score avant pénalités
        impact_score = min(100, impact_base + bonus_maturite)
        
        # Pénalité anomalie
        penalite = 0
        if llm_eval.get('anomalie_absence_metriques_chiffrees', False):
            impact_score *= self.penalites['anomalie_absence_metriques_chiffrees']['multiplicateur']
            penalite = impact_score * (1 - self.penalites['anomalie_absence_metriques_chiffrees']['multiplicateur'])
        
        return {
            'dim_impact': round(impact_score, 2),
            'dim_impact_base': round(impact_base, 2),
            'dim_impact_bonus_maturite': round(bonus_maturite, 2),
            'dim_impact_penalite': round(penalite, 2),
            'impact_precision_score': round(precision, 2),
            'impact_ampleur_score': round(ampleur, 2),
            'impact_portee_score': round(portee, 2),
            'impact_repetition_score': round(repetition, 2),
            'impact_nature_coeff': round(nature_coeff, 2)
        }
    
    def calculate_hard_skills_depth(self, llm_eval: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcule la dimension HARD_SKILLS_DEPTH.
        
        Formule:
        HardSkills = 0.30 × complexite + 0.20 × maitrise + 0.20 × autonomie
                   + 0.15 × type_problemes + 0.15 × transversalite
        
        Pénalité si surdeclaration_seniority: × 0.85
        """
        weights = self.dimensions_config['hard_skills_depth']['composantes']
        
        complexite = self.map_value('complexite_niveau_max', llm_eval['complexite_niveau_max'])
        maitrise = self.map_value('niveau_maitrise_global', llm_eval['hs_niveau_maitrise_global'])
        autonomie = self.map_value('autonomie_technique', llm_eval['hs_autonomie_technique'])
        type_prob = self.map_value('type_problemes', llm_eval['complexite_type_problemes'])
        transversal = self.map_value('transversalite_competences', llm_eval['hs_transversalite_competences'])
        
        hs_score = (
            weights['complexite'] * complexite +
            weights['maitrise'] * maitrise +
            weights['autonomie'] * autonomie +
            weights['type_problemes'] * type_prob +
            weights['transversalite'] * transversal
        )
        
        # Pénalité anomalie
        if llm_eval.get('anomalie_surdeclaration_seniority', False):
            hs_score *= self.penalites['anomalie_surdeclaration_seniority']['multiplicateur']
        
        return {
            'dim_hard_skills_depth': round(hs_score, 2),
            'hs_complexite_score': round(complexite, 2),
            'hs_maitrise_score': round(maitrise, 2),
            'hs_autonomie_score': round(autonomie, 2),
            'hs_type_problemes_score': round(type_prob, 2),
            'hs_transversalite_score': round(transversal, 2)
        }
    
    def calculate_coherence(self, llm_eval: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcule la dimension COHERENCE.
        
        Formule:
        ProgressionScore = 0.5 × technique + 0.3 × hierarchique + 0.2 × vitesse
        Coherence = 0.40 × ProgressionScore + 0.35 × continuite + 0.25 × logique_sectorielle
        """
        weights = self.dimensions_config['coherence']['composantes']
        prog_weights = self.dimensions_config['coherence']['progression_sub_weights']
        
        # Progression
        tech = self.map_value('progression_technique', llm_eval['progression_technique'])
        hier = self.map_value('progression_hierarchique', llm_eval['progression_hierarchique'])
        vitesse = self.map_value('vitesse_relative', llm_eval['progression_vitesse_relative'])
        
        progression_score = (
            prog_weights['technique'] * tech +
            prog_weights['hierarchique'] * hier +
            prog_weights['vitesse'] * vitesse
        )
        
        # Continuité et logique
        continuite = self.map_value('continuite_thematique', llm_eval['coherence_continuite_thematique'])
        logique = self.map_value('logique_sectorielle', llm_eval['coherence_logique_sectorielle'])
        
        coherence_score = (
            weights['progression'] * progression_score +
            weights['continuite_thematique'] * continuite +
            weights['logique_sectorielle'] * logique
        )
        
        return {
            'dim_coherence': round(coherence_score, 2),
            'coherence_progression_score': round(progression_score, 2),
            'coherence_continuite_score': round(continuite, 2),
            'coherence_logique_sectorielle_score': round(logique, 2)
        }
    
    def calculate_rarete_marche(self, llm_eval: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcule la dimension RARETE_MARCHE.
        
        Formule:
        Rareté = 0.50 × densite + 0.30 × combinaison + 0.20 × contribution
        """
        weights = self.dimensions_config['rarete_marche']['composantes']
        
        densite = self.map_value('densite_competences_rares', llm_eval['rarete_densite_competences_rares'])
        combinaison = self.map_value('combinaison_atypique', llm_eval['rarete_combinaison_atypique'])
        contribution = self.map_value('contribution_reconnue', llm_eval['rarete_contribution_reconnue'])
        
        rarete_score = (
            weights['densite_competences_rares'] * densite +
            weights['combinaison_atypique'] * combinaison +
            weights['contribution_reconnue'] * contribution
        )
        
        return {
            'dim_rarete_marche': round(rarete_score, 2),
            'rarete_densite_score': round(densite, 2),
            'rarete_combinaison_score': round(combinaison, 2),
            'rarete_contribution_score': round(contribution, 2)
        }
    
    def calculate_stabilite(self, llm_eval: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcule la dimension STABILITE.
        
        Formule:
        Stabilite = 0.40 × coherence_parcours + 0.35 × duree + 0.25 × engagement
        """
        weights = self.dimensions_config['stabilite']['composantes']
        
        coherence = self.map_value('coherence_parcours', llm_eval['stabilite_coherence_parcours'])
        duree = self.map_value('duree_typique_poste', llm_eval['stabilite_duree_typique_poste'])
        engagement = self.map_value('engagement_long_terme', llm_eval['stabilite_engagement_long_terme'])
        
        stabilite_score = (
            weights['coherence_parcours'] * coherence +
            weights['duree_typique_poste'] * duree +
            weights['engagement_long_terme'] * engagement
        )
        
        return {
            'dim_stabilite': round(stabilite_score, 2),
            'stabilite_coherence_parcours_score': round(coherence, 2),
            'stabilite_duree_score': round(duree, 2),
            'stabilite_engagement_score': round(engagement, 2)
        }
    
    def calculate_communication(self, llm_eval: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcule la dimension COMMUNICATION.
        
        Formule:
        Communication = 0.30 × clarte + 0.25 × structure + 0.25 × precision + 0.20 × densite
        """
        weights = self.dimensions_config['communication']['composantes']
        
        clarte = self.map_value('clarte', llm_eval['communication_clarte'])
        structure = self.map_value('structure', llm_eval['communication_structure'])
        precision = self.map_value('precision_vocabulaire', llm_eval['communication_precision_vocabulaire'])
        densite = self.map_value('densite_informationnelle', llm_eval['communication_densite_informationnelle'])
        
        comm_score = (
            weights['clarte'] * clarte +
            weights['structure'] * structure +
            weights['precision_vocabulaire'] * precision +
            weights['densite_informationnelle'] * densite
        )
        
        return {
            'dim_communication': round(comm_score, 2),
            'communication_clarte_score': round(clarte, 2),
            'communication_structure_score': round(structure, 2),
            'communication_precision_score': round(precision, 2),
            'communication_densite_score': round(densite, 2)
        }
    
    def calculate_global_score(self, dimensions: Dict[str, float]) -> float:
        """
        Calcule le score global à partir des 6 dimensions.
        
        Formule:
        ScoreCore = 0.25 × Impact + 0.25 × HardSkills + 0.15 × Coherence
                  + 0.20 × Rareté + 0.10 × Stabilité + 0.05 × Communication
        """
        poids = {
            'impact': self.dimensions_config['impact']['poids_global'],
            'hard_skills_depth': self.dimensions_config['hard_skills_depth']['poids_global'],
            'coherence': self.dimensions_config['coherence']['poids_global'],
            'rarete_marche': self.dimensions_config['rarete_marche']['poids_global'],
            'stabilite': self.dimensions_config['stabilite']['poids_global'],
            'communication': self.dimensions_config['communication']['poids_global']
        }
        
        score_global = (
            poids['impact'] * dimensions['dim_impact'] +
            poids['hard_skills_depth'] * dimensions['dim_hard_skills_depth'] +
            poids['coherence'] * dimensions['dim_coherence'] +
            poids['rarete_marche'] * dimensions['dim_rarete_marche'] +
            poids['stabilite'] * dimensions['dim_stabilite'] +
            poids['communication'] * dimensions['dim_communication']
        )
        
        # Plafonner à 100
        score_global = min(100, max(0, score_global))
        
        return round(score_global, 2)
    
    def calculate_family_projection(
        self, 
        llm_eval: Dict[str, Any], 
        dimensions: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Projette le profil dans les 8 familles professionnelles.
        
        Returns:
            Dict avec scores bruts (C_i), vecteur normalisé (V_i), dominance
        """
        famille_scores = {}
        
        # C_TECH
        c_tech = (
            0.35 * dimensions['dim_hard_skills_depth'] +
            0.25 * (dimensions['dim_impact'] if llm_eval['impact_nature'] == 'TECHNIQUE' else 0) +
            0.20 * dimensions['hs_complexite_score'] +
            0.10 * self.map_value('progression_technique', llm_eval['progression_technique']) +
            0.10 * dimensions['dim_rarete_marche']
        )
        famille_scores['c_tech'] = round(c_tech, 2)
        
        # C_BUSINESS
        c_business = (
            0.35 * (dimensions['dim_impact'] if llm_eval['impact_nature'] == 'BUSINESS' else 0) +
            0.25 * self.map_value('progression_hierarchique', llm_eval['progression_hierarchique']) +
            0.20 * dimensions['impact_portee_score'] +
            0.10 * dimensions['dim_stabilite'] +
            0.10 * dimensions['dim_communication']
        )
        famille_scores['c_business'] = round(c_business, 2)
        
        # C_SCIENCE
        c_science = (
            0.30 * dimensions['dim_hard_skills_depth'] +
            0.25 * (dimensions['hs_complexite_score'] if llm_eval['complexite_type_problemes'] == 'RECHERCHE' else 0) +
            0.20 * self.map_value('contribution_reconnue', llm_eval['rarete_contribution_reconnue']) +
            0.15 * self.map_value('maturite_relative', llm_eval['impact_maturite_relative']) +
            0.10 * (70 if llm_eval['complexite_environnement'] == 'ACADEMIQUE' else 0)
        )
        famille_scores['c_science'] = round(c_science, 2)
        
        # C_ORG
        portee_org = 80 if llm_eval['impact_portee'] in ['ORGANISATION', 'MARCHE'] else 40
        c_org = (
            0.35 * self.map_value('progression_hierarchique', llm_eval['progression_hierarchique']) +
            0.25 * portee_org +
            0.20 * dimensions['dim_stabilite'] +
            0.10 * dimensions['dim_communication'] +
            0.10 * dimensions['dim_impact']
        )
        famille_scores['c_org'] = round(c_org, 2)
        
        # C_HEALTH
        gestion_risque = 100 if llm_eval.get('signal_gestion_risque_critique', False) else 0
        c_health = (
            0.30 * dimensions['dim_hard_skills_depth'] +
            0.25 * dimensions['dim_impact'] +
            0.20 * gestion_risque +
            0.15 * dimensions['dim_stabilite'] +
            0.10 * dimensions['dim_rarete_marche']
        )
        if llm_eval['complexite_environnement'] != 'REGLEMENTE':
            c_health *= 0.5
        famille_scores['c_health'] = round(c_health, 2)
        
        # C_LEGAL
        c_legal = (
            0.30 * gestion_risque +
            0.25 * (dimensions['dim_impact'] if llm_eval['impact_nature'] == 'REGLEMENTAIRE' else 0) +
            0.20 * self.map_value('progression_hierarchique', llm_eval['progression_hierarchique']) +
            0.15 * dimensions['dim_stabilite'] +
            0.10 * dimensions['dim_communication']
        )
        famille_scores['c_legal'] = round(c_legal, 2)
        
        # C_CREATIVE
        portee_marche = 100 if llm_eval['impact_portee'] == 'MARCHE' else 50
        c_creative = (
            0.30 * dimensions['dim_communication'] +
            0.25 * (dimensions['dim_impact'] if llm_eval['impact_nature'] == 'CREATIF' else 0) +
            0.20 * self.map_value('combinaison_atypique', llm_eval['rarete_combinaison_atypique']) +
            0.15 * portee_marche +
            0.10 * dimensions['dim_rarete_marche']
        )
        famille_scores['c_creative'] = round(c_creative, 2)
        
        # C_OPS
        complexite_ops = dimensions['hs_complexite_score'] if llm_eval['complexite_niveau_max'] in ['STANDARD', 'AVANCE'] else 0
        c_ops = (
            0.30 * dimensions['dim_stabilite'] +
            0.25 * (dimensions['dim_impact'] if llm_eval['impact_nature'] == 'OPERATIONNEL' else 0) +
            0.20 * dimensions['hs_autonomie_score'] +
            0.15 * complexite_ops +
            0.10 * dimensions['dim_coherence']
        )
        famille_scores['c_ops'] = round(c_ops, 2)
        
        # Normalisation (vecteur somme = 1.0)
        total = sum(famille_scores.values())
        vecteur = {}
        
        if total > 0:
            for key, value in famille_scores.items():
                vecteur[f'v_{key[2:]}'] = round(value / total, 4)
        else:
            for key in famille_scores.keys():
                vecteur[f'v_{key[2:]}'] = 0.0
        
        # Dominance
        if total > 0:
            max_score = max(famille_scores.values())
            moyenne_score = total / len(famille_scores)
            dominance_index = round(max_score / moyenne_score, 2) if moyenne_score > 0 else 0
            
            # Trouver la famille dominante
            famille_dominante = max(famille_scores, key=famille_scores.get)
            famille_dominante = famille_dominante.replace('c_', 'C_').upper()
        else:
            dominance_index = 0
            famille_dominante = 'INDEFINI'
        
        return {
            **famille_scores,
            **vecteur,
            'dominance_index': dominance_index,
            'famille_dominante': famille_dominante
        }
    
    def evaluate(self, llm_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Point d'entrée principal: évalue un profil complet.
        
        Args:
            llm_evaluation: Dictionnaire avec toutes les valeurs du contrat LLM V2
        
        Returns:
            Dictionnaire complet avec:
            - Toutes les dimensions calculées
            - Score global
            - Projection familles professionnelles
        """
        # Calculer les 6 dimensions
        impact = self.calculate_impact(llm_evaluation)
        hard_skills = self.calculate_hard_skills_depth(llm_evaluation)
        coherence = self.calculate_coherence(llm_evaluation)
        rarete = self.calculate_rarete_marche(llm_evaluation)
        stabilite = self.calculate_stabilite(llm_evaluation)
        communication = self.calculate_communication(llm_evaluation)
        
        # Fusionner toutes les dimensions
        all_dimensions = {
            **impact,
            **hard_skills,
            **coherence,
            **rarete,
            **stabilite,
            **communication
        }
        
        # Score global
        score_global = self.calculate_global_score(all_dimensions)
        
        # Projection familles
        family_projection = self.calculate_family_projection(llm_evaluation, all_dimensions)
        
        # Décision automatique basée sur score
        if score_global >= 80:
            decision = 'EXCELLENT'
        elif score_global >= 65:
            decision = 'BON'
        elif score_global >= 50:
            decision = 'MOYEN'
        else:
            decision = 'FAIBLE'
        
        return {
            'engine_version': self.version,
            'score_global': score_global,
            'decision': decision,
            **all_dimensions,
            'family_projection': family_projection
        }


# ============================================================================
# TESTS UNITAIRES
# ============================================================================

def test_engine():
    """Test basique du moteur avec un profil fictif."""
    
    engine = ScoringEngine()
    
    # Profil test: Senior technique avec impact fort
    llm_eval = {
        'niveau_profil': 'SENIOR',
        'type_parcours': 'CORPORATE',
        'mobilite_geographique': 'INTERNATIONALE',
        
        'impact_preuve_precision': 'CHIFFREE',
        'impact_ampleur': 'MAJEURE',
        'impact_portee': 'ORGANISATION',
        'impact_nature': 'TECHNIQUE',
        'impact_maturite_relative': 'AU_DESSUS_NIVEAU',
        'impact_repetition': 'STRUCTUREL',
        
        'complexite_niveau_max': 'CRITIQUE',
        'complexite_type_problemes': 'ARCHITECTURE',
        'complexite_environnement': 'ENTREPRISE',
        
        'hs_niveau_maitrise_global': 'EXPERTISE',
        'hs_transversalite_competences': 'FORTE',
        'hs_autonomie_technique': 'REFERENT',
        
        'progression_technique': 'FORTE',
        'progression_hierarchique': 'MODEREE',
        'progression_vitesse_relative': 'RAPIDE',
        
        'coherence_continuite_thematique': 'FORTE',
        'coherence_logique_sectorielle': 'COHERENTE',
        'coherence_narratif_professionnel': 'TRES_STRUCTURE',
        
        'rarete_densite_competences_rares': 'PLUSIEURS',
        'rarete_combinaison_atypique': True,
        'rarete_exposition_internationale': True,
        'rarete_contribution_reconnue': 'EXTERNE',
        
        'stabilite_coherence_parcours': 'TRES_LOGIQUE',
        'stabilite_duree_typique_poste': 'LONGUE',
        'stabilite_engagement_long_terme': 'ELEVE',
        
        'communication_clarte': 'EXCELLENTE',
        'communication_structure': 'TRES_STRUCTUREE',
        'communication_precision_vocabulaire': 'TRES_PRECISE',
        'communication_densite_informationnelle': 'PROFONDE',
        
        'signal_publication_scientifique': False,
        'signal_responsabilite_budget': True,
        'signal_responsabilite_equipe': True,
        'signal_gestion_risque_critique': False,
        'signal_impact_marche_direct': True,
        'signal_experience_reglementee': False,
        
        'anomalie_surdeclaration_seniority': False,
        'anomalie_competences_sans_preuves': False,
        'anomalie_absence_metriques_chiffrees': False,
        'anomalie_incoherence_majeure_parcours': False,
        'anomalie_keyword_stuffing_probable': False
    }
    
    result = engine.evaluate(llm_eval)
    
    print("\n" + "="*60)
    print("TEST MOTEUR CORE_V1_STABLE")
    print("="*60)
    print(f"Score Global: {result['score_global']}/100")
    print(f"Décision: {result['decision']}")
    print("\nDimensions:")
    print(f"  - Impact: {result['dim_impact']}")
    print(f"  - Hard Skills Depth: {result['dim_hard_skills_depth']}")
    print(f"  - Cohérence: {result['dim_coherence']}")
    print(f"  - Rareté Marché: {result['dim_rarete_marche']}")
    print(f"  - Stabilité: {result['dim_stabilite']}")
    print(f"  - Communication: {result['dim_communication']}")
    print("\nProjection Familles:")
    fp = result['family_projection']
    print(f"  - Dominante: {fp['famille_dominante']} (index: {fp['dominance_index']})")
    print(f"  - C_TECH: {fp['c_tech']:.2f} ({fp['v_tech']:.1%})")
    print(f"  - C_BUSINESS: {fp['c_business']:.2f} ({fp['v_business']:.1%})")
    print(f"  - C_SCIENCE: {fp['c_science']:.2f} ({fp['v_science']:.1%})")
    print("="*60 + "\n")


if __name__ == '__main__':
    test_engine()
