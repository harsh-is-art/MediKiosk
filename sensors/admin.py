# Django Admin Imports

from django.contrib import admin

# Local Application Model Imports

from .models import VitalReading


# Vital Reading Admin Confi.

@admin.register(VitalReading)
class VitalReadingAdmin(admin.ModelAdmin):
    # List Display Confi.

    list_display = ['session', 'spo2', 'heart_rate', 'temperature', 'is_valid', 'created_at']

    # List Filter Confi.

    list_filter = ['is_valid']