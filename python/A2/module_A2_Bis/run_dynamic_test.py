import time
from A2_bis_dynamic_agent import A2BisDynamicAgent

# ═══════════════════════════════════════════════════════════════════
# Signal d'entrée — structure réelle issue de A1 + extracteur CV
# ═══════════════════════════════════════════════════════════════════
INPUT_DATA = {
    # Clés exactes telles qu'elles arrivent dans mon_dict
    "competences": [
        "Python",
        "Machine Learning",
        "TensorFlow",
        "PyTorch",
        "Scikit-learn",
        "NLP",
        "Computer Vision",
        "Optimisation"
    ],
    "experiences": [
        {
            "Role":        "Stagiaire en développement et d'algorithmes de clustering",
            "entreprise":  "Université Euromed de Fes",
            "periode":     "Août 2025",
            "description": (
                "Conception et implémentation d'une nouvelle méthode de clustering "
                "basée sur K-means et DbScan."
            )
        }
    ],
    "projets": [
        "Classification de texte NLP avec spaCy & NLTK",
        "Détection d'objets sur images en Computer Vision avec OpenCV et TensorFlow",
        "Modélisation et ordonnancement d'atterrissage d'avions"
    ],
    # Scores issus de A1
    "scores": {
        "score_global": 65.3,
        "decision": "BON",
        "dimensions": {
            "impact": {
                "score": 49.3,
                "poids": 25,
                "composantes": {
                    "precision":  50.0,
                    "ampleur":    30.0,
                    "portee":     40.0,
                    "repetition": 70.0
                }
            },
            "hard_skills_depth": {
                "score": 70.97,
                "poids": 25,
                "composantes": {
                    "complexite": 70.0,
                    "maitrise":   85.0,
                    "autonomie":  85.0
                }
            },
            "coherence": {
                "score": 84.4,
                "poids": 15
            },
            "rarete_marche": {
                "score": 45.0,
                "poids": 20
            },
            "stabilite": {
                "score": 89.5,
                "poids": 10
            },
            "communication": {
                "score": 92.5,
                "poids": 5
            }
        }
    }
}


def run():
    print("🚀 Démarrage de l'Agent A2_bis...\n")

    agent = A2BisDynamicAgent()

    start_time = time.time()
    results    = agent.process_competencies(INPUT_DATA)
    duration   = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"  RAPPORT A2 (ESCO + GEMINI) — {duration:.2f}s")
    print("=" * 60)

    competencies = results.get("competencies", [])

    if competencies:
        print(f"\n📋 {len(competencies)} compétence(s) — triées par score :\n")

        for i, comp in enumerate(competencies, 1):
            score  = comp.get("score",  0.0)
            status = comp.get("status", "declare")
            level  = comp.get("level",  "secondaire")
            stack  = comp.get("stack",  [])

            badge_status = "✅ Validé"  if status == "valide" else "📝 Déclaré"
            badge_level  = "⭐ Core"    if level  == "core"   else "🔹 Secondaire"
            filled = round(score)
            bar    = "█" * filled + "░" * (5 - filled)

            print(f"  {i:02d}. {comp['name']}")
            print(f"       Score   : {bar}  {score:.2f}/5")
            print(f"       Statut  : {badge_status}   Niveau : {badge_level}")
            if stack:
                print(f"       Stack   : {' · '.join(stack)}")
            print()

        avg = sum(c.get("score", 0) for c in competencies) / len(competencies)
        print(f"  SCORE MOYEN : {avg:.2f} / 5.0")
    else:
        print("⚠️  Aucun résultat.")

    print("\n" + "=" * 60 + "\nFin du traitement.")


if __name__ == "__main__":
    run()