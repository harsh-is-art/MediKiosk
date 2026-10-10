# Django Admin Imports

from django.contrib import admin


# Local Application Model Imports

from .models import Medicine


# Medicine Admin Confi.

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    # List Display Confi.

    list_display = ['brand_name', 'generic_name', 'dosage_form', 'strength', 'manufacturer']

    # Search Confi.

    search_fields = ['brand_name', 'generic_name']

    # List Filter Confi.

    list_filter = ['dosage_form']