# DRF Serializer Imports

from rest_framework import serializers


# Local Application Model Imports

from .models import Medicine


# Medicine Serializer

class MedicineSerializer(serializers.ModelSerializer):
    # Serializer Meta Confi.

    class Meta:
        model = Medicine
        fields = ['id', 'brand_name', 'generic_name', 'dosage_form', 'strength', 'manufacturer']