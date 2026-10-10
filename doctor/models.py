# Django & Application Imports

from django.db import models
from django.contrib.auth.models import User
from kiosk.models import PatientSession


# Doctor Profile Model Definition

class DoctorProfile(models.Model):
    """
    Profile for doctors working with the MediKiosk system.
    """

    # Database Fields

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile', null=True, blank=True)
    name = models.CharField(max_length=150)
    specialization = models.CharField(max_length=100, default='General Physician')
    department = models.CharField(max_length=100, default='General OPD')
    registration_number = models.CharField(max_length=50, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Model Meta Confi.

    class Meta:
        ordering = ['name']

    # String Representation

    def __str__(self):
        return f"Dr. {self.name} ({self.specialization})"


# Doctor Note Model Definition

class DoctorNote(models.Model):
    """
    Clinical notes and directives recorded by doctor for a patient session.
    """

    # Database Fields

    session = models.ForeignKey(PatientSession, on_delete=models.CASCADE, related_name='doctor_notes')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')
    note_text = models.TextField(help_text="Doctor's clinical assessment and treatment plan")
    prescription_notes = models.TextField(blank=True, default='', help_text="Prescribed medicines/dosage")
    created_at = models.DateTimeField(auto_now_add=True)

    # Model Meta Confi.

    class Meta:
        ordering = ['-created_at']

    # String Representation

    def __str__(self):
        return f"Note for Session {self.session_id} by {self.doctor or 'Doctor'}"

