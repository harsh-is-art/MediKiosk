"""
Medical entity extraction — provider-independent post-processing.
Extracts medicines, lab values, and diagnoses from raw OCR text.
"""


# Python Standard Library Imports

import re
import logging


# Logger Confi.

logger = logging.getLogger(__name__)


# Medical Entity Extraction

def extract_medical_entities(raw_text: str) -> dict:
    """
    Extract structured medical entities from raw OCR text.
    Uses regex patterns and fuzzy matching.

    Returns:
        dict with keys: medicines, lab_values, diagnoses, dosages
    """

    # Validate OCR Input

    if not raw_text:
        return {'medicines': [], 'lab_values': [], 'diagnoses': [], 'dosages': []}

    # Initialize Medical Entity Containers

    entities = {
        'medicines': [],
        'lab_values': [],
        'diagnoses': [],
        'dosages': [],
    }

    # Medicine Recognition Patterns

    medicine_patterns = [
        r'\b(Tab|Cap|Syp|Inj|Oint)\b\.?\s*([A-Za-z]+(?:\s[A-Za-z]+)?)',
        r'\b([A-Z][a-z]+(?:cillin|mycin|azole|prazole|sartan|olol|pril|statin|formin))\b',
    ]

    # Extract Medicine Names

    for pattern in medicine_patterns:
        matches = re.findall(pattern, raw_text, re.IGNORECASE)

        for match in matches:
            name = match if isinstance(match, str) else ' '.join(match).strip()

            if name and name not in entities['medicines']:
                entities['medicines'].append(name)

    # Dosage Recognition Patterns

    # Common dosage formats:
    # Examples: "500mg", "250 mg", "1-0-1", "BD", "TDS"

    dosage_patterns = [
        r'\b(\d+\s*(?:mg|mcg|ml|g|IU))\b',
        r'\b(\d+-\d+-\d+)\b',
        r'\b(OD|BD|TDS|QID|SOS|PRN|HS)\b',
    ]

    # Extract Dosage Information

    for pattern in dosage_patterns:
        matches = re.findall(pattern, raw_text, re.IGNORECASE)
        entities['dosages'].extend(matches)

    # Laboratory Value Recognition Patterns

    # Common laboratory formats:
    # Examples: "Hb 12.5", "BP 120/80", "Sugar 180"

    lab_patterns = [
        (r'\b(?:Hb|Haemoglobin|Hemoglobin)\s*:?\s*(\d+\.?\d*)', 'Hemoglobin'),
        (r'\b(?:BP|Blood Pressure)\s*:?\s*(\d+/\d+)', 'Blood Pressure'),
        (r'\b(?:Sugar|Glucose|BSL|RBS)\s*:?\s*(\d+\.?\d*)', 'Blood Sugar'),
        (r'\b(?:Creatinine)\s*:?\s*(\d+\.?\d*)', 'Creatinine'),
        (r'\b(?:WBC|TLC)\s*:?\s*(\d+\.?\d*)', 'WBC Count'),
    ]

    # Extract Laboratory Values

    for pattern, label in lab_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)

        if match:
            entities['lab_values'].append({
                'name': label,
                'value': match.group(1),
            })

    # Diagnosis Keyword Definitions

    diagnosis_keywords = [
        'diabetes', 'hypertension', 'asthma', 'COPD', 'tuberculosis', 'TB',
        'thyroid', 'anemia', 'malaria', 'dengue', 'typhoid', 'pneumonia',
        'UTI', 'gastritis', 'arthritis',
    ]

    # Diagnosis Detection

    text_lower = raw_text.lower()

    for diag in diagnosis_keywords:
        if diag.lower() in text_lower:
            entities['diagnoses'].append(diag)

    # Optional Medicine Database Fuzzy Matching

    try:
        from medicines.models import Medicine
        from medicines.utils import fuzzy_match_medicine

        # Match Extracted Medicines Against Database

        for med_name in entities['medicines']:
            match = fuzzy_match_medicine(med_name)

            if match:
                entities['medicines'] = [
                    match.brand_name if m == med_name else m
                    for m in entities['medicines']
                ]

    except Exception:
        # Fuzzy matching is optional
        pass

    # Return Extracted Medical Entities

    return entities