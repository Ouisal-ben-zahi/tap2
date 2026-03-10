# Architecture — Agent intelligent de matching Offres / Candidats

## Objectifs

1. **Classer** les candidats par compatibilité sémantique avec le poste (embeddings, pas mots-clés).
2. **Justifier** chaque classement (score /100, forces, manques, raison du rang) via LLM.
3. **Apprendre** des décisions recruteur (feedback → bonus/pénalité ou re-ranking).
4. **Évoluer** : embeddings pré-calculés, pipeline modulaire, scalable.

---

## Stack technique

| Composant        | Choix                    | Alternative (contrainte)   |
|------------------|--------------------------|----------------------------|
| Embeddings       | sentence-transformers    | —                          |
| Similarité       | sklearn cosine_similarity| numpy / pgvector           |
| API              | Flask (existant)         | FastAPI si migration       |
| Base             | MySQL (existant)          | PostgreSQL + pgvector      |
| Stockage vecteurs| JSON/BLOB (MySQL)        | pgvector si PostgreSQL     |

---

## Structure des modules

```
backend/A4/
├── ARCHITECTURE_MATCHING_AGENT.md   # Ce document
├── weighted_matching.py            # Existant (TF-IDF, multi-critères) — conservé pour compatibilité
├── agent/
│   ├── __init__.py
│   ├── config.py           # Modèle, dimensions, seuils, poids
│   ├── embeddings.py       # Service embeddings (sentence-transformers)
│   ├── pipeline.py        # Pipeline: filtre → similarité → rank → top N
│   ├── justification.py   # Appel LLM → explication structurée
│   └── feedback.py        # Stockage décisions + bonus/pénalité re-rank
├── storage/
│   └── (embeddings en base — voir migrations)
```

---

## 1. Embeddings sémantiques (`agent/embeddings.py`)

- **Rôle** : transformer texte (CV, offre) en vecteur fixe.
- **Modèle** : `sentence-transformers` (ex. `paraphrase-multilingual-MiniLM-L12-v2` pour FR).
- **API** :
  - `embed_text(text: str) -> np.ndarray`
  - `embed_job(job_id: int) -> np.ndarray` (titre + skills + mission + langues, etc.)
  - `embed_candidate(candidate_id: int) -> np.ndarray` (titre_profil + skills + résumé + langues)
- **Cache** : vecteurs candidats stockés en base (`candidate_embeddings`); recalcul si CV/profil modifié.
- **Pas de TF-IDF** : tout le matching sémantique repose sur ces vecteurs.

---

## 2. Pipeline de matching (`agent/pipeline.py`)

- **Étape 1 — Filtrage minimal**  
  - Domaine (categorie_profil) aligné sur l’offre.  
  - Optionnel : compétences critiques (ex. au moins 1 skill obligatoire présent).  
  - Réduit le nombre de candidats avant calcul de similarité.

- **Étape 2 — Similarité vectorielle**  
  - Vecteur de l’offre : `embed_job(job_id)`.  
  - Vecteurs candidats : chargés depuis `candidate_embeddings` (ou calcul à la volée si absent).  
  - Score = **cosine_similarity**(job_embedding, candidate_embedding).

- **Étape 3 — Classement**  
  - Tri par score de similarité décroissant.

- **Étape 4 — Top N**  
  - Retourner les N premiers (ex. N=20).

- **Étape 5 (optionnelle) — Re-ranking avec feedback**  
  - Appliquer bonus (candidat souvent sélectionné) / pénalité (souvent rejeté) pour ajuster l’ordre.

Sortie pipeline : liste de `(candidate_id, similarity_score)`.

---

## 3. Justification automatique (`agent/justification.py`)

- **Entrée** : `job_id`, liste des top N candidats (id + résumé profil).
- **Appel LLM** (prompt structuré) pour chaque candidat (ou batch) :  
  - Score sur 100.  
  - Forces principales.  
  - Manques éventuels.  
  - Raison du classement (1–2 phrases).
- **Sortie** : pour chaque candidat, objet structuré :  
  `{ "score_100": int, "strengths": list[str], "weaknesses": list[str], "explanation": str }`.
