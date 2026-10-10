# DRF Serializers Definition

from rest_framework import serializers
from .models import PatientSession, ConversationLog, DocumentUpload, ClinicalSummary


# Session Start Serializer

class SessionStartSerializer(serializers.Serializer):
    """
    Validates session start request.
    """

    # Session Start Fields

    language = serializers.ChoiceField(choices=PatientSession.LANGUAGE_CHOICES, default='en')
    consent = serializers.BooleanField(required=True)


# Patient Session Serializer

class SessionSerializer(serializers.ModelSerializer):
    """
    Serializer for PatientSession model.
    """

    # Serializer Meta Confi.

    class Meta:
        model = PatientSession
        fields = [
            'id', 'status', 'language', 'consent_given', 'abha_id',
            'chief_complaints', 'selected_body_regions', 'token_number',
            'red_flags', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'token_number', 'created_at', 'updated_at']


# Conversation Serializer

class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for ConversationLog model.
    """

    # Serializer Meta Confi.

    class Meta:
        model = ConversationLog
        fields = ['id', 'session', 'role', 'content', 'input_type', 'confidence', 'created_at']
        read_only_fields = ['id', 'session', 'created_at']


# Chat Input Serializer

class ChatInputSerializer(serializers.Serializer):
    """
    Validates chat message input.
    """

    session_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="SESSION_START")
    input_type = serializers.ChoiceField(
        choices=ConversationLog.INPUT_TYPE_CHOICES,
        default='text',
        required=False
    )


# Symptom Input Serializer

class SymptomInputSerializer(serializers.Serializer):
    """
    Validates symptom/body region selection.
    """

    # Symptom Input Fields

    session_id = serializers.UUIDField()
    complaints = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    body_regions = serializers.ListField(child=serializers.CharField(), required=False, default=list)


# Document Upload Serializer

class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for DocumentUpload model.
    """

    # Serializer Meta Confi.

    class Meta:
        model = DocumentUpload
        fields = ['id', 'session', 'image', 'raw_ocr_text', 'extracted_entities', 'ocr_provider', 'ocr_confidence', 'created_at']
        read_only_fields = ['id', 'raw_ocr_text', 'extracted_entities', 'ocr_provider', 'ocr_confidence', 'created_at']


# Clinical Summary Serializer

class ClinicalSummarySerializer(serializers.ModelSerializer):
    """
    Serializer for ClinicalSummary model.
    """

    # Serializer Meta Confi.

    class Meta:
        model = ClinicalSummary
        fields = ['id', 'session', 'summary_text', 'structured_data', 'generated_at']
        read_only_fields = ['id', 'generated_at']


# ASR Input Serializer

class ASRInputSerializer(serializers.Serializer):
    """
    Validates audio transcription request.
    """

    # ASR Input Fields

    session_id = serializers.UUIDField()
    language = serializers.CharField(default='en')


# TTS Input Serializer

class TTSInputSerializer(serializers.Serializer):
    """
    Validates text-to-speech synthesis request.
    """

    # TTS Input Fields

    text = serializers.CharField(max_length=2000)
    language = serializers.CharField(default='en', max_length=10)
    speaker = serializers.CharField(required=False, default=None, allow_null=True)


# =====================================================================
# V1 & V2 EXTENDED SERIALIZERS
# =====================================================================

from .models import (
    StructuredHistory, MedicalDocument, DocumentField,
    DocumentMedication, DocumentLabResult
)

class StructuredHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StructuredHistory
        fields = [
            'id', 'session', 'chief_complaint', 'hpi', 'past_medical_history',
            'medications', 'allergies', 'family_history', 'social_history',
            'missing_fields', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentField
        fields = [
            'id', 'document', 'field_name', 'field_value', 'confidence',
            'needs_review', 'provenance', 'verified_by', 'verified_at',
            'rejection_reason'
        ]
        read_only_fields = ['id', 'verified_at']


class DocumentMedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentMedication
        fields = ['id', 'document', 'name', 'dose', 'frequency', 'duration', 'confidence', 'needs_review']
        read_only_fields = ['id']


class DocumentLabResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentLabResult
        fields = ['id', 'document', 'test_name', 'value', 'unit', 'reference_range', 'confidence', 'loinc_code', 'needs_review']
        read_only_fields = ['id']


class MedicalDocumentSerializer(serializers.ModelSerializer):
    fields = DocumentFieldSerializer(many=True, read_only=True)
    medications = DocumentMedicationSerializer(many=True, read_only=True)
    lab_results = DocumentLabResultSerializer(many=True, read_only=True)

    class Meta:
        model = MedicalDocument
        fields = [
            'id', 'session', 'document_type', 'image_file', 'processed_image_file',
            'status', 'overall_confidence', 'created_at', 'fields', 'medications', 'lab_results'
        ]
        read_only_fields = ['id', 'status', 'overall_confidence', 'created_at']