import json
import logging
import os
from typing import Dict, List, Any

if __package__:
    from .esco_connector import EscoConnector
    from .clustering_engine import llm_associate, llm_clusterize
    from .skill_scorer import SkillScorer
else:
    # Fallback quand le script est exécuté directement depuis ce dossier
    from esco_connector import EscoConnector
    from clustering_engine import llm_associate, llm_clusterize
    from skill_scorer import SkillScorer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("A2_Dynamic_Agent")


class A2BisDynamicAgent:
    """
    Agent de scoring SEMI-DÉTERMINISTE.

    Structure d'entrée attendue :
    {
        "competences":  ["Python", "NLP", ...],          # anciennement skills
        "experiences":  [ { Role, entreprise, periode, description }, ... ],
        "projets":      ["Réalisation 1", "Réalisation 2", ...],  # strings libres
        "scores": {
            "score_global": 65.3,
            "decision":     "BON",
            "dimensions":   { ... }
        }
    }

    Pipeline :
    ┌──────────────────────────────────────────────────────────────┐
    │ 0. ESCO        Normalisation des noms + suggestions stack    │
    │ 1. LLM         Association compétence ↔ exp + réalisations  │
    │ 2. DÉTERMINISTE SkillScorer → note individuelle /5          │
    │ 3. LLM         Nommage contextuel + stack enrichie           │
    └──────────────────────────────────────────────────────────────┘
    """

    def __init__(self, weights_path: str = "agent_contract_weights.json", api_url: str = "http://localhost:8080"):
        if not os.path.isabs(weights_path):
            weights_path = os.path.join(os.path.dirname(__file__), weights_path)
        self.weights_config = self._load_json(weights_path)
        self.esco = EscoConnector(api_url)

        criteria     = self.weights_config.get("skill_scoring_criteria", {})
        target_scale = self.weights_config.get("normalization", {}).get("target_scale", 5.0)
        self.scorer  = SkillScorer(criteria, target_scale)

        logger.info("A2 Dynamic Agent initialisé.")

    def _load_json(self, path: str) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def process_competencies(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Paramètre unique : le dict complet issu de A1/l'extracteur.

        Accepte les deux conventions de clés :
          compétences : "competences" ou "skills"
          expériences : "experiences" ou "experience"
          réalisations: "projets"     ou "realisations"
        """
        # ── Lecture tolérante des clés ─────────────────────────────────────────
        input_skills  = (input_data.get("competences")
                         or input_data.get("skills", []))
        experiences   = (input_data.get("experiences")
                         or input_data.get("experience", []))
        realisations  = (input_data.get("projets")
                         or input_data.get("realisations", []))
        scores_block  = input_data.get("scores", {})
        score_global  = scores_block.get("score_global", 0.0)
        dimensions    = scores_block.get("dimensions", {})

        # has_proof : déduit du score de cohérence (>= 60 = validé)
        coherence_score  = dimensions.get("coherence", {}).get("score", 0.0)
        has_proof_global = coherence_score >= 60.0

        # ── Étape 0 : Validation ESCO ──────────────────────────────────────────
        print(f"🔄 Validation ESCO pour {len(input_skills)} compétences...")
        esco_map = {}
        for raw_name in input_skills:
            esco_data = self.esco.search_skill(raw_name)
            if esco_data:
                uri              = esco_data['uri']
                normalized       = esco_data['title']
                related          = self.esco.get_related_skills(uri)
                esco_suggestions = [r['technology_name'] for r in related]
            else:
                uri              = "unknown"
                normalized       = raw_name
                esco_suggestions = []

            esco_map[raw_name] = {
                "normalized_name":  normalized,
                "esco_suggestions": esco_suggestions
            }

        # ── Étape 1 : LLM — Association sémantique ────────────────────────────
        print(f"🔗 Association sémantique ({len(input_skills)} compétences"
              f" × {len(experiences)} exp + {len(realisations)} réalisations)...")

        associations = llm_associate(input_skills, experiences, realisations, dimensions)

        # ── Étape 2 : Déterministe — SkillScorer ──────────────────────────────
        print("🧮 Scoring individuel déterministe...")
        scored_skills = []

        for raw_name in input_skills:
            skill_ctx = associations.get(raw_name, {
                "related_exp_indices":  [],
                "related_real_indices": [],
                "has_metric": False,
                "scope":      "individuel",
                "nb_exp":     0,
                "is_recent":  False
            })

            individual_score = self.scorer.score(skill_ctx, score_global)
            esco_info        = esco_map[raw_name]

            scored_skills.append({
                "original_name":   raw_name,          # nom lisible — utilisé pour l'affichage
                "normalized_name": raw_name,           # on garde le nom original : ESCO est trop générique pour les frameworks techniques
                "esco_label":      esco_info["normalized_name"],  # label ESCO conservé pour usage interne uniquement
                "score":           individual_score,
                "status":          "valide" if has_proof_global else "declare",
                "esco_suggestions": esco_info["esco_suggestions"],
                "exp_context": {
                    "nb_exp_liees":        skill_ctx.get("nb_exp", 0),
                    "has_metric":          skill_ctx.get("has_metric", False),
                    "scope":               skill_ctx.get("scope", "individuel"),
                    "is_recent":           skill_ctx.get("is_recent", False),
                    "exp_indices":         skill_ctx.get("related_exp_indices", []),
                    "realisation_indices": skill_ctx.get("related_real_indices", [])
                }
            })

        logger.info("Scores individuels : %s",
                    {s["original_name"]: s["score"] for s in scored_skills})

        # ── Étape 3 : LLM — Nommage contextuel + stack ────────────────────────
        print("🧠 Nommage contextuel et enrichissement stack...")
        return llm_clusterize(input_data, scored_skills)
