# Mémoire des validations utilisateur (Agent Memory)

## Objectif

Permettre aux agents (B1 CV corrigé, puis B2/B3 si besoin) d’**apprendre à partir des validations utilisateur** :  
quand l’utilisateur valide (approuve / rejette / demande révision) avec un commentaire, cette information est sauvegardée et réinjectée dans les prochains prompts pour que l’IA améliore sa sortie.

En résumé : **sauvegarde mémoire** pour l’option « l’agent corrige ses problèmes lui-même » à partir des validations.

## État actuel

- **Avant** : seul le dernier feedback du **même candidat** était utilisé lors d’une régénération (champ `feedback_comment` dans `corrected_cv_versions`).
- **Maintenant** :
  1. **Sauvegarde** : à chaque validation (approved / rejected / needs_revision), l’appel enregistre dans `agent_validation_memory` (agent_id, status, feedback_comment, candidate_id).
  2. **Injection** : à chaque génération du CV corrigé (B1), le prompt reçoit un bloc « APPRENTISSAGE À PARTIR DES VALIDATIONS UTILISATEUR » construit à partir des N derniers rejets/révisions **dont le commentaire est considéré comme général** (règles, format, style). Les retours **personnels** (nom, formation, expérience précise d’un candidat) sont exclus pour ne pas appliquer les corrections d’un candidat aux autres. Si au moins un retour personnel a été exclu, un rappel générique est ajouté : « respecter strictement les données de la fiche candidat sans en inventer ».

Ainsi l’IA apprend des **règles générales** (longueur, format des dates, ne pas inventer, etc.) sans réutiliser les données personnelles des candidats.

## Fichiers

- **`agent_memory.py`**  
  - `save_validation(agent_id, validation_status, feedback_comment=None, candidate_id=None)` : enregistre une validation.  
  - `get_memory_for_prompt(agent_id, max_items=10)` : retourne le texte à injecter dans le prompt (rejets/révisions avec commentaire).

- **Base de données**  
  - Migration : `database/08_agent_validation_memory.sql` (table `agent_validation_memory`).

- **Intégration**  
  - **B1 (CV corrigé)** :  
    - Lors de la validation du CV : `app.py` → `validate_corrected_cv` appelle `save_validation("B1", ...)`.  
    - Lors de la génération : `B1/generate_corrected_cv.py` → `prepare_prompt` appelle `get_memory_for_prompt("B1")` et ajoute le texte au prompt.

## Étendre à d’autres agents (B2, B3)

1. Lors d’une action de validation côté front (ex. « Valider / Rejeter portfolio » ou « Valider entretien »), appeler une route qui enregistre la validation puis appeler `save_validation("B2", ...)` ou `save_validation("B3", ...)`.
2. Dans le module qui construit le prompt de l’agent (B2 ou B3), appeler `get_memory_for_prompt("B2")` ou `get_memory_for_prompt("B3")` et concaténer le résultat au prompt système ou utilisateur.

Après avoir appliqué la migration `08_agent_validation_memory.sql`, la mémoire est opérationnelle pour B1 ; B2/B3 deviennent « apprenants » dès qu’on ajoute les appels à `save_validation` et `get_memory_for_prompt` comme ci-dessus.
