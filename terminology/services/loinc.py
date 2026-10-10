"""
LOINC Lookup Service.
Maps laboratory observations, tests, and clinical measurements to LOINC codes.
"""
import logging
from ..models import TerminologyConcept

logger = logging.getLogger(__name__)

LOINC_STANDARD_CATALOG = [
    {"code": "2708-6", "display": "Oxygen saturation in Arterial blood by Pulse oximetry", "description": "SpO2 percentage", "category": "lab"},
    {"code": "8867-4", "display": "Heart rate", "description": "Cardiac pulse rate in beats per minute", "category": "lab"},
    {"code": "8480-6", "display": "Systolic blood pressure", "description": "Systolic arterial pressure in mmHg", "category": "lab"},
    {"code": "8462-4", "display": "Diastolic blood pressure", "description": "Diastolic arterial pressure in mmHg", "category": "lab"},
    {"code": "8310-5", "display": "Body temperature", "description": "Core body temperature in Celsius", "category": "lab"},
    {"code": "2345-7", "display": "Glucose [Mass/volume] in Blood", "description": "Random / fasting blood sugar", "category": "lab"},
    {"code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood", "description": "HbA1c percentage", "category": "lab"},
    {"code": "718-7", "display": "Hemoglobin [Mass/volume] in Blood", "description": "Total hemoglobin g/dL", "category": "lab"},
    {"code": "6690-2", "display": "Leukocytes [#/volume] in Blood", "description": "Total White Blood Cell Count (WBC)", "category": "lab"},
    {"code": "777-3", "display": "Platelets [#/volume] in Blood", "description": "Platelet count", "category": "lab"},
    {"code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma", "description": "Serum creatinine kidney function", "category": "lab"},
    {"code": "1751-7", "display": "Albumin [Mass/volume] in Serum or Plasma", "description": "Serum albumin liver/kidney test", "category": "lab"},
    {"code": "1975-2", "display": "Bilirubin.total [Mass/volume] in Serum or Plasma", "description": "Total bilirubin liver function", "category": "lab"},
]

def seed_loinc_catalog():
    try:
        for item in LOINC_STANDARD_CATALOG:
            TerminologyConcept.objects.get_or_create(
                code=item["code"],
                system="loinc",
                defaults={
                    "display": item["display"],
                    "description": item["description"],
                    "category": item["category"],
                }
            )
    except Exception as e:
        logger.debug(f"LOINC catalog seeding deferred (database not ready): {e}")

class LOINCService:
    def __init__(self):
        seed_loinc_catalog()

    def search(self, query: str, limit: int = 5):
        if not query:
            return []
        q = query.lower().strip()
        matches = []
        concepts = TerminologyConcept.objects.filter(system="loinc")
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
