import numpy as np
from sklearn.cluster import KMeans

# ----- 1️⃣ Liste de tous tes domaines -----
domains = [
    "Développement logiciel / Software engineering",
    "Développement web",
    "Réseaux informatiques",
    "Cybersécurité",
    "Cloud computing",
    "DevOps",
    "Architecture logicielle",
    "Intelligence artificielle & Data",
    "Analyse de données",
    "Intelligence artificielle & Machine learning",
    "Business Intelligence (BI)",
    "ERP & CRM",
    "Marketing digital",
    "Community management",
    "SEO / SEA",
    "Content marketing",
    "Branding & communication corporate",
    "Relations publiques (RP)",
    "Email marketing",
    "Growth marketing",
    "Comptabilité générale",
    "Audit & contrôle de gestion",
    "Finance d’entreprise",
    "Analyse financière",
    "Banque & gestion de portefeuille",
    "Fiscalité",
    "Trésorerie",
    "Assurance",
    "Vente terrain",
    "Vente en magasin / retail",
    "Business development",
    "Gestion grands comptes",
    "E-commerce",
    "Relation client",
    "Négociation commerciale",
    "Avant-vente / presales",
    "Logistique transport",
    "Maintenance automobile",
    "Gestion flotte véhicules",
    "Transport international",
    "Exploitation transport",
    "Mécanique automobile",
    "Diagnostic technique",
    "Réseaux télécom",
    "Support télécom",
    "Fibre optique",
    "Radio & mobile (4G/5G)",
    "VoIP & communications unifiées",
    "Infrastructure télécom",
    "Transaction immobilière",
    "Gestion locative",
    "Syndic",
    "Promotion immobilière",
    "Expertise immobilière",
    "Négociation immobilière",
    "Design graphique",
    "UI / UX design",
    "Motion design",
    "Montage vidéo",
    "Photographie",
    "Illustration",
    "Production média",
    "Direction artistique",
    "Gestion des stocks",
    "Planification & approvisionnement",
    "Transport & distribution",
    "Supply chain management",
    "Import / Export",
    "Gestion d’entrepôt",
    "Procurement / achats"
]

# ----- 2️⃣ Encodage simple (one-hot) -----
X = np.eye(len(domains))  # chaque domaine = vecteur unique

# ----- 3️⃣ Clustering K-Means -----
k = 10  # nombre de clusters (à ajuster selon ton intuition)
kmeans = KMeans(n_clusters=k, random_state=42)
labels = kmeans.fit_predict(X)

# ----- 4️⃣ Fonction pour récupérer domaines compatibles -----
def compatible_domains(candidate_domain):
    if candidate_domain not in domains:
        return []
    cluster = labels[domains.index(candidate_domain)]
    # tous les domaines dans le même cluster
    compatible = [d for d, l in zip(domains, labels) if l == cluster]
    # score approximatif = 1 / nombre de domaines dans cluster
    score = round(1 / len(compatible), 2)
    return [(d, score) for d in compatible]

# ----- 5️⃣ Exemple -----
candidate = "Analyse de données"
results = compatible_domains(candidate)

print(f"Domaines compatibles pour '{candidate}':\n")
for domain, score in results:
    print(f"{domain}  (score ~ {score})")