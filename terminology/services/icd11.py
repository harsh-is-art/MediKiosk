"""
WHO ICD-11 Official API Client & Terminology Resolver.

Supports:
1. Live WHO ICD-11 API (OAuth2 client credentials against https://icd.who.int/icdapi).
2. Automatic OAuth2 token caching with expiration tracking.
3. Fallback to pre-seeded local ICD-11 canonical database when offline or if credentials are unset.
"""
import os
import time
import logging
import requests
from ..models import TerminologyConcept

logger = logging.getLogger(__name__)

# Standard canonical ICD-11 curated reference subset for common primary OPD symptoms
ICD11_STANDARD_CATALOG = [
    {"code": "MD11", "display": "Chest pain", "description": "Pain or discomfort in the chest region", "category": "symptom"},
    {"code": "MD80", "display": "Cough", "description": "Sudden, repetitive, spasmodic contraction of the thoracic cavity", "category": "symptom"},
    {"code": "MG26", "display": "Fever", "description": "Elevation of body temperature above normal range (pyrexia)", "category": "symptom"},
    {"code": "MD90", "display": "Shortness of breath / Dyspnoea", "description": "Subjective feeling of breathing discomfort", "category": "symptom"},
    {"code": "MD30", "display": "Abdominal pain", "description": "Pain localized in the abdominal cavity", "category": "symptom"},
    {"code": "MB23", "display": "Headache", "description": "Pain located in head, scalp, or neck", "category": "symptom"},
    {"code": "ME05", "display": "Nausea and vomiting", "description": "Gastric discomfort with sensation of emesis", "category": "symptom"},
    {"code": "ME01", "display": "Diarrhoea", "description": "Frequent and liquid bowel movements", "category": "symptom"},
    {"code": "ME03", "display": "Constipation", "description": "Infrequent or difficult bowel movements", "category": "symptom"},
    {"code": "FA00", "display": "Osteoarthritis", "description": "Degenerative joint disease", "category": "diagnosis"},
    {"code": "BA00", "display": "Hypertension (Essential)", "description": "Persistently elevated systemic arterial blood pressure", "category": "diagnosis"},
    {"code": "5A11", "display": "Type 2 diabetes mellitus", "description": "Metabolic disorder characterized by high blood sugar", "category": "diagnosis"},
    {"code": "CA23", "display": "Asthma", "description": "Chronic inflammatory disease of the airways", "category": "diagnosis"},
    {"code": "1B10", "display": "Tuberculosis", "description": "Mycobacterial pulmonary or extrapulmonary infection", "category": "diagnosis"},
    {"code": "FB56", "display": "Pain in joint / Arthralgia", "description": "Discomfort or pain in one or more joints", "category": "symptom"},
]

def seed_icd11_catalog():
    """Ensure standard ICD-11 concepts exist in the database."""
    try:
        for item in ICD11_STANDARD_CATALOG:
            TerminologyConcept.objects.get_or_create(
                code=item["code"],
                system="icd11",
                defaults={
                    "display": item["display"],
                    "description": item["description"],
                    "category": item["category"],
                }
            )
    except Exception as e:
        logger.debug(f"ICD11 catalog seeding deferred (database not ready): {e}")

class ICD11Service:
    TOKEN_ENDPOINT = "https://icdaccessmanagement.who.int/connect/token"
    API_SEARCH_ENDPOINT = "https://id.who.int/icd/release/11/2024-01/mms/search"

    def __init__(self):
        self.client_id = os.getenv("WHO_ICD_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("WHO_ICD_CLIENT_SECRET", "").strip()
        self.access_token = None
        self.token_expiry = 0
        seed_icd11_catalog()

    def _get_token(self):
        """Fetches or refreshes OAuth2 token from WHO Access Management."""
        if not self.client_id or not self.client_secret:
            return None

        now = time.time()
        if self.access_token and now < (self.token_expiry - 60):
            return self.access_token

        try:
            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'icdapi_access',
                'grant_type': 'client_credentials'
            }
            res = requests.post(self.TOKEN_ENDPOINT, data=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                self.access_token = data.get('access_token')
                expires_in = data.get('expires_in', 3600)
                self.token_expiry = now + expires_in
                return self.access_token
            else:
                logger.warning(f"WHO ICD-11 token request failed: {res.status_code} {res.text}")
        except Exception as e:
            logger.warning(f"WHO ICD-11 token request exception: {e}")

        return None

    def search_online(self, query: str, limit: int = 5):
        """Query official WHO ICD-11 API directly."""
        token = self._get_token()
        if not token:
            return []

        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
                'API-Version': 'v2',
                'Accept-Language': 'en'
            }
            params = {'q': query}
            res = requests.get(self.API_SEARCH_ENDPOINT, headers=headers, params=params, timeout=8)
            if res.status_code == 200:
                data = res.json()
                destinations = data.get('destinationEntities', [])
                results = []
                for entity in destinations[:limit]:
                    code = entity.get('theCode') or entity.get('stemId', '').split('/')[-1]
                    title = entity.get('title', '')
                    if code and title:
                        # Persist concept in database cache
                        concept, _ = TerminologyConcept.objects.get_or_create(
                            code=code,
                            system='icd11',
                            defaults={
                                'display': title,
                                'description': entity.get('definition', ''),
                                'category': 'symptom' if 'symptom' in title.lower() else 'finding'
                            }
                        )
                        score = entity.get('score', 0.85)
                        results.append({'score': score, 'concept': concept})
                return results
        except Exception as e:
            logger.warning(f"WHO ICD-11 API search error: {e}")

        return []

    def search(self, query: str, limit: int = 5):
        """Searches via online WHO API if configured, otherwise uses local database catalog."""
        if not query:
            return []

        # If WHO credentials provided, try online search first
        if self.client_id and self.client_secret:
            online_results = self.search_online(query, limit)
            if online_results:
                return online_results

        # Local search fallback
        q = query.lower().strip()
        matches = []
        concepts = TerminologyConcept.objects.filter(system="icd11")
        for c in concepts:
            score = 0.0
            if q in c.display.lower():
                score = 0.95 if q == c.display.lower() else 0.85
            elif q in c.description.lower():
                score = 0.70
            elif any(token in c.display.lower() for token in q.split()):
                score = 0.60
            if score > 0:
                matches.append((score, c))
        matches.sort(key=lambda x: x[0], reverse=True)
        return [{"score": s, "concept": c} for s, c in matches[:limit]]

    def resolve_concept(self, text: str):
        """Find the best match or None."""
        results = self.search(text, limit=1)
        if results and results[0]["score"] >= 0.5:
            return results[0]
        return None
