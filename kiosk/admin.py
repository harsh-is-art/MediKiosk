# Django Admin Imports

from django.contrib import admin


# Local Application Model Imports

from .models import PatientSession, ConversationLog, DocumentUpload, ClinicalSummary


# Conversation Log Inline Administration

class ConversationInline(admin.TabularInline):
    """
    Inline administration configuration for conversation logs
    associated with a patient session.
    """

    # Inline Confi.

    model = ConversationLog
    extra = 0
    readonly_fields = ['created_at']


# Document Upload Inline Administration

class DocumentInline(admin.TabularInline):
    """
    Inline administration configuration for documents
    associated with a patient session.
    """

    # Inline Confi.

    model = DocumentUpload
    extra = 0
    readonly_fields = ['created_at']


# Patient Session Admin

@admin.register(PatientSession)
class PatientSessionAdmin(admin.ModelAdmin):
    """
    Admin configuration for PatientSession model.
    """

    # List Display Confi.

    list_display = ['id', 'token_number', 'status', 'language', 'consent_given', 'created_at']

    # List Filter Confi.

    list_filter = ['status', 'language', 'consent_given']

    # Search Confi.

    search_fields = ['id', 'abha_id']

    # Read-Only Fields

    readonly_fields = ['id', 'created_at', 'updated_at']

    # Related Inline Models

    inlines = [ConversationInline, DocumentInline]


# Conversation Log Admin

@admin.register(ConversationLog)
class ConversationLogAdmin(admin.ModelAdmin):
    """
    Admin configuration for ConversationLog model.
    """

    # List Display Confi.

    list_display = ['session', 'role', 'content_preview', 'input_type', 'created_at']

    # List Filter Confi.

    list_filter = ['role', 'input_type']

    # Content Preview

    def content_preview(self, obj):
        """
        Returns a shortened preview of the conversation content.
        """

        return obj.content[:80]

    content_preview.short_description = 'Content'


# Document Upload Admin

@admin.register(DocumentUpload)
class DocumentUploadAdmin(admin.ModelAdmin):
    """
    Admin configuration for DocumentUpload model.
    """

    # List Display Confi.

    list_display = ['session', 'ocr_provider', 'ocr_confidence', 'created_at']

    # List Filter Confi.

    list_filter = ['ocr_provider']


# Clinical Summary Admin

@admin.register(ClinicalSummary)
class ClinicalSummaryAdmin(admin.ModelAdmin):
    """
    Admin configuration for ClinicalSummary model.
    """

    # List Display Confi.

    list_display = ['session', 'summary_preview', 'generated_at']

    # Summary Preview

    def summary_preview(self, obj):
        """
        Returns a shortened preview of the clinical summary.
        """

        return obj.summary_text[:100]

    summary_preview.short_description = 'Summary'