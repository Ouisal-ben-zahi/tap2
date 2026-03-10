"""
Agent de Scoring V2 - Architecture 3 Couches
=============================================

Orchestration du systÃ¨me de scoring:
1. PrÃ©pare le prompt pour Claude (Contrat LLM V2)
2. Appelle Claude pour obtenir l'Ã©valuation qualitative
3. Valide la rÃ©ponse du LLM
4. Passe l'Ã©valuation au moteur de calcul
5. Sauvegarde en base de donnÃ©es

Auteur: SystÃ¨me TAP
Version: 2.0 (CORE_V1_STABLE)
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import google.generativeai as genai


class AgentScoringV2:
    """
    Agent orchestrateur du système de scoring en 3 couches.
    
    Workflow:
    TalentCard JSON → Agent → Claude (éval qualitative) → Moteur (scores) → DB
    """
    
    def __init__(self, db_connection, api_key: Optional[str] = None):
        """
        Initialise l'agent avec connexion DB et API Gemini.
        
        Args:
            db_connection: Connexion MySQL
            api_key: Clé API Google (optionnel, utilise GOOGLE_API_KEY env)
        """
        self.db = db_connection
        
        # Configurer Gemini
        if api_key is None:
            api_key = os.getenv('GOOGLE_API_KEY')
        genai.configure(api_key=api_key)
        
        # Modèle Gemini 2.0 Flash
        self.model = genai.GenerativeModel(
            'gemini-2.5-flash',  # ou 'gemini-1.5-flash' si 2.0 non disponible
            generation_config={
                "temperature": 0,
                "response_mime_type": "application/json"
            }
        )
        
        # Charger le contrat LLM
        config_dir = os.path.join(os.path.dirname(__file__), './')
        with open(os.path.join(config_dir, 'llm_contract_candidat.json'), 'r', encoding='utf-8') as f:
            self.llm_contract = json.load(f)
        
        # Importer le moteur de scoring.
        # 1) Chemin normal quand importé comme module de package: A2.agent_scoring_v2
        # 2) Fallback quand le fichier est exécuté directement
        try:
            from .scoring_engine import ScoringEngine
        except ImportError:
            from scoring_engine import ScoringEngine
        self.engine = ScoringEngine()
        
        print(f"Agent Scoring V2 initialisé (Engine: {self.engine.version}, LLM: Gemini 2.5 Flash)")
    
    def build_evaluation_prompt(self, talentcard: Dict[str, Any], chat_soft_skills_text: Optional[str] = None) -> str:
        """
        Construit le prompt structuré pour Gemini.
        Inclut le schéma JSON directement dans le prompt.
        Si chat_soft_skills_text est fourni (réponse chatbot), l'évaluateur en tient compte pour les soft skills.
        
        Args:
            talentcard: Données du TalentCard JSON
            chat_soft_skills_text: Texte libre des soft skills déclarés par le candidat (question soft_skills_8_examples)
        
        Returns:
            Prompt formaté avec schema JSON
        """
        instructions = self.llm_contract['instructions_llm']
        schema = self.llm_contract['schema_output']
        
        talentcard_formatted = json.dumps(talentcard, indent=2, ensure_ascii=False)
        
        # Construire le schéma JSON exemple
        exemple = self.llm_contract.get('exemple_output_valide', {})
        exemple_str = json.dumps(exemple, indent=2, ensure_ascii=False)
        
        soft_skills_block = ""
        communication_rule = ""
        if chat_soft_skills_text:
            soft_skills_block = f"""
SOFT SKILLS DECLARES PAR LE CANDIDAT (réponse libre du candidat au chatbot - NE PAS IGNORER) :
Le candidat a fourni ci-dessous la liste de ses soft skills et des exemples concrets. Ce texte est la SOURCE PRINCIPALE pour la section "communication" de ta sortie JSON.
---
{chat_soft_skills_text}
---
"""
            communication_rule = """
