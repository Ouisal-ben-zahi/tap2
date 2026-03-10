import requests
import logging

logger = logging.getLogger("ESCO_Connector")

class EscoConnector:
    """
    Connecteur pour l'API ESCO locale.
    Remplace les fichiers JSON statiques par des appels dynamiques.
    """
    def __init__(self, api_url="http://localhost:8080"):
        self.base_url = api_url.rstrip('/')
        self.session = requests.Session()

    def search_skill(self, term):
        """Recherche une compétence/techno par nom."""
        try:
            # On cherche dans les concepts, skills et occupations pour être large
            params = {
                'text': term,
                'type': 'skill',
                'language': 'en', # Ou 'fr' selon ta config ESCO locale
                'limit': 1
            }
            # Note: L'endpoint /search est souvent à la racine ou sous /v1/search
            resp = self.session.get(f"{self.base_url}/search", params=params, timeout=2)
            
            if resp.status_code == 200:
                results = resp.json().get('_embedded', {}).get('results', [])
                if results:
                    return results[0] # On retourne le meilleur match
        except Exception as e:
            logger.warning(f"ESCO API Error (Search '{term}'): {e}")
        return None

    def get_related_skills(self, uri):
        """
        Récupère des compétences 'narrower' (plus précises) pour simuler une Stack.
        Ex: Machine Learning -> Supervised Learning, Deep Learning...
        """
        try:
            # L'API ESCO permet de naviguer via l'URI de la ressource
            # On demande les relations "narrowerConcept"
            params = {'uri': uri, 'language': 'en'}
            resp = self.session.get(f"{self.base_url}/resource/related", params=params, timeout=2)
            
            stack = []
            if resp.status_code == 200:
                relations = resp.json().get('_embedded', {}).get('hasNarrowerConcept', [])
                # On en prend 3 au hasard pour l'exemple
                for rel in relations[:3]:
                    stack.append({
                        "technology_id": rel.get('uri', '').split('/')[-1],
                        "technology_name": rel.get('title', 'Unknown')
                    })
            return stack
        except Exception as e:
            # Ce n'est pas bloquant, on retourne une liste vide
            return []