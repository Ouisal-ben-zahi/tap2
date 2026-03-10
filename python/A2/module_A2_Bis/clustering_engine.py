from google import genai
from google.genai import types
import json
import os

api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)


# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 1 — Association sémantique : compétence ↔ expériences + réalisations
# ═══════════════════════════════════════════════════════════════════════════

def llm_associate(skills: list, experiences: list, realisations: list, dimensions: dict) -> dict:
    """
    Pour chaque compétence, le LLM analyse :
      - les expériences (Role, entreprise, periode, description)
      - les réalisations (strings libres)
    Et extrait : has_metric, scope, nb_exp, is_recent

    Particularités de la structure réelle :
      - les métriques sont dans le texte libre de 'description' (pas de champ séparé)
      - la récence est inférée depuis le champ 'periode' (string, ex: "Août 2025")
      - les réalisations comptent comme expériences supplémentaires (preuves de compétences)
    """
    prompt = f"""
    Tu es un expert RH technique. Associe chaque compétence à ses preuves concrètes.

    DATE DE RÉFÉRENCE : février 2026 (pour évaluer la récence).

    COMPÉTENCES À ANALYSER :
    {json.dumps(skills, indent=2, ensure_ascii=False)}

    EXPÉRIENCES PROFESSIONNELLES (indexées à partir de 0) :
    {json.dumps(experiences, indent=2, ensure_ascii=False)}

    RÉALISATIONS / PROJETS (indexées à partir de 0) :
    {json.dumps(realisations, indent=2, ensure_ascii=False)}

    CONTEXTE DIMENSIONNEL DU PROFIL :
    {json.dumps(dimensions, indent=2, ensure_ascii=False)}

    ════════════════════════════════════════════════════════
    MISSION — Pour chaque compétence, détermine :

    1. related_exp_indices : indices des EXPÉRIENCES où la compétence est mobilisée.

    2. related_real_indices : indices des RÉALISATIONS qui prouvent cette compétence.

    3. has_metric : true si au minimum une expérience OU réalisation liée contient
       une donnée chiffrée (%, nombre, ratio, durée, volume) attribuable DIRECTEMENT
       à CETTE compétence.
       → Cherche dans le texte libre de 'description'.
       → Exemple : "basée sur K-means et DbScan" n'est PAS une métrique chiffrée.
       → Exemple : "réduction de 30%" ou "sur 2M transactions" SONT des métriques.

    4. scope : meilleure portée parmi toutes les preuves liées :
       - "individuel"   → projet solo / usage personnel
       - "equipe"       → contribution à une équipe (2-20 personnes)
       - "organisation" → impact sur toute une organisation / département
       - "marche"       → produit publié / impact external / utilisateurs réels
       Défaut "individuel" si aucune preuve liée.

    5. nb_exp : total d'expériences + réalisations liées.

    6. is_recent : true si au moins une preuve liée a une période <= 18 mois
       avant février 2026 (soit après août 2024).
       → Analyse le champ 'periode' des expériences (ex: "Août 2025" = récent).
       → Les réalisations sans date sont considérées récentes par défaut.

    RÈGLES :
    - Une réalisation comme "Classification de texte NLP avec spaCy & NLTK"
      est une preuve directe pour NLP, spaCy, NLTK — mais PAS pour Python seul.
    - Un outil (Python) peut être lié à plusieurs expériences/réalisations
      même si c'est implicite dans la description.
    - Sois précis : ne lie une compétence que si elle est réellement exercée.

    FORMAT (JSON STRICT) :
    {{
      "associations": {{
        "NomCompetence1": {{
          "related_exp_indices":  [0],
          "related_real_indices": [1, 2],
          "has_metric":  false,
          "scope":       "individuel",
          "nb_exp":      3,
          "is_recent":   true
        }},
        "NomCompetence2": {{
          "related_exp_indices":  [],
          "related_real_indices": [],
          "has_metric":  false,
          "scope":       "individuel",
          "nb_exp":      0,
          "is_recent":   false
        }}
      }}
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json'),
        )
        parsed = json.loads(response.text)
        return parsed.get("associations", {})

    except Exception as e:
        print(f"❌ Erreur LLM Association : {e}")
        return {
            skill: {
                "related_exp_indices":  [],
                "related_real_indices": [],
                "has_metric": False,
                "scope":      "individuel",
                "nb_exp":     0,
                "is_recent":  False
            }
            for skill in skills
        }


# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 3 — Nommage contextuel + stack
# ═══════════════════════════════════════════════════════════════════════════

def llm_clusterize(profile_context: dict, scored_skills: list) -> dict:
    """
    Reçoit les compétences scorées individuellement.
    Produit : nom contextuel précis + stack + level (core/secondaire).
    """
    scores_block = profile_context.get("scores", {})
    dimensions   = scores_block.get("dimensions", {})
    dim_summary  = {
        dim: {"score": v.get("score", 0), "poids": v.get("poids", 0)}
        for dim, v in dimensions.items()
    }

    prompt = f"""
    Tu es un expert en recrutement technique.

    CONTEXTE DU PROFIL :
    - Décision   : {scores_block.get('decision', 'N/A')}
    - Score (/5) : {round(scores_block.get('score_global', 0) / 100 * 5, 2)}
    - Dimensions :
    {json.dumps(dim_summary, indent=6, ensure_ascii=False)}

    COMPÉTENCES SCORÉES (score /5 — ne pas modifier) :
    {json.dumps(scored_skills, indent=2, ensure_ascii=False)}

    MISSION : retourne la liste triée par score décroissant.

    RÈGLES DE NOMMAGE :
    1. Le "name" = TOUJOURS le champ "original_name" tel quel, sans modification.
       Ex : "Machine Learning", "NLP", "Computer Vision", "Scikit-learn", "Python".
       N'utilise JAMAIS "esco_label" comme name — c'est un champ interne à ignorer.

    2. ORDRE à score égal : domaines métier avant outils.
       Domaines : Machine Learning, NLP, Computer Vision, Optimisation, Clustering...
       Outils    : Python, TensorFlow, PyTorch, Scikit-learn, OpenCV...

    3. stack = 3-5 VRAIS outils/frameworks/libs concrets utilisés pour cette compétence.
       - Pour un domaine (Machine Learning) → cite les frameworks qui l'implémentent :
         ["Python", "Scikit-learn", "TensorFlow", "PyTorch"]
       - Pour un outil (Python) → cite les libs utilisées dans ce profil :
         ["NumPy", "Pandas", "Scikit-learn", "Matplotlib"]
       - INTERDIT dans la stack : mettre une compétence de la liste comme outil d'elle-même.
         Ex : "computer vision" n'est PAS un outil dans la stack de "Computer Vision".
       - Préfère les outils mentionnés dans exp_context (réalisations, expériences liées).

    4. level = "core" si compétence fait partis des compétences attendues pour la spécialité du profil, "secondaire" sinon.
    5. Reprends score et status tels quels.

    FORMAT (JSON STRICT) :
    {{
      "competencies": [
        {{
          "name":   "original_name exact",
          "score":  0.0,
          "status": "valide",
          "scope":  "core",
          "stack":  ["outil1", "outil2", "outil3"]
        }}
      ]
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json'),
        )

        print("\n🔍 [DEBUG] Gemini clusterize :")
        print(response.text[:500])

        parsed = json.loads(response.text)
        if "competencies" in parsed:
            return parsed
        for key, val in parsed.items():
            if isinstance(val, list) and len(val) > 0:
                print(f"⚠️  Clé inattendue : '{key}' utilisée")
                return {"competencies": val}
        return {"competencies": []}

    except Exception as e:
        print(f"❌ Erreur Gemini (clusterize) : {e}")
        return {"competencies": []}