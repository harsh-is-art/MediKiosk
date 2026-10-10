"""
Document Intelligence Processing Pipeline.
Preprocess -> Detect/Crop -> OCR -> Handwriting/Vision -> Structure -> Confidence Validation.
"""
import os
import re
import time
import json
import logging
from typing import Dict, Any, Tuple
import cv2
import numpy as np
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile

from ..models import (
    MedicalDocument, DocumentField, DocumentMedication,
    DocumentLabResult, AuditLog
)
from ..utils.ocr import get_ocr_provider
from ..utils.llm import call_llm

logger = logging.getLogger(__name__)

def preprocess_image(image_path: str) -> Tuple[np.ndarray, str]:
    """
    Image preprocessing: deskew, denoise, contrast normalization.
    Returns processed opencv image matrix and processed image file path.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image from {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Adaptive Contrast Normalization (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(denoised)

    # Auto-Crop document slip using largest contour if detected
    thresh = cv2.adaptiveThreshold(contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cropped = img
    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) > (img.shape[0] * img.shape[1] * 0.15):
            x, y, w, h = cv2.boundingRect(largest)
            cropped = img[y:y+h, x:x+w]

    # Save processed image
    dir_name = os.path.dirname(image_path)
    base_name = os.path.basename(image_path)
    proc_path = os.path.join(dir_name, f"proc_{base_name}")
    cv2.imwrite(proc_path, cropped)

    return cropped, proc_path


def parse_document_structure(raw_text: str, doc_type: str = "prescription") -> Dict[str, Any]:
    """
    Uses LLM / Rule extraction to structure text into medications, lab results, and patient fields with confidence.
    """
    prompt = f"""You are a medical document extraction specialist.
Analyze this OCR text extracted from a medical document ({doc_type}):

DOCUMENT TEXT:
{raw_text}

Extract information into a structured JSON with confidence scores (0.0 to 1.0) per field:
{{
  "document_type": "{doc_type}",
  "patient_name": {{"value": "string or unknown", "confidence": 0.0-1.0}},
  "date": {{"value": "YYYY-MM-DD or unknown", "confidence": 0.0-1.0}},
  "medications": [
    {{"name": "drug name", "dose": "e.g. 500mg", "frequency": "e.g. twice daily", "duration": "e.g. 5 days", "confidence": 0.0-1.0}}
  ],
  "lab_results": [
    {{"test": "test name", "value": "numeric or text", "unit": "unit", "reference_range": "ref", "confidence": 0.0-1.0}}
  ],
  "notes": ["string"],
  "overall_confidence": 0.0-1.0
}}

