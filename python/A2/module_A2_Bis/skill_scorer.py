import logging

logger = logging.getLogger("SkillScorer")

# Mapping portée → valeur normalisée 0-1
SCOPE_MAP = {
    "individuel":   0.25,
    "equipe":       0.50,
    "organisation": 0.75,
    "marche":       1.00
}


class SkillScorer:
    """
    Notation déterministe d'une compétence sur /5.

    MÊME procédure pour toutes les compétences.
    Ce qui varie = le contexte sémantique (produit par le LLM d'association).

    Critères (poids configurables dans le contrat JSON) :
    ┌─────────────┬────────────────────────────────────────────────────┐
    │ base        │ Score global du profil normalisé (0-100 → 0-1)     │
    │ proof       │ Exp associée avec métrique=1.0 / sans=0.5 / rien=0 │
    │ scope       │ Meilleure portée parmi les exp associées           │
    │ repetition  │ Nb d'exp liées, plafonné à 3                       │
    │ recency     │ Au moins une exp récente (< 2 ans)                 │
    └─────────────┴────────────────────────────────────────────────────┘
    """

    def __init__(self, criteria: dict, target_scale: float = 5.0):
        self.criteria     = criteria       # {"base": 0.30, "proof": 0.30, ...}
        self.target_scale = target_scale   # 5.0

    def score(self, skill_context: dict, score_global: float) -> float:
        """
        Parameters
        ----------
        skill_context : dict produit par llm_associate()
            {
                "has_metric": bool,    # exp liée avec métrique chiffrée relative à la compétence
                "scope":      str,     # individuel / equipe / organisation / marche
                "nb_exp":     int,     # nombre d'expériences associées
                "is_recent":  bool     # au moins une exp < 2 ans
            }
        score_global : float (0-100)   # score du profil issu de A1

        Returns
        -------
        float  note de la compétence sur /5
        """
        c = self.criteria

        # ── Critère 1 : base ──────────────────────────────────────────────
        v_base = score_global / 100.0

        # ── Critère 2 : proof ─────────────────────────────────────────────
        if skill_context.get("has_metric"):
            v_proof = 1.0          # exp liée ET métrique chiffrée → bonus plein
        elif skill_context.get("nb_exp", 0) > 0:
            v_proof = 0.5          # exp liée mais sans métrique → demi-bonus
        else:
            v_proof = 0.0          # aucune exp associée → pas de proof

        # ── Critère 3 : scope ─────────────────────────────────────────────
        v_scope = SCOPE_MAP.get(skill_context.get("scope", "individuel"), 0.25)

        # ── Critère 4 : repetition ────────────────────────────────────────
        nb_exp       = min(skill_context.get("nb_exp", 0), 3)
        v_repetition = nb_exp / 3.0

        # ── Critère 5 : recency ───────────────────────────────────────────
        v_recency = 1.0 if skill_context.get("is_recent") else 0.0

        # ── Score final ───────────────────────────────────────────────────
        raw = (
            v_base       * c.get("base",       0.30) +
            v_proof      * c.get("proof",      0.30) +
            v_scope      * c.get("scope",      0.15) +
            v_repetition * c.get("repetition", 0.15) +
            v_recency    * c.get("recency",    0.10)
        )

        logger.debug(
            f"  base={v_base:.2f} proof={v_proof:.2f} scope={v_scope:.2f} "
            f"rep={v_repetition:.2f} rec={v_recency:.2f} → raw={raw:.3f} → /5={raw*self.target_scale:.2f}"
        )

        return round(max(0.0, min(raw * self.target_scale, self.target_scale)), 2)
