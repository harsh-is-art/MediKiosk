# Sensor Serializers Definition

from rest_framework import serializers
from .models import VitalReading


# Vital Reading Serializer

class VitalReadingSerializer(serializers.ModelSerializer):
    abnormal_details = serializers.ReadOnlyField()

    # Serializer Meta Confi.

    class Meta:
        model = VitalReading
        fields = [
            'id', 'session', 'spo2', 'heart_rate', 'systolic_bp', 'diastolic_bp',
            'temperature', 'is_valid', 'is_abnormal', 'severity', 'provenance',
            'abnormal_details', 'created_at'
        ]
        read_only_fields = ['id', 'is_abnormal', 'severity', 'abnormal_details', 'created_at']