# Module & Testing Framework Imports

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from kiosk.models import PatientSession
from .models import DoctorProfile, DoctorNote


# Doctor Dashboard & Notes API Tests

class DoctorDashboardTests(APITestCase):
    """
    Test cases for the doctor dashboard and doctor notes API.
    """

    # Test Data Setup

    def setUp(self):
        """
        Creates the test user, patient sessions, and doctor profile
        required for the test cases.
        """

        self.user = User.objects.create_user(username='dr_sharma', password='password123')
        self.active_session = PatientSession.objects.create(status='active', language='en', consent_given=True, token_number=1)
        self.completed_session = PatientSession.objects.create(status='completed', language='hi', consent_given=True, token_number=2)
        self.doctor = DoctorProfile.objects.create(
            user=self.user,
            name='Sharma',
            specialization='General Physician',
            department='OPD-1'
        )

    # Dashboard Authentication Tests

    def test_dashboard_view_unauthenticated_redirects(self):
        """
        Verifies that unauthenticated users are redirected
        when accessing the doctor dashboard.
        """

        url = reverse('doctor:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_dashboard_view_authenticated_doctor(self):
        """
        Verifies that an authenticated doctor can access
        the doctor dashboard successfully.
        """

        self.client.login(username='dr_sharma', password='password123')
        url = reverse('doctor:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Doctor Dashboard')

    # Doctor Note Model Tests

    def test_doctor_note_creation_model(self):
        """
        Verifies that a DoctorNote can be created and correctly
        associated with a patient session and doctor.
        """

        note = DoctorNote.objects.create(
            session=self.active_session,
            doctor=self.doctor,
            note_text='Patient diagnosed with mild viral fever.',
            prescription_notes='Paracetamol 500mg TDS'
        )
        self.assertEqual(note.session, self.active_session)
        self.assertEqual(note.doctor.name, 'Sharma')
        self.assertIn('Sharma', str(note))

    # Unauthenticated Note Creation Test

    def test_create_note_unauthenticated_rejected(self):
        """
        Verifies that unauthenticated users cannot create
        doctor notes.
        """

        url = reverse('doctor:create-note')
        data = {
            'session_id': str(self.active_session.id),
            'note_text': 'Unauthenticated note',
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    # Authenticated Note Creation Test

    def test_create_note_authenticated(self):
        """
        Verifies that an authenticated doctor can successfully
        create a doctor note.
        """

        self.client.force_authenticate(user=self.user)
        url = reverse('doctor:create-note')
        data = {
            'session_id': str(self.active_session.id),
            'note_text': 'Prescribed rest and hydration.',
            'prescription_notes': 'Paracetamol 500mg'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['note_text'], 'Prescribed rest and hydration.')

    # Doctor Impersonation Prevention Test

    def test_impersonation_prevented_uses_logged_in_doctor(self):
        """
        Verifies that a doctor cannot create a note on behalf
        of another doctor by supplying another doctor's ID.
        """

        other_user = User.objects.create_user(username='dr_other', password='password123')
        other_doctor = DoctorProfile.objects.create(user=other_user, name='Other Doctor')

        self.client.force_authenticate(user=self.user)
        url = reverse('doctor:create-note')

        # Try passing other_doctor.id in request
        data = {
            'session_id': str(self.active_session.id),
            'doctor_id': other_doctor.id,
            'note_text': 'Testing doctor profile binding',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify saved note belongs to self.doctor (Sharma), not other_doctor
        saved_note = DoctorNote.objects.get(id=response.data['id'])
        self.assertEqual(saved_note.doctor, self.doctor)