REGLES QUAND LE BLOC SOFT SKILLS CI-DESSUS EST PRÉSENT :
1) Section "communication" : remplis UNIQUEMENT à partir du texte des soft skills (clarte, structure, precision_vocabulaire, densite_informationnelle).
2) Section "evaluation_soft_skills_declares" : OBLIGATOIRE. Extrais du texte du candidat CHAQUE soft skill qu'il mentionne (ex: Leadership, Travail d'équipe, Résolution de problèmes...) et pour chacun assigne un niveau : FAIBLE (exemples vagues ou absents), MOYEN (exemples corrects), FORT (exemples concrets et convaincants). Retourne un tableau d'objets [ {"nom": "Nom du soft skill", "niveau": "FAIBLE"|"MOYEN"|"FORT"}, ... ]. Si le candidat n'a rien fourni, retourne [].
Si le bloc SOFT SKILLS est absent, laisse "evaluation_soft_skills_declares" à [] et utilise le profil pour "communication".
"""
        
        prompt = f"""Tu es un Evaluateur très très exigeant et expert de profils professionnels.
Tu es consultant auprès de grands cabinets prestigieux élitistes. Tu analyse les profils sur la base de ce contrat:{schema}
tu ne fait pas de cadeaux ou de bonus. tu es directe et véridicte. tu es objectif et sans biais.
MISSION: Analyse ce profil et retourne une evaluation très objective et structurée en JSON.

REGLES CRITIQUES:
1. {instructions['no_scores']}
2. {instructions['closed_lists_only']}
3. {instructions['no_extra_fields']}
4. {instructions['no_weighting']}
5. {instructions['no_global_judgement']}
6. {instructions['objectivity']}
{communication_rule}

PROFIL A ANALYSER:
{talentcard_formatted}
{soft_skills_block}

SCHEMA JSON A RESPECTER (retourne exactement cette structure):
{exemple_str}

GUIDELINES:

ETUDIANT : Cursus en cours, stages, alternances uniquement.
JUNIOR : 1 à 3 ans d'expérience, exécute sous supervision.
INTERMEDIAIRE : 3 à 6 ans, maîtrise son poste, autonome sur ses tâches.
SENIOR : +6 ans, influence les méthodes, résout des problèmes complexes.
LEAD : Expertise reconnue + dimension mentorat ou direction stratégique.
impact, portee 
PERSONNELLE : L'action n'impacte que le travail du candidat.
LOCALE : Impact limité à un seul projet ou une petite unité.
EQUIPE : Impact sur la productivité ou les méthodes de toute la brigade/bureau.
ENTREPRISE : Impact sur le résultat global, l'image ou l'organisation de la société.
MARCHE : Impact externe, normes industrielles, brevets ou influence secteur.
...

