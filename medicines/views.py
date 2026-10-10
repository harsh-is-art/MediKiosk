# Django REST Framework Imports

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

# Local Application Model, Serializer & Utility Imports

from .models import Medicine
from .serializers import MedicineSerializer
from .utils import fuzzy_match_medicine

# REST Framework Permission Imports

from rest_framework.permissions import AllowAny


# Medicine Search API View

class MedicineSearchView(APIView):
    # API Permissions

    permission_classes = [AllowAny]

    # HTTP GET Request Handler

    def get(self, request):
        """
        Searches for a medicine using the provided query
        and returns the closest matching medicine.
        """

        # Extract & Normalize Search Query

        query = request.query_params.get('q', '').strip()

        # Validate Search Query

        if not query or len(query) < 2:
            return Response(
                {'error': 'Query must be at least 2 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Perform Fuzzy Medicine Matching

        match_info = fuzzy_match_medicine(query, threshold=75)

        # Return Successful Medicine Match

        if match_info and match_info.get('medicine'):
            match = match_info['medicine']

            return Response({
                'found': True,
                'score': match_info['score'],
                'match_type': match_info['match_type'],
                'medicine': MedicineSerializer(match).data,
                'brand_name': match.brand_name,
                'generic_name': match.generic_name,
                'dosage_form': match.dosage_form,
                'strength': match.strength,
            })

        # Return No Medicine Match

        return Response({
            'found': False,
            'query': query,
            'match_type': match_info['match_type'] if match_info else 'no_match',
            'score': match_info['score'] if match_info else 0,
        })


# Medicine List API View

class MedicineListView(APIView):
    # API Permissions

    permission_classes = [AllowAny]

    # HTTP GET Request Handler

    def get(self, request):
        """
        Retrieves and returns the available medicines.
        """

        # Retrieve Medicine Records

        medicines = Medicine.objects.all()[:100]

        # Return Serialized Medicine List

        return Response(
            MedicineSerializer(medicines, many=True).data
        )