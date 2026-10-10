# Module & Testing Framework Imports

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Medicine
from .utils import fuzzy_match_medicine, correct_ocr_medicines

# Medicine API & Fuzzy Match Tests

class MedicineAPITests(APITestCase):
    # Test Data Setup

    def setUp(self):
        self.med = Medicine.objects.create(
            brand_name='Dolo-650',
            generic_name='Paracetamol',
            dosage_form='Tablet',
            strength='650mg',
            manufacturer='Micro Labs'
        )

    # Medicine List API Test

    def test_list_medicines(self):
        """
        Verifies that the medicine list endpoint returns
        the available medicine records successfully.
        """

        url = reverse('medicines:medicine-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    # Medicine Search Tests

    def test_search_medicine_found(self):
        """
        Verifies that an exact medicine search returns
        the expected medicine record.
        """

        url = reverse('medicines:medicine-search') + '?q=Paracetamol'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['found'])
        self.assertEqual(response.data['brand_name'], 'Dolo-650')

    def test_search_medicine_fuzzy_typo(self):
        """
        Verifies that the medicine search can identify
        a medicine despite a minor spelling error.
        """

        url = reverse('medicines:medicine-search') + '?q=Paracetamoll'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['found'])
        self.assertEqual(response.data['brand_name'], 'Dolo-650')

    def test_search_medicine_short_query(self):
        """
        Verifies that an excessively short search query
        is rejected by the API.
        """

        url = reverse('medicines:medicine-search') + '?q=a'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Fuzzy Matching Utility Tests

    def test_fuzzy_match_util(self):
        """
        Verifies that the fuzzy medicine matching utility
        identifies the expected medicine and score.
        """

        match_info = fuzzy_match_medicine('Paracetamol')

        self.assertIsNotNone(match_info)
        self.assertEqual(match_info['medicine'].brand_name, 'Dolo-650')
        self.assertTrue(match_info['score'] >= 75)
        self.assertIn(
            match_info['match_type'],
            ['exact', 'strong_fuzzy', 'weak_fuzzy']
        )

    def test_weak_fuzzy_match_rejection(self):
        """
        Verifies that a weak or ambiguous medicine string
        is rejected when using the 75 threshold.
        """

        # Weak/ambiguous string should return None with 75 threshold

        match_info = fuzzy_match_medicine('XyzRandomPharm')

        self.assertIsNone(match_info)

    # OCR Medicine Correction Tests

    def test_correct_ocr_medicines_util(self):
        """
        Verifies that medicine names extracted from OCR text
        can be corrected using fuzzy matching.
        """

        results = correct_ocr_medicines('Tab. Dolo-650 1-0-1')

        self.assertEqual(len(results), 1)
        self.assertTrue('Dolo-650' in results[0]['corrected'])
        self.assertTrue(results[0]['score'] >= 75)