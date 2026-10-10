"""
SNOMED CT Lookup Service.
Maps clinical findings, symptoms, body sites, and substances to standard SNOMED CT concepts.
"""
import logging
from ..models import TerminologyConcept

logger = logging.getLogger(__name__)

SNOMED_STANDARD_CATALOG = [
    {"code": "29857009", "display": "Chest pain", "description": "Pain in thoracic cavity structure", "category": "finding"},
    {"code": "49727002", "display": "Cough", "description": "Respiratory cough reflex symptom", "category": "finding"},
    {"code": "386661006", "display": "Fever", "description": "Elevated core body temperature", "category": "finding"},
    {"code": "267036007", "display": "Dyspnea / Shortness of breath", "description": "Labored or difficult respiration", "category": "finding"},
    {"code": "21522000", "display": "Abdominal pain", "description": "Abdominal sensory pain finding", "category": "finding"},
    {"code": "25064002", "display": "Headache", "description": "Cephalea finding", "category": "finding"},
    {"code": "57676002", "display": "Joint pain", "description": "Arthralgia finding", "category": "finding"},
    {"code": "422587007", "display": "Nausea", "description": "Unpleasant sensation of urge to vomit", "category": "finding"},
    {"code": "62315008", "display": "Diarrhea", "description": "Loose stool consistency symptom", "category": "finding"},
    {"code": "14760008", "display": "Constipation", "description": "Decreased bowel motility finding", "category": "finding"},
    {"code": "38341003", "display": "Hypertension", "description": "High arterial blood pressure disorder", "category": "finding"},
    {"code": "44054006", "display": "Type 2 diabetes", "description": "Non-insulin dependent diabetes mellitus", "category": "finding"},
    {"code": "195967001", "display": "Asthma", "description": "Extrinsic or intrinsic asthma disorder", "category": "finding"},
    # Medications
    {"code": "387517004", "display": "Paracetamol", "description": "Acetaminophen analgesic/antipyretic", "category": "medication"},
    {"code": "387458008", "display": "Amoxicillin", "description": "Penicillin antibiotic substance", "category": "medication"},
    {"code": "372567009", "display": "Metformin", "description": "Biguanide antihyperglycemic substance", "category": "medication"},
    {"code": "372658004", "display": "Amlodipine", "description": "Dihydropyridine calcium channel blocker", "category": "medication"},
]

def seed_snomed_catalog():
    try:
        for item in SNOMED_STANDARD_CATALOG:
            TerminologyConcept.objects.get_or_create(
                code=item["code"],
                system="snomed_ct",
                defaults={
                    "display": item["display"],
                    "description": item["description"],
                    "category": item["category"],
                }
            )
    except Exception as e:
        logger.debug(f"SNOMED catalog seeding deferred (database not ready): {e}")

class SNOMEDService:
    def __init__(self):
        seed_snomed_catalog()

    def search(self, query: str, limit: int = 5):
        if not query:
            return []
        q = query.lower().strip()
        matches = []
        concepts = TerminologyConcept.objects.filter(system="snomed_ct")
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
        results = self.search(text, limit=1)
        if results and results[0]["score"] >= 0.5:
            return results[0]
        return None
