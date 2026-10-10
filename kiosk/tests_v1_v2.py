import uuid
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from kiosk.models import (
    PatientSession, StructuredHistory, MedicalDocument, 
    DocumentField, DocumentLabResult, DocumentMedication, ExtractionLog
)
from sensors.models import VitalReading
from terminology.models import TerminologyConcept, ConceptMapping
from terminology.services.icd11 import ICD11Service
from terminology.services.snomed import SNOMEDService
from terminology.services.loinc import LOINCService
from kiosk.services.extraction import extract_clinical_json, ClinicalExtractionSchema


class V1IntakeAndProvenanceTests(APITestCase):
    def setUp(self):
        self.session = PatientSession.objects.create(
            status='active',
            language='en',
            consent_given=True,
            token_number=101
        )

    def test_structured_history_extraction_and_provenance(self):
        """Test extraction creates structured dictionary with proper provenance tags and logs audit."""
        payload = {
            "chief_complaint": "Severe chest pain radiating to left arm",
            "hpi": {
                "onset": "2 hours ago",
                "duration": "constant",
                "severity": 8,
                "character": "tight pressure",
                "location": "retrosternal",
                "associated_symptoms": ["shortness of breath", "sweating"],
                "aggravating_factors": ["deep breathing"],
                "relieving_factors": ["rest"]
            },
            "past_medical_history": ["hypertension"],
            "medications": ["amlodipine 5mg"],
            "allergies": ["penicillin"],
            "family_history": ["father had MI"],
            "social_history": ["smoker 10 pack years"],
            "missing_fields": []
        }

        with patch('kiosk.services.extraction.call_llm') as mock_llm:
            import json
            mock_llm.return_value = json.dumps(payload)
            res = extract_clinical_json("Patient reports severe chest pain.", self.session)

        self.assertIsNotNone(res)
        self.assertEqual(res["chief_complaint"]["text"], "Severe chest pain radiating to left arm")
        self.assertEqual(res["chief_complaint"]["provenance"], 'ai_extracted')
        self.assertEqual(res["hpi"]["severity"], 8)
        self.assertEqual(res["medications"][0]["provenance"], 'ai_extracted')
        
        # Verify ExtractionLog audit record
        logs = ExtractionLog.objects.filter(session=self.session)
        self.assertTrue(logs.exists())
        self.assertTrue(logs.first().is_valid)

    def test_body_pointing_canonical_regions_and_provenance(self):
        """Test body pointing canonical regions API and history attachment."""
        url = reverse('kiosk:body-pointing-regions')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("regions", res.data)
        region_ids = [r["id"] for r in res.data["regions"]]
        self.assertIn("chest", region_ids)

        # Test body pointing intake helper
        from kiosk.utils.body_pointing_helper import append_body_region_to_history
        history = append_body_region_to_history(self.session, "chest", provenance="patient_reported")
        self.assertEqual(history.hpi.get("location"), "chest")
        self.assertTrue(any("chest" in item.get("text", "").lower() for item in history.hpi.get("associated_symptoms", [])))

    def test_flagged_vitals_severity_logic(self):
        """Test abnormal / critical vitals severity computation and flagged endpoint."""
        reading = VitalReading.objects.create(
            session=self.session,
            systolic_bp=185,
            diastolic_bp=122,
            heart_rate=125,
            spo2=88,
            temperature=39.5,
            provenance='sensor'
        )
        self.assertTrue(reading.is_abnormal)
        self.assertEqual(reading.severity, 'critical')

        url = reverse('sensors:vitals-flagged', kwargs={'session_id': str(self.session.id)})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['flagged_readings'][0]['severity'], 'critical')

    def test_doctor_mark_reviewed_workflow(self):
        """Test clinician reviewed status update on PatientSession."""
        self.assertFalse(self.session.clinician_reviewed)
        url = reverse('doctor:review-session', kwargs={'session_id': str(self.session.id)})
        res = self.client.post(url, {'status': 'completed', 'notes': 'Assessed in OPD'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.session.refresh_from_db()
        self.assertTrue(self.session.clinician_reviewed)


class TerminologyServiceTests(APITestCase):
    def setUp(self):
        self.session = PatientSession.objects.create(
            status='active',
            language='en',
            consent_given=True,
            token_number=102
        )

    def test_icd11_service_resolution_and_catalog(self):
        """Test ICD-11 local catalog fallback and search."""
        service = ICD11Service()
        results = service.search("chest pain")
        self.assertGreater(len(results), 0)
        top = results[0]
        self.assertIn("score", top)
        self.assertEqual(top["concept"].code, "MD11")

    def test_snomed_service_search(self):
        """Test SNOMED CT clinical concept search."""
        service = SNOMEDService()
        results = service.search("cough")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["concept"].code, "49727002")

    def test_loinc_service_search(self):
        """Test LOINC lab observation search."""
        service = LOINCService()
        results = service.search("oxygen saturation")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["concept"].code, "2708-6")

    def test_terminology_mapping_and_confirmation_api(self):
        """Test mapping an unmapped term and doctor confirmation."""
        map_url = reverse('terminology:terminology-map')
        post_data = {
            "session_id": str(self.session.id),
            "items": [
                {
                    "text": "cough",
                    "concept_type": "symptom",
                    "preferred_system": "snomed_ct"
                }
            ]
        }
        res = self.client.post(map_url, post_data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(res.data['mappings']) > 0)
        mapping_id = res.data['mappings'][0]['id']
        self.assertEqual(res.data['mappings'][0]['review_status'], 'auto_mapped')

        # Clinician confirms the mapping
        confirm_url = reverse('terminology:confirm-mapping', kwargs={'mapping_id': mapping_id})
        res_confirm = self.client.post(confirm_url, {'action': 'confirm'}, format='json')
        self.assertEqual(res_confirm.status_code, status.HTTP_200_OK)
        self.assertEqual(res_confirm.data['review_status'], 'clinician_confirmed')
        self.assertEqual(res_confirm.data['provenance'], 'clinician_confirmed')


class V2DocumentIntelligenceTests(APITestCase):
    def setUp(self):
        self.session = PatientSession.objects.create(
            status='active',
            language='en',
            consent_given=True,
            token_number=103
        )

    def test_low_confidence_flagging_and_verification_flow(self):
        """Low-confidence fields (<0.75) must set needs_review=True and allow clinician review."""
        doc = MedicalDocument.objects.create(
            session=self.session,
            document_type='lab_report',
            overall_confidence=0.72,
            status='needs_review'
        )

        field = DocumentField.objects.create(
            document=doc,
            field_name='blood_glucose',
            field_value='180 mg/dL',
            confidence=0.68,
            needs_review=True,
            provenance='ai_extracted'
        )

        # Retrieve fields endpoint
        url_fields = reverse('kiosk:document-fields-list', kwargs={'document_id': doc.id})
        res_fields = self.client.get(url_fields)
        self.assertEqual(res_fields.status_code, status.HTTP_200_OK)
        self.assertTrue(res_fields.data[0]['needs_review'])

        # Clinician verifies field
        verify_url = reverse('kiosk:document-field-verify', kwargs={'document_id': doc.id, 'field_id': field.id})
        res_verify = self.client.post(verify_url, {'corrected_value': '180 mg/dL'}, format='json')
        self.assertEqual(res_verify.status_code, status.HTTP_200_OK)
        
        field.refresh_from_db()
        self.assertFalse(field.needs_review)
        self.assertEqual(field.provenance, 'clinician_confirmed')
