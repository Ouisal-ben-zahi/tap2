# Génération Automatique de Portfolios HTML

Ce module permet de générer automatiquement des portfolios HTML à partir des données d'un candidat.

## 📋 Vue d'ensemble

Le système génère deux versions de portfolio :
1. **Version ONE-PAGE** : Portfolio fullscreen sur une seule slide (1920x1080px), sans scroll
2. **Version LONG** : Portfolio scrollable classique avec plusieurs sections

## 🏗️ Architecture

### Fichiers principaux

- `generate_portfolio_html.py` : Agent de génération HTML
- `agent_portfolio.py` : Agent de génération de contenu JSON (existant)
- `portfolio_1page_template.html` : Template Jinja2 pour la version one-page
- `portfolio_template.html` : Template Jinja2 pour la version longue (existant)

### Flux de génération

```
Données candidat (DB)
    ↓
agent_portfolio.generate_portfolio_content()
    ↓
JSON structuré (talent_graph)
    ↓
transform_portfolio_data_for_template()
    ↓
Données formatées pour template
    ↓
generate_portfolio_html()
    ↓
HTML rendu avec Jinja2
    ↓
Conversion URLs MinIO → Proxy
    ↓
HTML final prêt à l'affichage
```

## 🔌 API Endpoints

### 1. Générer et afficher le portfolio HTML

**GET** `/portfolio/<candidate_uuid>/html/<version>`

**Query params:**
- `db_candidate_id` (obligatoire) : ID du candidat en base de données

**Path params:**
- `version` : `"one-page"` ou `"long"`

**Exemple:**
```bash
GET /portfolio/abc123/html/one-page?db_candidate_id=42
```

**Returns:**
- HTML content (Content-Type: text/html)

### 2. Générer et sauvegarder le portfolio HTML

**POST** `/portfolio/<candidate_uuid>/generate-html`

**Body (JSON):**
```json
{
  "db_candidate_id": 42,
  "version": "one-page",  // ou "long"
  "save_to_minio": true   // optionnel, défaut: true
}
```

**Returns:**
```json
{
  "success": true,
  "version": "one-page",
  "html_content": "<!DOCTYPE html>...",
  "minio_url": "http://minio/.../portfolio_abc123_one-page.html",
  "message": "Portfolio HTML généré avec succès (version: one-page)"
}
```

## 💻 Utilisation en Python

### Génération simple

```python
from B2.generate_portfolio_html import generate_portfolio_html

success, html_content, error = generate_portfolio_html(
    candidate_id=42,
    version="one-page",
    candidate_image_url="http://...",
    candidate_email="candidate@example.com",
    candidate_phone="+33 6 12 34 56 78",
    candidate_job_title="Développeur Full-Stack",
    candidate_years_experience=5
)

if success:
    # Sauvegarder le HTML
    with open("portfolio.html", "w", encoding="utf-8") as f:
        f.write(html_content)
else:
    print(f"Erreur: {error}")
```

### Génération et sauvegarde dans MinIO

```python
from B2.generate_portfolio_html import generate_and_save_portfolio_html

success, html_content, minio_url, error = generate_and_save_portfolio_html(
    candidate_id=42,
    candidate_uuid="abc123",
    version="one-page",
    candidate_image_url="http://...",
    save_to_minio=True
)

if success:
    print(f"Portfolio généré: {minio_url}")
    print(f"HTML disponible: {len(html_content)} caractères")
```

## 📝 Template Variables

Les templates Jinja2 utilisent les variables suivantes :

### `candidate`
- `first_name` : Prénom
- `last_name` : Nom
- `job_title` : Titre du poste
- `role` : Rôle professionnel
- `executive_summary` : Résumé exécutif
- `about_text` : Texte "À propos"
- `years_experience` : Années d'expérience
- `profile_image_url` : URL de l'image de profil
- `email` : Email
- `phone` : Téléphone
- `linkedin_url` : URL LinkedIn
- `github_url` : URL GitHub
- `technical_skills` : Liste des compétences techniques
- `soft_skills` : Liste des compétences soft
- `projects` : Liste des projets
- `experiences` : Liste des expériences

### `portfolio`
- `year` : Année du portfolio

### Structure des projets

```python
{
    "title": "Nom du projet",
    "description": "Description du projet",
    "solution": "Solution apportée",
    "main_image_url": "http://...",
    "preview_images": [{"url": "http://..."}],
    "stack": ["React", "Node.js"],
    "links": [{"url": "http://...", "label": "Voir le projet"}]
}
```

### Structure des expériences

```python
{
    "role": "Développeur Full-Stack",
    "company": "Entreprise XYZ",
    "period": "2020 - 2023",
    "date_start": "2020-01",
    "date_end": "2023-12",
    "description": "Description de l'expérience",
    "impact": "Impact de l'expérience"
}
```

## 🎨 Personnalisation du Template

### Modifier le template one-page

Éditer `frontend/src/portfolio html/portfolio_1page_template.html`

### Ajouter des sections

1. Ajouter la section dans le template HTML
2. Ajouter les données correspondantes dans `transform_portfolio_data_for_template()`
3. Mettre à jour le prompt de l'agent IA si nécessaire

## 🔧 Configuration

### URLs Proxy

Les URLs MinIO sont automatiquement converties en URLs proxy Flask pour l'affichage dans le navigateur.

Format URL proxy : `http://flask-server/minio-proxy/candidates/{candidate_id}/...`

### Taille de référence

- Version one-page : 1920x1080px (Full HD)
- Le contenu est automatiquement mis à l'échelle pour s'adapter à l'écran

## 🐛 Dépannage

### Template introuvable

Vérifier que le template existe dans :
- `frontend/src/portfolio html/portfolio_1page_template.html`
- `frontend/src/portfolio html/portfolio_template.html`

### Erreur de rendu Jinja2

Vérifier que toutes les variables utilisées dans le template sont présentes dans `template_data`.

### Images non affichées

Vérifier que les URLs MinIO sont correctement converties en URLs proxy.

## 📚 Références

- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Agent Portfolio](./agent_portfolio.py)
- [Template Engine](../app.py#L3547)
