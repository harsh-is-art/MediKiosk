"""
Clinical AI Extraction Service.
Validates LLM output against Pydantic schema, tags every item with provenance,
retries once on malformed output, and audits in ExtractionLog.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

from ..models import PatientSession, ExtractionLog
from ..utils.llm import call_llm

logger = logging.getLogger(__name__)

class HPIModel(BaseModel):
    onset: Optional[str] = "unspecified"
    duration: Optional[str] = "unspecified"
    location: Optional[str] = "unspecified"
    severity: Optional[int] = Field(default=5, ge=0, le=10)
    character: Optional[str] = "unspecified"
    progression: Optional[str] = "unspecified"
    associated_symptoms: List[str] = Field(default_factory=list)
    aggravating_factors: List[str] = Field(default_factory=list)
    relieving_factors: List[str] = Field(default_factory=list)

class ClinicalExtractionSchema(BaseModel):
    chief_complaint: str = Field(default="General consultation")
    hpi: HPIModel = Field(default_factory=HPIModel)
    past_medical_history: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    family_history: List[str] = Field(default_factory=list)
    social_history: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)


def tag_item_provenance(item: Any, default_prov: str = "ai_extracted") -> Any:
    """Attaches clinical provenance tag to data dictionaries or items."""
    if isinstance(item, dict):
        if 'provenance' not in item:
            item['provenance'] = default_prov
        return item
    elif isinstance(item, str):
        return {'text': item, 'provenance': default_prov}
    return item


def extract_clinical_json(transcript: str, session: Optional[PatientSession] = None) -> dict:
    """
    Extracts structured clinical information from a patient transcript.
    - Calls LLM
    - Validates against ClinicalExtractionSchema (Pydantic)
    - Retries once on malformed output
    - Tags every field with provenance = "ai_extracted"
    - Logs raw and parsed output to ExtractionLog
    """
    system_prompt = """You are a clinical NLP extractor for a hospital patient intake system.
Convert the provided patient dialogue into the exact JSON schema with these keys:
{
  "chief_complaint": "string",
  "hpi": {
    "onset": "string",
    "duration": "string",
    "location": "string",
    "severity": integer (0 to 10),
    "character": "string",
    "progression": "string",
    "associated_symptoms": ["string"],
    "aggravating_factors": ["string"],
    "relieving_factors": ["string"]
  },
  "past_medical_history": ["string"],
  "medications": ["string"],
  "allergies": ["string"],
  "family_history": ["string"],
  "social_history": ["string"],
  "missing_fields": ["string list of essential clinical fields not yet mentioned by patient, e.g. onset, duration, severity, allergies"]
}

Output valid JSON only. Do not invent diagnoses."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"TRANSCRIPT:\n{transcript}"}
    ]

    last_raw_response = ""
    last_error = ""

    for attempt in range(2):
        try:
            raw_response = call_llm(messages)
            last_raw_response = raw_response

            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            parsed_data = json.loads(cleaned)
            validated = ClinicalExtractionSchema(**parsed_data)
            validated_dict = validated.model_dump()

            # Attach provenance = "ai_extracted" to every element
            tagged_output = {
                "chief_complaint": {
                    "text": validated_dict["chief_complaint"],
                    "provenance": "ai_extracted"
                },
                "hpi": {
                    **validated_dict["hpi"],
                    "provenance": "ai_extracted",
                    "associated_symptoms": [
                        tag_item_provenance(s, "ai_extracted") for s in validated_dict["hpi"]["associated_symptoms"]
                    ]
                },
                "past_medical_history": [
                    tag_item_provenance(p, "ai_extracted") for p in validated_dict["past_medical_history"]
                ],
                "medications": [
                    tag_item_provenance(m, "ai_extracted") for m in validated_dict["medications"]
                ],
                "allergies": [
                    tag_item_provenance(a, "ai_extracted") for a in validated_dict["allergies"]
                ],
                "family_history": [
                    tag_item_provenance(f, "ai_extracted") for f in validated_dict["family_history"]
                ],
                "social_history": [
                    tag_item_provenance(s, "ai_extracted") for s in validated_dict["social_history"]
                ],
                "missing_fields": validated_dict["missing_fields"]
            }

            # Log to ExtractionLog
            ExtractionLog.objects.create(
                session=session,
                raw_transcript=transcript,
                raw_llm_response=raw_response,
                parsed_output=tagged_output,
                is_valid=True,
                retry_count=attempt
            )

            return tagged_output

        except (json.JSONDecodeError, ValidationError, Exception) as e:
            last_error = str(e)
            logger.warning(f"Clinical extraction attempt {attempt+1} failed: {e}")
            if attempt == 0:
                messages.append({"role": "assistant", "content": last_raw_response})
                messages.append({"role": "user", "content": "Your previous response was not valid JSON or failed schema validation. Please reply with ONLY raw, valid JSON."})

    # Fallback default object with provenance
    fallback_output = {
        "chief_complaint": {"text": "General intake", "provenance": "ai_extracted"},
        "hpi": {"onset": "unknown", "duration": "unknown", "location": "unspecified", "severity": 5, "associated_symptoms": [], "provenance": "ai_extracted"},
        "past_medical_history": [],
        "medications": [],
        "allergies": [],
        "family_history": [],
        "social_history": [],
        "missing_fields": ["onset", "duration", "severity", "allergies"]
    }

    ExtractionLog.objects.create(
        session=session,
        raw_transcript=transcript,
        raw_llm_response=last_raw_response,
        parsed_output=fallback_output,
        is_valid=False,
        validation_error=last_error,
        retry_count=1
    )

    return fallback_output
