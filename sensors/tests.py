# Module & Testing Framework Imports

import uuid
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from kiosk.models import PatientSession
from .models import VitalReading


# Sensor API Test Cases

class SensorsAPITests(APITestCase):
    # Test Data Setup

    def setUp(self):
        self.session = PatientSession.objects.create(
            status='active',
            language='en',
            consent_given=True,
            token_number=1
        )

    # Valid Vital Reading Test

    def test_post_vitals_valid(self):
        url = reverse('sensors:vitals-post')

        data = {
            'session_id': str(self.session.id),
            'spo2': 98.0,
            'heart_rate': 72,
            'temperature': 36.6
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_valid'])

    # Abnormal Vital Reading Test

    def test_post_vitals_abnormal(self):
        url = reverse('sensors:vitals-post')

        data = {
            'session_id': str(self.session.id),
            'spo2': 88.0,
            'heart_rate': 130,
            'temperature': 39.0
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('spo2', response.data['is_abnormal'])
        self.assertIn('heart_rate', response.data['is_abnormal'])

    # Inactive Session Validation Test

    def test_post_vitals_inactive_session_rejected(self):
        inactive_session = PatientSession.objects.create(
            status='completed',
            language='en',
            consent_given=True
        )

        url = reverse('sensors:vitals-post')

        data = {
            'session_id': str(inactive_session.id),
            'spo2': 98.0,
            'heart_rate': 75
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no longer active', response.data['error'])

    # Malformed Session UUID Test

    def test_post_vitals_malformed_uuid(self):
        url = reverse('sensors:vitals-post')

        data = {
            'session_id': 'invalid-uuid-123',
            'spo2': 98.0,
            'heart_rate': 75
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # NaN Vital Reading Validation Test

    def test_post_vitals_nan_rejected(self):
        url = reverse('sensors:vitals-post')

        data = {
            'session_id': str(self.session.id),
            'spo2': 'NaN',
            'heart_rate': 75
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Sensor Authentication Validation Test

    def test_post_vitals_auth_required_rejection(self):
        url = reverse('sensors:vitals-post')

        data = {
            'session_id': str(self.session.id),
            'spo2': 98.0,
            'heart_rate': 72,
        }

        with self.settings(
            SENSOR_AUTH_REQUIRED=True,
            SENSOR_SECRET_KEY='valid-secret'
        ):

            # Missing Sensor Secret

            resp_missing = self.client.post(
                url,
                data,
                format='json'
            )

            self.assertEqual(
                resp_missing.status_code,
                status.HTTP_401_UNAUTHORIZED
            )

            # Invalid Sensor Secret

            resp_invalid = self.client.post(
                url,
                data,
                format='json',
                HTTP_X_SENSOR_SECRET='wrong'
            )

            self.assertEqual(
                resp_invalid.status_code,
                status.HTTP_401_UNAUTHORIZED
            )

            # Valid Sensor Secret

            resp_valid = self.client.post(
                url,
                data,
                format='json',
                HTTP_X_SENSOR_SECRET='valid-secret'
            )

            self.assertEqual(
                resp_valid.status_code,
                status.HTTP_201_CREATED
            )