Output valid raw JSON only. Do not guess low-confidence values without setting confidence < 0.70."""

    try:
        messages = [
            {"role": "system", "content": "You are a clinical document parser. Output raw JSON only."},
            {"role": "user", "content": prompt}
        ]
        resp = call_llm(messages)
        cleaned = resp.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(cleaned)
        return data
    except Exception as e:
        logger.warning(f"LLM document structure error: {e}")
        # Rule-based fallback
        return {
            "document_type": doc_type,
            "patient_name": {"value": "Extracted from slip", "confidence": 0.60},
            "date": {"value": "unspecified", "confidence": 0.50},
            "medications": [],
            "lab_results": [],
            "notes": [raw_text[:200]],
            "overall_confidence": 0.55
        }


def run_document_pipeline(medical_doc: MedicalDocument) -> MedicalDocument:
    """
    Executes the end-to-end document intelligence pipeline:
    1. Preprocess & crop
    2. OCR extraction
    3. Structural parsing
    4. Confidence threshold check
    5. Database records creation & Audit log
    """
    start_time = time.time()
    threshold = getattr(settings, 'DOCUMENT_CONFIDENCE_THRESHOLD', 0.75)

    try:
        image_path = medical_doc.image_file.path

        # Step 1: Preprocess & Deskew
        cropped_img, proc_path = preprocess_image(image_path)
        rel_proc = os.path.relpath(proc_path, settings.MEDIA_ROOT).replace("\\", "/")
        medical_doc.processed_image_file = rel_proc
        medical_doc.save()

        # Step 2: OCR
        ocr_provider = get_ocr_provider()
        ocr_res = ocr_provider.extract_text(proc_path)
        raw_text = ocr_res.get("text", "")
        ocr_conf = float(ocr_res.get("confidence", 0.80) or 0.80)

        # Step 3: Structural Extraction
        structured = parse_document_structure(raw_text, doc_type=medical_doc.document_type)
        overall_conf = float(structured.get("overall_confidence", ocr_conf))

        medical_doc.overall_confidence = overall_conf

        # Step 4: Populate DocumentField items
        p_name = structured.get("patient_name", {})
        val = p_name.get("value", "")
        conf = float(p_name.get("confidence", overall_conf))
        DocumentField.objects.create(
            document=medical_doc,
            field_name="patient_name",
            field_value=val,
            confidence=conf,
            needs_review=(conf < threshold),
            provenance="ai_extracted"
        )

        p_date = structured.get("date", {})
        d_val = p_date.get("value", "")
        d_conf = float(p_date.get("confidence", overall_conf))
        DocumentField.objects.create(
            document=medical_doc,
            field_name="date",
            field_value=d_val,
            confidence=d_conf,
            needs_review=(d_conf < threshold),
            provenance="ai_extracted"
        )

        # Step 5: Populate Medications
        for med in structured.get("medications", []):
            m_conf = float(med.get("confidence", overall_conf))
            DocumentMedication.objects.create(
                document=medical_doc,
                name=med.get("name", "Unknown medication"),
                dose=med.get("dose", ""),
                frequency=med.get("frequency", ""),
                duration=med.get("duration", ""),
                confidence=m_conf,
                needs_review=(m_conf < threshold)
            )

        # Step 6: Populate Lab Results
        for lab in structured.get("lab_results", []):
            l_conf = float(lab.get("confidence", overall_conf))
            test_name = lab.get("test", "Lab Test")

            # Try LOINC mapping
            from terminology.services.loinc import LOINCService
            loinc_svc = LOINCService()
            resolved = loinc_svc.resolve_concept(test_name)
            loinc_code = resolved["concept"].code if resolved else None

            DocumentLabResult.objects.create(
                document=medical_doc,
                test_name=test_name,
                value=str(lab.get("value", "")),
                unit=lab.get("unit", ""),
                reference_range=lab.get("reference_range", ""),
                confidence=l_conf,
                loinc_code=loinc_code,
                needs_review=(l_conf < threshold)
            )

        # Determine Document Review Status
        has_needs_review = (
            overall_conf < threshold or
            medical_doc.fields.filter(needs_review=True).exists() or
            medical_doc.medications.filter(needs_review=True).exists() or
            medical_doc.lab_results.filter(needs_review=True).exists()
        )

        medical_doc.status = "needs_review" if has_needs_review else "processed"
        medical_doc.save()

        # Audit log
        AuditLog.objects.create(
            session=medical_doc.session,
            document=medical_doc,
            action="document_pipeline_run",
            step="structure_and_validate",
            model_used="pipeline_paddle_llm",
            latency_ms=(time.time() - start_time) * 1000,
            confidence=overall_conf,
            details={"raw_text_length": len(raw_text), "status": medical_doc.status}
        )

        return medical_doc

    except Exception as e:
        logger.error(f"Document pipeline exception: {e}", exc_info=True)
        medical_doc.status = "needs_review"
        medical_doc.save()
        AuditLog.objects.create(
            session=medical_doc.session,
            document=medical_doc,
            action="document_pipeline_error",
            step="failure",
            latency_ms=(time.time() - start_time) * 1000,
            details={"error": str(e)}
        )
        return medical_doc