- **Modulaire** : scoring (pipeline) et justification (LLM) sont découplés ; on peut désactiver la justification ou changer de LLM.

---

## 4. Apprentissage continu / feedback (`agent/feedback.py`)

- **Table** : `matching_feedback (id, job_id, candidate_id, decision, created_at)`  
  - `decision` : `selected` | `rejected`.
- **Utilisation** :  
  - Lors du matching : pour chaque candidat, regarder l’historique (ex. taux de sélection global ou sur jobs similaires).  
  - **Bonus** si souvent sélectionné (ex. +0.05 sur le score).  
  - **Pénalité** si souvent rejeté (ex. -0.05).  
- **Évolution** : plus tard, possible d’entraîner un petit modèle de re-ranking ou d’ajuster des poids à partir de ces signaux.

---

## 5. Base de données

### Nouvelles tables

- **`candidate_embeddings`**  
  - `candidate_id` (PK, FK), `embedding` (JSON ou BLOB : liste de floats), `model_version`, `updated_at`.  
  - Permet de pré-calculer et réutiliser les vecteurs sans recalcul à chaque match.

- **`matching_feedback`**  
  - `id` (PK), `job_id`, `candidate_id`, `decision` (ENUM ou VARCHAR : selected/rejected), `created_at`.  
  - Optionnel : `recruiter_id`, `comment`.

- **`job_embeddings`** (optionnel, pour cache)  
  - `job_id`, `embedding`, `model_version`, `updated_at`.  
  - Si on ne veut pas recalculer l’embedding de l’offre à chaque requête.

---

## 6. API

- **Match** : `POST /api/recruteur/match`
  - Body : `{ "job_id": int, "top_n": int (optionnel, défaut 20), "with_explanation": bool (optionnel, défaut true) }`.
  - Réponse : liste d’objets ci-dessous.
- **Feedback** : `POST /api/recruteur/match/feedback`
  - Body : `{ "job_id": int, "candidate_id": int, "decision": "selected" | "rejected" }`.
  - Enregistre la décision pour le re-ranking futur.

Réponse typique `/match` :

```json
[
  {
    "candidate_id": 1,
    "score": 0.87,
    "similarity_score": 0.87,
    "explanation": "Profil très aligné avec la mission data...",
    "strengths": ["Python", "ML", "expérience 5 ans"],
    "weaknesses": ["Pas de Spark"]
  }
]
```

- **Flux** :  
  1. Pipeline → top N par similarité (et feedback si activé).  
  2. Si `with_explanation` : appel justification LLM pour chaque élément du top N.  
  3. Agrégation et retour JSON.

---

## 7. Contraintes respectées

- **Scalable** : embeddings pré-calculés, filtrage avant similarité, top N limité.
- **Pas de mots exacts** : similarité uniquement sur vecteurs (sentence-transformers).
- **Modulaire** :  
  - scoring (embeddings + pipeline) séparé de la justification (LLM);  
  - feedback séparé (stockage + application au re-rank).
- **Production-ready** : config centralisée, erreurs gérées, dépendances optionnelles (sentence-transformers chargé à l’usage).

---

## 8. Dépendances à ajouter

- `sentence-transformers`
- `numpy` (souvent déjà présent via sklearn)
- Modèle téléchargé au premier usage (ex. `paraphrase-multilingual-MiniLM-L12-v2`).

---

## 9. Ordre d’implémentation recommandé

1. **config** + **embeddings** (embed_text, embed_job, embed_candidate + écriture/lecture en base).  
2. **Migrations** : `candidate_embeddings`, `matching_feedback` (et optionnellement `job_embeddings`).  
3. **pipeline** : filtre → similarité → rank → top N.  
4. **feedback** : enregistrement des décisions + application bonus/pénalité dans le pipeline.  
5. **justification** : appel LLM, format de sortie structuré.  
6. **API** : route `/api/recruteur/match` qui enchaîne pipeline → (justification) → réponse.

Après cela, on peut faire évoluer (pgvector, FastAPI, modèle de re-ranking entraîné sur le feedback) sans casser le reste.
