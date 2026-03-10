# Guide d'utilisation - Sauvegarde des Réponses Agent 3

Ce guide explique comment utiliser le système de sauvegarde des réponses, liens et images pour l'Agent 3.

## 📋 Vue d'ensemble

Le système permet de :
1. **Sauvegarder les réponses** aux questions générées par Gemini
2. **Extraire automatiquement les liens** (GitHub, démo, etc.) depuis les réponses
3. **Télécharger et sauvegarder les images** dans MinIO
4. **Structurer les données** dans la table `candidate_projects`

## 🔌 Endpoints disponibles

### 1. Sauvegarder les réponses

**POST** `/agent3/<candidate_uuid>/save-responses`

Sauvegarde les réponses, extrait les liens, télécharge les images et met à jour la base de données.

**Body (JSON)** :
```json
{
  "db_candidate_id": 1,
  "project_name": "Mon Projet",
  "answers": {
    "q1": "Description du projet...",
    "q2": "https://github.com/user/project",
    "q3": "https://mon-projet.netlify.app",
    "q4": "https://example.com/screenshot.png"
  },
  "questions": [
    {"id": "q1", "text": "Question 1"},
    {"id": "q2", "text": "Question 2"},
    ...
  ]
}
```

**Réponse** :
```json
{
  "success": true,
  "candidate_uuid": "...",
  "db_candidate_id": 1,
  "project_id": 123,
  "project_name": "Mon Projet",
  "message": "Réponses sauvegardées avec succès pour le projet 'Mon Projet'"
}
```

### 2. Upload d'image direct

**POST** `/agent3/<candidate_uuid>/upload-image`

Upload une image directement (pas depuis une URL) pour un projet.

**Form Data** :
- `db_candidate_id`: int (obligatoire)
- `project_name`: str (obligatoire)
- `image`: file (obligatoire) - Fichier image

**Réponse** :
```json
{
  "success": true,
  "minio_url": "http://localhost:9000/tap-files/candidates/1/projects/Mon_Projet/uploaded_image.jpg",
  "object_name": "candidates/1/projects/Mon_Projet/uploaded_image.jpg",
  "message": "Image uploadée avec succès"
}
```

## 🔍 Extraction automatique

Le système extrait automatiquement :

### Liens GitHub
- Détecte les URLs contenant `github.com`
- Prend le premier lien trouvé comme `github_url` principal

### Liens de démo
- Détecte les URLs de plateformes de déploiement :
  - `netlify.app`
  - `vercel.app`
  - `herokuapp.com`
  - `github.io`
  - `surge.sh`
  - `firebaseapp.com`
  - `appspot.com`
  - `railway.app`

### Images
- Détecte les URLs d'images (extensions : `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.bmp`)
- Détecte aussi les services d'hébergement d'images (`imgur.com`, `cloudinary.com`)
- **Télécharge automatiquement** les images et les sauvegarde dans MinIO
- Les URLs MinIO sont stockées dans `image_urls` (JSON array)

### Technologies
- Détecte automatiquement les technologies mentionnées dans les réponses
- Technologies détectées : Python, JavaScript, React, Node, Django, Flask, Angular, Vue, MySQL, PostgreSQL, MongoDB, Redis, Docker, Kubernetes, AWS, Azure, GCP, Git, HTML, CSS, TypeScript, Java, Spring, PHP, Laravel

## 💾 Structure de données sauvegardée

Les données sont sauvegardées dans la table `candidate_projects` :

```sql
- project_name: Nom du projet
- github_url: Premier lien GitHub trouvé
- demo_url: Premier lien de démo trouvé
- image_urls: JSON array des URLs MinIO des images
- additional_links: JSON array des autres liens (non GitHub, non démo)
- detailed_description: Description combinée de toutes les réponses
- technologies: JSON array des technologies détectées
- additional_info: JSON object avec toutes les réponses individuelles {question_id: answer}
- status: 'completed' après sauvegarde
```

## 📝 Exemple d'utilisation complète

### Étape 1 : Générer les questions

```bash
curl -X POST http://localhost:5002/agent3/test-uuid/process \
  -H "Content-Type: application/json" \
  -d @test_agent3_payload.json
```

### Étape 2 : Collecter les réponses

L'utilisateur répond aux questions via le frontend ou l'API.

### Étape 3 : Sauvegarder les réponses

```bash
curl -X POST http://localhost:5002/agent3/test-uuid/save-responses \
  -H "Content-Type: application/json" \
  -d '{
    "db_candidate_id": 1,
    "project_name": "Application E-commerce",
    "answers": {
      "q1": "Application de vente en ligne avec React et Node.js",
      "q2": "https://github.com/user/ecommerce-app",
      "q3": "https://ecommerce-app.netlify.app",
      "q4": "https://imgur.com/abc123.png",
      "q5": "J'ai utilisé React, Node.js, MongoDB et Docker"
    },
    "questions": [
      {"id": "q1", "text": "Description du projet"},
      {"id": "q2", "text": "Lien GitHub"},
      {"id": "q3", "text": "Lien de démo"},
      {"id": "q4", "text": "Capture d'écran"},
      {"id": "q5", "text": "Technologies utilisées"}
    ]
  }'
```

Le système va :
1. ✅ Extraire `https://github.com/user/ecommerce-app` → `github_url`
2. ✅ Extraire `https://ecommerce-app.netlify.app` → `demo_url`
3. ✅ Télécharger `https://imgur.com/abc123.png` → MinIO → `image_urls`
4. ✅ Détecter "React", "Node.js", "MongoDB", "Docker" → `technologies`
5. ✅ Sauvegarder toutes les réponses dans `additional_info`
6. ✅ Créer/mettre à jour le projet dans `candidate_projects`

### Étape 4 : Upload d'image direct (optionnel)

Si l'utilisateur veut uploader une image directement :

```bash
curl -X POST http://localhost:5002/agent3/test-uuid/upload-image \
  -F "db_candidate_id=1" \
  -F "project_name=Application E-commerce" \
  -F "image=@screenshot.png"
```

## 🔧 Fonctions utilitaires

### `extract_urls(text)`
Extrait toutes les URLs d'un texte.

### `extract_github_urls(text)`
Extrait spécifiquement les URLs GitHub.

### `extract_demo_urls(text)`
Extrait les URLs de démo.

### `extract_image_urls(text)`
Extrait les URLs d'images.

### `download_image_from_url(image_url, candidate_id, project_name, image_index)`
Télécharge une image depuis une URL et la sauvegarde dans MinIO.

### `parse_answer_for_project_info(answer)`
Parse une réponse pour extraire les informations structurées.

### `save_project_responses(candidate_id, project_name, answers, questions)`
Sauvegarde les réponses dans la base de données et télécharge les images.

## ⚠️ Notes importantes

1. **Images** : Les images sont automatiquement téléchargées depuis les URLs et sauvegardées dans MinIO. Les URLs originales sont remplacées par les URLs MinIO.

2. **Duplication** : Si un projet avec le même nom existe déjà, il sera mis à jour au lieu d'être créé.

3. **Technologies** : La détection des technologies est basique (recherche de mots-clés). Pour une détection plus précise, utilisez un parsing plus sophistiqué.

4. **Timeout** : Le téléchargement d'images a un timeout de 30 secondes. Les images trop grandes ou inaccessibles seront ignorées.

5. **MinIO** : Assurez-vous que MinIO est configuré et accessible avant d'utiliser ces endpoints.

## 🧪 Test

Pour tester la sauvegarde :

```bash
python test_agent3_simple.py
# Puis utilisez les réponses générées pour tester /save-responses
```
