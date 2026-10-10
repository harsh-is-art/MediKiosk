# Provenance Choices and Reusable Mixin / Field Definition

from django.db import models

PROVENANCE_CHOICES = [
    ('patient_reported', 'Patient Reported'),
    ('ai_extracted', 'AI Extracted'),
    ('ai_inferred', 'AI Inferred'),
    ('clinician_confirmed', 'Clinician Confirmed'),
]

class ProvenanceMixin(models.Model):
    provenance = models.CharField(
        max_length=30,
        choices=PROVENANCE_CHOICES,
        default='ai_extracted',
        help_text='Provenance tracking for clinical credibility'
    )

    class Meta:
        abstract = True
