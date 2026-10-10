from django.contrib import admin
from .models import TerminologyConcept, ConceptMapping

@admin.register(TerminologyConcept)
class TerminologyConceptAdmin(admin.ModelAdmin):
    list_display = ('code', 'system', 'display', 'category')
    search_fields = ('code', 'display', 'description')
    list_filter = ('system', 'category')

@admin.register(ConceptMapping)
class ConceptMappingAdmin(admin.ModelAdmin):
    list_display = ('session', 'source_text', 'concept_type', 'terminology_concept', 'confidence', 'review_status', 'provenance')
    list_filter = ('review_status', 'concept_type', 'provenance')
    search_fields = ('source_text', 'terminology_concept__display')
