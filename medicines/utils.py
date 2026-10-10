# Module Imports & Logging Setup

import re
import logging
from fuzzywuzzy import fuzz, process

logger = logging.getLogger(__name__)


# Fuzzy Medicine Matching Function

def fuzzy_match_medicine(name, threshold=75):
    """
    Find the closest matching medicine in the database matching brand or generic name.
    Returns a dict with medicine object, actual score, and match_type, or None if match is ambiguous/insufficient.
    """
    if not name or not isinstance(name, str):
        return None

    cleaned_name = name.strip()
    if len(cleaned_name) < 3:
        return None

    from .models import Medicine

    medicines = Medicine.objects.all()
    if not medicines.exists():
        return None

    choices = {}
    for m in medicines:
        choices[f"b_{m.id}"] = m.brand_name
        if m.generic_name:
            choices[f"g_{m.id}"] = m.generic_name

    if not choices:
        return None

    matches = process.extract(cleaned_name, choices, scorer=fuzz.token_sort_ratio, limit=3)
    if not matches:
        return None

    top_match = matches[0]
    top_score = top_match[1]

    # Ambiguity check: if top 2 matches have nearly identical top scores (within 2 points)
    if len(matches) > 1 and (top_score - matches[1][1]) < 2 and top_score < 95:
        logger.info(f"Ambiguous medicine match for '{name}': {matches[0]} vs {matches[1]}")
        return {
            'medicine': None,
            'score': top_score,
            'match_type': 'ambiguous',
        }

    if top_score >= threshold:
        key = top_match[2]
        med_id = int(key.split('_')[1])
        med_obj = Medicine.objects.get(id=med_id)

        match_type = 'exact' if top_score >= 98 else ('strong_fuzzy' if top_score >= 85 else 'weak_fuzzy')
        return {
            'medicine': med_obj,
            'score': top_score,
            'match_type': match_type,
        }

    return None


# OCR Text Medicine Extraction Function

def correct_ocr_medicines(raw_text):
    """
    Extract and correct medicine names from OCR output.

    Returns list of dicts with original, corrected, score, and match_type.
    """
    if not raw_text or not isinstance(raw_text, str):
        return []

    # Common medicine prefixes in prescriptions
    patterns = [
        r'(?:Tab|Cap|Syp|Inj|Oint)\.?\s+([A-Za-z0-9\-]+)',
    ]

    results = []
    for pattern in patterns:
        matches = re.findall(pattern, raw_text, re.IGNORECASE)
        for match in matches:
            match_str = match if isinstance(match, str) else ' '.join(match).strip()
            match_info = fuzzy_match_medicine(match_str, threshold=75)
            if match_info and match_info.get('medicine'):
                med = match_info['medicine']
                results.append({
                    'original': match_str,
                    'corrected': med.brand_name,
                    'score': match_info['score'],
                    'match_type': match_info['match_type'],
                })
            else:
                results.append({
                    'original': match_str,
                    'corrected': match_str,
                    'score': match_info['score'] if match_info else 0,
                    'match_type': match_info['match_type'] if match_info else 'no_match',
                })

    return results



