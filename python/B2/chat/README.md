# Chatbot Portfolio - Documentation Simple

## 📋 Vue d'ensemble

Ce chatbot simple permet de collecter les informations nécessaires pour générer un portfolio professionnel. Il pose des questions ciblées une par une jusqu'à ce que tous les champs obligatoires soient remplis.

## 🗄️ Structure de la base de données

### Table `portfolio_sessions`

```sql
CREATE TABLE portfolio_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL UNIQUE,
    candidate_id INT NOT NULL,
    profile JSON NOT NULL,
    missing_fields JSON NOT NULL,
    current_question_key VARCHAR(100) NULL,
    current_question TEXT NULL,
    asked_questions JSON NOT NULL,
    is_complete BOOLEAN DEFAULT FALSE,
    extracted_data JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**Installation :**
```bash
mysql -u root -p tap_db < database/create_portfolio_sessions_table.sql
```

## 📦 Structure des données

### Profil Portfolio

```json
{
  "nom": "Jean Dupont",
  "titre_professionnel": "Développeur Full-Stack",
  "pitch": "Développeur passionné avec 5 ans d'expérience...",
  "competences": ["Python", "React", "Node.js"],
  "projets": [
    {
      "nom": "Application E-commerce",
      "description": "Application complète avec React et Node.js",
      "lien": "https://github.com/user/project"
    }
  ],
  "liens": {
    "linkedin": "https://linkedin.com/in/jeandupont",
    "github": "https://github.com/jeandupont",
    "portfolio": "",
    "autre": ""
  }
}
```

### Champs obligatoires

- `nom` : Nom complet
- `titre_professionnel` : Titre actuel
- `pitch` : Description personnelle (2-3 lignes)
- `competences` : Liste des compétences techniques
- `projets` : Au moins un projet détaillé
- `liens` : Au moins un lien (LinkedIn, GitHub, etc.)

## 🔌 API Endpoints

### 1. Démarrer une session

**POST** `/portfolio/start`

**Body :**
```json
{
  "candidate_id": 123,
  "extracted_data": {
    "nom": "Jean",
    "prenom": "Dupont",
    "titre_profil": "Développeur",
    "skills": ["Python", "React"],
    "linkedin": "https://linkedin.com/in/jeandupont"
  }
}
```

**Response :**
```json
{
  "success": true,
  "session_id": "uuid-here",
  "question": "Quel est votre nom complet ?",
  "is_complete": false,
  "profile": { ... },
  "missing_fields": ["nom", "titre_professionnel", ...]
}
```

### 2. Envoyer un message (réponse)

**POST** `/portfolio/<session_id>/message`

**Body :**
```json
{
  "message": "Jean Dupont"
}
```

**Response :**
```json
{
  "success": true,
  "session_id": "uuid-here",
  "question": "Quel est votre titre professionnel actuel ?",
  "is_complete": false,
  "profile": { ... },
  "missing_fields": ["titre_professionnel", ...],
  "filled_field": "nom"
}
```

### 3. Récupérer l'état de la session

**GET** `/portfolio/<session_id>/state`

**Response :**
```json
{
  "success": true,
  "session_id": "uuid-here",
  "state": {
    "session_id": "uuid-here",
    "candidate_id": 123,
    "profile": { ... },
    "missing_fields": [...],
    "current_question_key": "titre_professionnel",
    "current_question": "Quel est votre titre professionnel actuel ?",
    "asked_questions": ["nom"],
    "is_complete": false
  }
}
```

## 🔄 Flux d'utilisation

1. **Démarrer la session** : Appeler `/portfolio/start` avec le `candidate_id` et les données extraites (optionnel)
2. **Poser la première question** : Le chatbot retourne automatiquement la première question
3. **Boucle de questions/réponses** :
   - L'utilisateur répond via `/portfolio/<session_id>/message`
   - Le chatbot extrait l'information et met à jour le profil
   - Le chatbot pose la question suivante
   - Répéter jusqu'à ce que `is_complete = true`
4. **Récupérer le profil final** : Utiliser `/portfolio/<session_id>/state` pour obtenir le profil complet

## 📝 Exemple d'utilisation (Python)

```python
import requests

BASE_URL = "http://localhost:5002"

# 1. Démarrer la session
response = requests.post(f"{BASE_URL}/portfolio/start", json={
    "candidate_id": 123,
    "extracted_data": {
        "nom": "Jean",
        "prenom": "Dupont",
        "skills": ["Python", "React"]
    }
})
data = response.json()
session_id = data["session_id"]
print(f"Question: {data['question']}")

# 2. Répondre aux questions
while not data["is_complete"]:
    user_answer = input(f"\nRéponse: ")
    
    response = requests.post(
        f"{BASE_URL}/portfolio/{session_id}/message",
        json={"message": user_answer}
    )
    data = response.json()
    
    if data["question"]:
        print(f"\nQuestion: {data['question']}")
    else:
        print("\n✅ Toutes les informations ont été collectées !")
        print(f"Profil: {data['profile']}")
        break
```

## 🎯 Logique des questions

L'ordre de priorité des questions est défini dans `question_logic.py` :

1. Nom
2. Titre professionnel
3. Pitch
4. Compétences
5. Projets
6. Liens

Le chatbot pose **une seule question à la fois** et ne répète jamais une question déjà posée (sauf si l'information n'a pas été correctement extraite).

## 🔧 Personnalisation

### Modifier les questions

Éditer `B2/chat/question_logic.py` :

```python
QUESTIONS = {
    "nom": "Votre question personnalisée ici",
    ...
}
```

### Modifier les champs obligatoires

Éditer `B2/chat/portfolio_session.py` :

```python
REQUIRED_FIELDS = [
    "nom",
    "titre_professionnel",
    # Ajouter vos champs ici
]
```

### Améliorer l'extraction des réponses

Modifier la méthode `extract_answer()` dans `question_logic.py` pour mieux comprendre les réponses de l'utilisateur.

## ⚠️ Notes importantes

- Les données sont **automatiquement sauvegardées** après chaque réponse
- La session est **persistante** : vous pouvez reprendre une session plus tard
- Le chatbot **ne génère pas** le portfolio, il collecte seulement les données
- Une fois `is_complete = true`, le profil est prêt à être utilisé pour générer le portfolio
