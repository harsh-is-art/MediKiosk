import uuid
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from kiosk.models import PatientSession
from .models import TerminologyConcept, ConceptMapping
from .serializers import TerminologyConceptSerializer, ConceptMappingSerializer
from .services.icd11 import ICD11Service
from .services.snomed import SNOMEDService
from .services.loinc import LOINCService

logger = logging.getLogger(__name__)

icd11_service = ICD11Service()
snomed_service = SNOMEDService()
loinc_service = LOINCService()

class TerminologyMapView(APIView):
    """
    POST /api/terminology/map/
    Maps free-text clinical items to standardized medical terminology concepts.
    Rule: AI identifies clinical concept; terminology service resolves standardized code.
    Never invents codes.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        session_id = request.data.get('session_id')
        items = request.data.get('items', [])
        # items format: [{'text': 'severe cough', 'concept_type': 'symptom', 'preferred_system': 'icd11'}]

        if not session_id or not items:
            return Response(
                {'error': 'session_id and items are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = PatientSession.objects.get(id=uuid.UUID(str(session_id)))
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        mappings_created = []

        for item in items:
            text = item.get('text', '').strip()
            if not text:
                continue

            concept_type = item.get('concept_type', 'symptom')
            pref_system = item.get('preferred_system', 'icd11').lower()

            res = None
            if pref_system == 'icd11' or concept_type in ('symptom', 'diagnosis'):
                res = icd11_service.resolve_concept(text)
                if not res:
                    res = snomed_service.resolve_concept(text)
            elif pref_system == 'loinc' or concept_type == 'lab':
                res = loinc_service.resolve_concept(text)
            elif pref_system == 'snomed_ct' or concept_type == 'medication':
                res = snomed_service.resolve_concept(text)

            if res:
                concept = res['concept']
                confidence = round(res['score'], 2)
                review_status = 'auto_mapped' if confidence >= 0.75 else 'needs_review'

                mapping, _ = ConceptMapping.objects.update_or_create(
                    session=session,
                    source_text=text,
                    concept_type=concept_type,
                    terminology_concept=concept,
                    defaults={
                        'confidence': confidence,
                        'review_status': review_status,
                        'provenance': 'ai_extracted',
                    }
                )
                mappings_created.append(mapping)

        return Response({
            'session_id': str(session.id),
            'mapped_count': len(mappings_created),
            'mappings': ConceptMappingSerializer(mappings_created, many=True).data
        }, status=status.HTTP_200_OK)


class TerminologySearchView(APIView):
    """
    GET /api/terminology/search/?q=...&system=...
    Searches standard concepts by query.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        system = request.query_params.get('system', '').lower().strip()

        if not query:
            return Response([])

        results = []
        if system == 'icd11':
            results = icd11_service.search(query)
        elif system == 'snomed_ct':
            results = snomed_service.search(query)
        elif system == 'loinc':
            results = loinc_service.search(query)
        else:
            # Search across all 3
            results.extend(icd11_service.search(query))
            results.extend(snomed_service.search(query))
            results.extend(loinc_service.search(query))

        data = []
        for r in results:
            concept_data = TerminologyConceptSerializer(r['concept']).data
            concept_data['match_score'] = r['score']
            data.append(concept_data)

        return Response(data)


class SessionTerminologyView(APIView):
    """
    GET /api/terminology/session/<session_id>/
    Retrieves all mapped terminology concepts for a patient session.
    """
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            session = PatientSession.objects.get(id=uuid.UUID(str(session_id)))
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        mappings = ConceptMapping.objects.filter(session=session).select_related('terminology_concept')
        return Response({
            'session_id': str(session.id),
            'mappings': ConceptMappingSerializer(mappings, many=True).data
        })


class ConfirmMappingView(APIView):
    """
    POST /api/terminology/mapping/<mapping_id>/confirm/
    Doctor confirms or rejects a terminology mapping.
    """
    permission_classes = [AllowAny]  # OPD workstation compatible

    def post(self, request, mapping_id):
        try:
            mapping = ConceptMapping.objects.get(id=mapping_id)
        except ConceptMapping.DoesNotExist:
            return Response({'error': 'Mapping not found.'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action', 'confirm') # 'confirm' or 'reject'
        if action == 'confirm':
            mapping.review_status = 'clinician_confirmed'
            mapping.provenance = 'clinician_confirmed'
        elif action == 'reject':
            mapping.review_status = 'clinician_rejected'
        mapping.save()

        return Response(ConceptMappingSerializer(mapping).data)