Retourne UNIQUEMENT le JSON, sans markdown ni texte supplémentaire."""
        
        return prompt
    
    def call_gemini(self, prompt: str) -> Dict[str, Any]:
       
        try:
            response = self.model.generate_content(prompt)
            
            # Parser le JSON (Gemini retourne du JSON strict avec response_mime_type)
            llm_evaluation = json.loads(response.text)
            
            print("Évaluation LLM obtenue avec succès")
            return llm_evaluation
            
        except json.JSONDecodeError as e:
            print(f"Erreur parsing JSON de Gemini: {e}")
            print(f"Résponse brute: {response.text[:500]}")
            raise
        except Exception as e:
            print(f"âŒ Erreur appel Gemini API: {e}")
            raise
    
    def flatten_llm_evaluation(self, llm_eval: Dict[str, Any]) -> Dict[str, Any]:
        
        def _section(data: Dict[str, Any], key: str) -> Dict[str, Any]:
            value = data.get(key, {})
            return value if isinstance(value, dict) else {}

        def _pick(data: Dict[str, Any], keys: list[str], default: Any) -> Any:
            for k in keys:
                if k in data and data[k] not in (None, ""):
                    return data[k]
            return default

        def _norm_enum(value: Any, default: str) -> str:
            if isinstance(value, str) and value.strip():
                return value.strip().upper()
            return default

        def _norm_bool(value: Any, default: bool) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                v = value.strip().lower()
                if v in {"true", "1", "yes", "oui", "vrai"}:
                    return True
                if v in {"false", "0", "no", "non", "faux"}:
                    return False
            return default

        # Valeurs de fallback depuis le contrat
        ex = self.llm_contract.get("exemple_output_valide", {})
        ex_profil = _section(ex, "profil_contexte")
        ex_impact = _section(ex, "impact")
        ex_complexite = _section(ex, "complexite")
        ex_hs = _section(ex, "hard_skills")
        ex_prog = _section(ex, "progression")
        ex_coh = _section(ex, "coherence")
        ex_rarete = _section(ex, "rarete")
        ex_stab = _section(ex, "stabilite")
        ex_comm = _section(ex, "communication")
        ex_signaux = _section(ex, "signaux_speciaux")
        ex_anom = _section(ex, "anomalies_detectees")

        profil = _section(llm_eval, "profil_contexte")
        impact = _section(llm_eval, "impact")
        complexite = _section(llm_eval, "complexite")
        hs = _section(llm_eval, "hard_skills")
        prog = _section(llm_eval, "progression")
        coh = _section(llm_eval, "coherence")
        rarete = _section(llm_eval, "rarete")
        stab = _section(llm_eval, "stabilite")
        comm = _section(llm_eval, "communication")
        signaux = _section(llm_eval, "signaux_speciaux")
        anom = _section(llm_eval, "anomalies_detectees")

        flat = {
            # Contexte
            "niveau_profil": _norm_enum(_pick(profil, ["niveau_profil"], ex_profil.get("niveau_profil", "JUNIOR")), ex_profil.get("niveau_profil", "JUNIOR")),
            "type_parcours": _norm_enum(_pick(profil, ["type_parcours"], ex_profil.get("type_parcours", "CORPORATE")), ex_profil.get("type_parcours", "CORPORATE")),
            "mobilite_geographique": _norm_enum(_pick(profil, ["mobilite_geographique"], ex_profil.get("mobilite_geographique", "NATIONALE")), ex_profil.get("mobilite_geographique", "NATIONALE")),

            # Impact
            "impact_preuve_precision": _norm_enum(_pick(impact, ["preuve_precision", "precision"], ex_impact.get("preuve_precision", "QUALITATIVE")), ex_impact.get("preuve_precision", "QUALITATIVE")),
            "impact_ampleur": _norm_enum(_pick(impact, ["ampleur"], ex_impact.get("ampleur", "MODEREE")), ex_impact.get("ampleur", "MODEREE")),
            "impact_portee": _norm_enum(_pick(impact, ["portee"], ex_impact.get("portee", "EQUIPE")), ex_impact.get("portee", "EQUIPE")),
            "impact_nature": _norm_enum(_pick(impact, ["nature_impact", "nature"], ex_impact.get("nature_impact", "TECHNIQUE")), ex_impact.get("nature_impact", "TECHNIQUE")),
            "impact_maturite_relative": _norm_enum(_pick(impact, ["maturite_relative"], ex_impact.get("maturite_relative", "ATTENDU_NIVEAU")), ex_impact.get("maturite_relative", "ATTENDU_NIVEAU")),
            "impact_repetition": _norm_enum(_pick(impact, ["repetition_impact", "repetition"], ex_impact.get("repetition_impact", "ISOLE")), ex_impact.get("repetition_impact", "ISOLE")),

            # Complexite
            "complexite_niveau_max": _norm_enum(_pick(complexite, ["niveau_max"], ex_complexite.get("niveau_max", "STANDARD")), ex_complexite.get("niveau_max", "STANDARD")),
            "complexite_type_problemes": _norm_enum(_pick(complexite, ["type_problemes"], ex_complexite.get("type_problemes", "EXECUTION")), ex_complexite.get("type_problemes", "EXECUTION")),
            "complexite_environnement": _norm_enum(_pick(complexite, ["environnement"], ex_complexite.get("environnement", "ENTREPRISE")), ex_complexite.get("environnement", "ENTREPRISE")),

            # Hard skills
            "hs_niveau_maitrise_global": _norm_enum(_pick(hs, ["niveau_maitrise_global"], ex_hs.get("niveau_maitrise_global", "OPERATIONNEL")), ex_hs.get("niveau_maitrise_global", "OPERATIONNEL")),
            "hs_transversalite_competences": _norm_enum(_pick(hs, ["transversalite_competences"], ex_hs.get("transversalite_competences", "MOYENNE")), ex_hs.get("transversalite_competences", "MOYENNE")),
            "hs_autonomie_technique": _norm_enum(_pick(hs, ["autonomie_technique"], ex_hs.get("autonomie_technique", "SEMI_AUTONOME")), ex_hs.get("autonomie_technique", "SEMI_AUTONOME")),

            # Progression
            "progression_technique": _norm_enum(_pick(prog, ["technique"], ex_prog.get("technique", "MODEREE")), ex_prog.get("technique", "MODEREE")),
            "progression_hierarchique": _norm_enum(_pick(prog, ["hierarchique"], ex_prog.get("hierarchique", "MODEREE")), ex_prog.get("hierarchique", "MODEREE")),
            "progression_vitesse_relative": _norm_enum(_pick(prog, ["vitesse_relative"], ex_prog.get("vitesse_relative", "NORMALE")), ex_prog.get("vitesse_relative", "NORMALE")),

            # Coherence
            "coherence_continuite_thematique": _norm_enum(_pick(coh, ["continuite_thematique"], ex_coh.get("continuite_thematique", "MOYENNE")), ex_coh.get("continuite_thematique", "MOYENNE")),
            "coherence_logique_sectorielle": _norm_enum(_pick(coh, ["logique_sectorielle"], ex_coh.get("logique_sectorielle", "TRANSITION_PARTIELLE")), ex_coh.get("logique_sectorielle", "TRANSITION_PARTIELLE")),
            "coherence_narratif_professionnel": _norm_enum(_pick(coh, ["narratif_professionnel"], ex_coh.get("narratif_professionnel", "LOGIQUE")), ex_coh.get("narratif_professionnel", "LOGIQUE")),

            # Rarete
            "rarete_densite_competences_rares": _norm_enum(_pick(rarete, ["densite_competences_rares"], ex_rarete.get("densite_competences_rares", "QUELQUES")), ex_rarete.get("densite_competences_rares", "QUELQUES")),
            "rarete_combinaison_atypique": _norm_bool(_pick(rarete, ["combinaison_atypique"], ex_rarete.get("combinaison_atypique", False)), bool(ex_rarete.get("combinaison_atypique", False))),
            "rarete_exposition_internationale": _norm_bool(_pick(rarete, ["exposition_internationale"], ex_rarete.get("exposition_internationale", False)), bool(ex_rarete.get("exposition_internationale", False))),
            "rarete_contribution_reconnue": _norm_enum(_pick(rarete, ["contribution_reconnue"], ex_rarete.get("contribution_reconnue", "AUCUNE")), ex_rarete.get("contribution_reconnue", "AUCUNE")),

            # Stabilite
            "stabilite_coherence_parcours": _norm_enum(_pick(stab, ["coherence_parcours"], ex_stab.get("coherence_parcours", "LOGIQUE")), ex_stab.get("coherence_parcours", "LOGIQUE")),
            "stabilite_duree_typique_poste": _norm_enum(_pick(stab, ["duree_typique_poste", "duree"], ex_stab.get("duree_typique_poste", "NORMALE")), ex_stab.get("duree_typique_poste", "NORMALE")),
            "stabilite_engagement_long_terme": _norm_enum(_pick(stab, ["engagement_long_terme", "engagement"], ex_stab.get("engagement_long_terme", "MOYEN")), ex_stab.get("engagement_long_terme", "MOYEN")),

            # Communication
            "communication_clarte": _norm_enum(_pick(comm, ["clarte"], ex_comm.get("clarte", "CORRECTE")), ex_comm.get("clarte", "CORRECTE")),
            "communication_structure": _norm_enum(_pick(comm, ["structure"], ex_comm.get("structure", "ORGANISEE")), ex_comm.get("structure", "ORGANISEE")),
            "communication_precision_vocabulaire": _norm_enum(_pick(comm, ["precision_vocabulaire", "precision"], ex_comm.get("precision_vocabulaire", "TECHNIQUE")), ex_comm.get("precision_vocabulaire", "TECHNIQUE")),
            "communication_densite_informationnelle": _norm_enum(_pick(comm, ["densite_informationnelle", "densite"], ex_comm.get("densite_informationnelle", "STRUCTUREE")), ex_comm.get("densite_informationnelle", "STRUCTUREE")),

            # Signaux
            "signal_publication_scientifique": _norm_bool(_pick(signaux, ["publication_scientifique"], ex_signaux.get("publication_scientifique", False)), bool(ex_signaux.get("publication_scientifique", False))),
            "signal_responsabilite_budget": _norm_bool(_pick(signaux, ["responsabilite_budget"], ex_signaux.get("responsabilite_budget", False)), bool(ex_signaux.get("responsabilite_budget", False))),
            "signal_responsabilite_equipe": _norm_bool(_pick(signaux, ["responsabilite_equipe"], ex_signaux.get("responsabilite_equipe", False)), bool(ex_signaux.get("responsabilite_equipe", False))),
            "signal_gestion_risque_critique": _norm_bool(_pick(signaux, ["gestion_risque_critique"], ex_signaux.get("gestion_risque_critique", False)), bool(ex_signaux.get("gestion_risque_critique", False))),
            "signal_impact_marche_direct": _norm_bool(_pick(signaux, ["impact_marche_direct"], ex_signaux.get("impact_marche_direct", False)), bool(ex_signaux.get("impact_marche_direct", False))),
            "signal_experience_reglementee": _norm_bool(_pick(signaux, ["experience_reglementee"], ex_signaux.get("experience_reglementee", False)), bool(ex_signaux.get("experience_reglementee", False))),

            # Anomalies
            "anomalie_surdeclaration_seniority": _norm_bool(_pick(anom, ["surdeclaration_seniority"], ex_anom.get("surdeclaration_seniority", False)), bool(ex_anom.get("surdeclaration_seniority", False))),
            "anomalie_competences_sans_preuves": _norm_bool(_pick(anom, ["competences_sans_preuves", "competences_sans_preuves_significatives"], ex_anom.get("competences_sans_preuves_significatives", False)), bool(ex_anom.get("competences_sans_preuves_significatives", False))),
            "anomalie_absence_metriques_chiffrees": _norm_bool(_pick(anom, ["absence_metriques_chiffrees"], ex_anom.get("absence_metriques_chiffrees", False)), bool(ex_anom.get("absence_metriques_chiffrees", False))),
            "anomalie_incoherence_majeure_parcours": _norm_bool(_pick(anom, ["incoherence_majeure_parcours"], ex_anom.get("incoherence_majeure_parcours", False)), bool(ex_anom.get("incoherence_majeure_parcours", False))),
            "anomalie_keyword_stuffing_probable": _norm_bool(_pick(anom, ["keyword_stuffing_probable"], ex_anom.get("keyword_stuffing_probable", False)), bool(ex_anom.get("keyword_stuffing_probable", False))),
        }

        return flat
    
    def save_to_database(
        self,
        candidate_id: int,
        llm_evaluation: Dict[str, Any],
        scoring_result: Dict[str, Any]
    ) -> tuple[int, int, int]:
        """
        Sauvegarde dans les 3 tables: llm_evaluation_v2, score, score_family_projection.
        
        Returns:
            Tuple (llm_eval_id, score_id, projection_id)
        """
        cursor = self.db.cursor()
        
        try:
            # 1. Sauvegarder l'évaluation LLM
            flat_llm = self.flatten_llm_evaluation(llm_evaluation)
            
            llm_columns = ', '.join(flat_llm.keys())
            llm_placeholders = ', '.join(['%s'] * len(flat_llm))
            
            llm_insert_query = f"""
                INSERT INTO llm_evaluation_v2 
                (candidate_id, {llm_columns})
                VALUES (%s, {llm_placeholders})
            """
            
            llm_values = [candidate_id] + list(flat_llm.values())
            cursor.execute(llm_insert_query, llm_values)
            llm_eval_id = cursor.lastrowid
            
            print(f"Evaluation LLM sauvegardée (ID: {llm_eval_id})")
            
            # 2. Sauvegarder les scores calculés
            score_insert_query = """
                INSERT INTO score  (
                    candidate_id, llm_evaluation_id, engine_version,
                    score_global, decision,
                    
                    dim_impact, dim_impact_base, dim_impact_bonus_maturite, dim_impact_penalite,
                    impact_precision_score, impact_ampleur_score, impact_portee_score,
                    impact_repetition_score, impact_nature_coeff,
                    
                    dim_hard_skills_depth, hs_complexite_score, hs_maitrise_score,
                    hs_autonomie_score, hs_type_problemes_score, hs_transversalite_score,
                    
                    dim_coherence, coherence_progression_score, coherence_continuite_score,
                    coherence_logique_sectorielle_score,
                    
                    dim_rarete_marche, rarete_densite_score, rarete_combinaison_score,
                    rarete_contribution_score,
                    
                    dim_stabilite, stabilite_coherence_parcours_score, stabilite_duree_score,
                    stabilite_engagement_score,
                    
                    dim_communication, communication_clarte_score, communication_structure_score,
                    communication_precision_score, communication_densite_score
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
            """
            
            score_values = (
                candidate_id, llm_eval_id, scoring_result['engine_version'],
                scoring_result['score_global'], scoring_result['decision'],
                
                scoring_result['dim_impact'], scoring_result['dim_impact_base'],
                scoring_result['dim_impact_bonus_maturite'], scoring_result['dim_impact_penalite'],
                scoring_result['impact_precision_score'], scoring_result['impact_ampleur_score'],
                scoring_result['impact_portee_score'], scoring_result['impact_repetition_score'],
                scoring_result['impact_nature_coeff'],
                
                scoring_result['dim_hard_skills_depth'], scoring_result['hs_complexite_score'],
                scoring_result['hs_maitrise_score'], scoring_result['hs_autonomie_score'],
                scoring_result['hs_type_problemes_score'], scoring_result['hs_transversalite_score'],
                
                scoring_result['dim_coherence'], scoring_result['coherence_progression_score'],
                scoring_result['coherence_continuite_score'], 
                scoring_result['coherence_logique_sectorielle_score'],
                
                scoring_result['dim_rarete_marche'], scoring_result['rarete_densite_score'],
                scoring_result['rarete_combinaison_score'], scoring_result['rarete_contribution_score'],
                
                scoring_result['dim_stabilite'], scoring_result['stabilite_coherence_parcours_score'],
                scoring_result['stabilite_duree_score'], scoring_result['stabilite_engagement_score'],
                
                scoring_result['dim_communication'], scoring_result['communication_clarte_score'],
                scoring_result['communication_structure_score'], scoring_result['communication_precision_score'],
                scoring_result['communication_densite_score']
            )
            
            cursor.execute(score_insert_query, score_values)
            score_id = cursor.lastrowid
            
            print(f"Scores sauvegardés (ID: {score_id}, Global: {scoring_result['score_global']}/100)")
            
            # 3. Sauvegarder la projection familles
            fp = scoring_result['family_projection']
            
            projection_insert_query = """
                INSERT INTO score_family_projection (
                    score_id, candidate_id,
                    c_tech, c_business, c_science, c_org, c_health, c_legal, c_creative, c_ops,
                    v_tech, v_business, v_science, v_org, v_health, v_legal, v_creative, v_ops,
                    dominance_index, famille_dominante
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            projection_values = (
                score_id, candidate_id,
                fp['c_tech'], fp['c_business'], fp['c_science'], fp['c_org'],
                fp['c_health'], fp['c_legal'], fp['c_creative'], fp['c_ops'],
                fp['v_tech'], fp['v_business'], fp['v_science'], fp['v_org'],
                fp['v_health'], fp['v_legal'], fp['v_creative'], fp['v_ops'],
                fp['dominance_index'], fp['famille_dominante']
            )
            
            cursor.execute(projection_insert_query, projection_values)
            projection_id = cursor.lastrowid
            
            print(f"Projection familles sauvegardée (Dominante: {fp['famille_dominante']})")
            
            self.db.commit()
            
            return llm_eval_id, score_id, projection_id
            
        except Exception as e:
            self.db.rollback()
            print(f"âŒ Erreur sauvegarde DB: {e}")
            raise
        finally:
            cursor.close()
    
    def evaluate_candidate(
        self,
        talentcard: Dict[str, Any],
        candidate_id: int,
        chat_soft_skills_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Point d'entrée principal: évalue un candidat complet.
        
        Workflow:
        1. Construit le prompt (enrichi des soft skills chatbot si fournis)
        2. Appelle Claude
        3. Valide la réponse
        4. Calcule les scores via le moteur
        5. Sauvegarde en DB
        6. Retourne l'analyse complète
        
        Args:
            talentcard: Données du TalentCard JSON
            candidate_id: ID du candidat en base
            chat_soft_skills_text: Texte des soft skills déclarés par le candidat (question soft_skills_8_examples)
        
        Returns:
            Dictionnaire complet de l'analyse
        """
        print(f"\n{'='*60}")
        print(f"Évaluation du candidat #{candidate_id}")
        print(f"{'='*60}\n")
        
        # Étape 1: Construire le prompt
        print("Construction du prompt...")
        prompt = self.build_evaluation_prompt(talentcard, chat_soft_skills_text=chat_soft_skills_text)
        
        # Étape 2: Appeler Gemini
        print("Appel Gemini API...")
        llm_evaluation = self.call_gemini(prompt)
        
        # Le moteur de scoring attend un format aplati (impact_preuve_precision, etc.)
        llm_evaluation_flat = self.flatten_llm_evaluation(llm_evaluation)
        
        # Étape 3: Calculer les scores
        print("Calcul des scores...")
        scoring_result = self.engine.evaluate(llm_evaluation_flat)
        
        print(f"Score Global: {scoring_result['score_global']}/100")
        print(f"Decision: {scoring_result['decision']}")
        
        # Étape 4: Sauvegarder en DB
        print("Sauvegarde en base de données...")
        llm_eval_id, score_id, projection_id = self.save_to_database(
            candidate_id,
            llm_evaluation,
            scoring_result
        )
        
        # Étape 5: Construire la réponse complète
        response = {
            'metadata': {
                'candidate_id': candidate_id,
                'timestamp': datetime.now().isoformat(),
                'llm_evaluation_id': llm_eval_id,
                'score_id': score_id,
                'projection_id': projection_id,
                'engine_version': scoring_result['engine_version'],
                'llm_contract_version': self.llm_contract['contract_version']
            },
            'scores': {
                'score_global': scoring_result['score_global'],
                'decision': scoring_result['decision'],
                'dimensions': {
                    'impact': {
                        'score': scoring_result['dim_impact'],
                        'poids': 25,
                        'composantes': {
                            'precision': scoring_result['impact_precision_score'],
                            'ampleur': scoring_result['impact_ampleur_score'],
                            'portee': scoring_result['impact_portee_score'],
                            'repetition': scoring_result['impact_repetition_score']
                        }
                    },
                    'hard_skills_depth': {
                        'score': scoring_result['dim_hard_skills_depth'],
                        'poids': 25,
                        'composantes': {
                            'complexite': scoring_result['hs_complexite_score'],
                            'maitrise': scoring_result['hs_maitrise_score'],
                            'autonomie': scoring_result['hs_autonomie_score']
                        }
                    },
                    'coherence': {
                        'score': scoring_result['dim_coherence'],
                        'poids': 15
                    },
                    'rarete_marche': {
                        'score': scoring_result['dim_rarete_marche'],
                        'poids': 20
                    },
                    'stabilite': {
                        'score': scoring_result['dim_stabilite'],
                        'poids': 10
                    },
                    'communication': {
                        'score': scoring_result['dim_communication'],
                        'poids': 5
                    }
                }
            },
            'family_projection': scoring_result['family_projection'],
            'llm_evaluation_raw': llm_evaluation
        }
        # Soft skills déclarés par le candidat et évalués (uniquement quand chatbot a fourni le texte)
        ev = llm_evaluation.get('evaluation_soft_skills_declares')
        if isinstance(ev, list):
            response['evaluation_soft_skills_declares'] = [
                {'nom': str(item.get('nom', '')).strip() or 'Soft skill', 'niveau': str(item.get('niveau', 'MOYEN')).strip().upper() or 'MOYEN'}
                for item in ev if isinstance(item, dict)
            ]
        else:
            response['evaluation_soft_skills_declares'] = []
        
        print(f"\n{'='*60}")
        print("Evaluation terminée avec succès")
        print(f"{'='*60}\n")
        
        return response
        

        
    def export_json(self, analyse: Dict[str, Any], output_path: str):
        """
        Exporte l'analyse en JSON formaté.
        
        Args:
            analyse: Dictionnaire de l'analyse
            output_path: Chemin du fichier de sortie
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analyse, f, indent=2, ensure_ascii=False)
        
        print(f"Analyse exportée: {output_path}")


# Point d'entrée pour tests
if __name__ == '__main__':
    print("Agent Scoring V2 - Module importé avec succès")
    print("Utilisez: from agent_scoring_v2 import AgentScoringV2")
