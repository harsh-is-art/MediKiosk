# Doctor Serializers Definition

from rest_framework import serializers
from .models import DoctorProfile, DoctorNote


# Doctor Profile Serializer

class DoctorProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for DoctorProfile model.
    """

    # Serializer Meta Confi.

    class Meta:
        model = DoctorProfile
        fields = ['id', 'name', 'specialization', 'department', 'registration_number', 'phone', 'is_available', 'created_at']
        read_only_fields = ['id', 'created_at']


# Doctor Note Serializer

class DoctorNoteSerializer(serializers.ModelSerializer):
    """
    Serializer for DoctorNote model.
    """

    # Doctor Name Field

    doctor_name = serializers.CharField(source='doctor.name', read_only=True)

    # Serializer Meta Confi.

    class Meta:
        model = DoctorNote
        fields = ['id', 'session', 'doctor', 'doctor_name', 'note_text', 'prescription_notes', 'created_at']
        read_only_fields = ['id', 'created_at']