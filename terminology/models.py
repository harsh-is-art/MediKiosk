from django.db import models
from kiosk.provenance import PROVENANCE_CHOICES

class TerminologyConcept(models.Model):
    SYSTEM_CHOICES = [
        ('icd11', 'ICD-11 (WHO)'),
        ('snomed_ct', 'SNOMED CT'),
        ('loinc', 'LOINC'),
    ]

    code = models.CharField(max_length=100, db_index=True)
    system = models.CharField(max_length=20, choices=SYSTEM_CHOICES, db_index=True)
    display = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    category = models.CharField(max_length=50, blank=True, default='', help_text='symptom, finding, lab, diagnosis, medication')

    class Meta:
        unique_together = ('code', 'system')
        ordering = ['system', 'code']

    def __str__(self):
        return f"[{self.system.upper()}] {self.code} - {self.display}"


class ConceptMapping(models.Model):
    CONCEPT_TYPE_CHOICES = [
        ('symptom', 'Symptom'),
        ('finding', 'Clinical Finding'),
        ('lab', 'Laboratory Observation'),
        ('diagnosis', 'Suspected Diagnosis'),
        ('medication', 'Medication'),
    ]

    REVIEW_STATUS_CHOICES = [
        ('auto_mapped', 'Auto Mapped'),
        ('needs_review', 'Needs Review'),
        ('clinician_confirmed', 'Clinician Confirmed'),
        ('clinician_rejected', 'Clinician Rejected'),
    ]

    session = models.ForeignKey('kiosk.PatientSession', on_delete=models.CASCADE, related_name='terminology_mappings')
    source_text = models.CharField(max_length=500)
    concept_type = models.CharField(max_length=30, choices=CONCEPT_TYPE_CHOICES, default='symptom')
    terminology_concept = models.ForeignKey(TerminologyConcept, on_delete=models.CASCADE, related_name='mappings')
    confidence = models.FloatField(default=0.0)
    review_status = models.CharField(max_length=30, choices=REVIEW_STATUS_CHOICES, default='auto_mapped')
    provenance = models.CharField(max_length=30, choices=PROVENANCE_CHOICES, default='ai_extracted')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-confidence', '-created_at']

    def __str__(self):
        return f"Mapping: {self.source_text} -> {self.terminology_concept.code} ({self.review_status})"
