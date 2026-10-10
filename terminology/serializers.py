from rest_framework import serializers
from .models import TerminologyConcept, ConceptMapping

class TerminologyConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TerminologyConcept
        fields = ['id', 'code', 'system', 'display', 'description', 'category']

class ConceptMappingSerializer(serializers.ModelSerializer):
    concept = TerminologyConceptSerializer(source='terminology_concept', read_only=True)

    class Meta:
        model = ConceptMapping
        fields = [
            'id', 'session', 'source_text', 'concept_type',
            'terminology_concept', 'concept', 'confidence',
            'review_status', 'provenance', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
