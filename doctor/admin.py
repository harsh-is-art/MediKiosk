# Django Admin Imports

from django.contrib import admin
from .models import DoctorProfile, DoctorNote


# Doctor Profile Admin

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for DoctorProfile model.
    """

    # List Display 

    list_display = ['name', 'specialization', 'department', 'registration_number', 'is_available', 'created_at']

    # List Filter 
    
    list_filter = ['specialization', 'department', 'is_available']

    # Search Confi.

    search_fields = ['name', 'registration_number', 'department']


# Doctor Note 

@admin.register(DoctorNote)
class DoctorNoteAdmin(admin.ModelAdmin):
    
    # List Display 

    list_display = ['session', 'doctor', 'note_preview', 'created_at']

    # List Filter 

    list_filter = ['doctor', 'created_at']

    # Search 

    search_fields = ['session__id', 'note_text', 'prescription_notes']

    # Note Preview

    def note_preview(self, obj):
        return obj.note_text[:80]

    note_preview.short_description = 'Note Preview'