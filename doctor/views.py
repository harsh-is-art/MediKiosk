# Django & REST Framework Imports

import logging
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny


# Local Application Model & Serializer Imports

from kiosk.models import PatientSession
from .models import DoctorProfile, DoctorNote
from .serializers import DoctorProfileSerializer, DoctorNoteSerializer


# Application Logger Confi.

logger = logging.getLogger(__name__)


# Doctor Dashboard Template View

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Renders the web dashboard HTML interface for doctors.
    """
    template_name = 'doctor/dashboard.html'
    login_url = '/admin/login/'

    def get_context_data(self, **kwargs):
        """
        Fetches all patient sessions with pre-fetched documents, summaries, vitals, and conversation history.
        """
        context = super().get_context_data(**kwargs)

        # Retrieve all sessions prefetching documents, summary, vitals, conversations, and V1/V2 records
        sessions = PatientSession.objects.all().prefetch_related(
            'documents', 'medical_documents__fields', 'medical_documents__medications',
            'medical_documents__lab_results', 'vitals', 'conversations',
            'terminology_mappings__terminology_concept'
        ).select_related('summary', 'structured_history').order_by('-created_at')

        context['all_sessions'] = sessions
        context['active_sessions'] = [s for s in sessions if s.status == 'active']
        context['completed_sessions'] = [s for s in sessions if s.status == 'completed']

        return context


# Doctor Clinical Note API Endpoint View

class DoctorNoteCreateView(APIView):
    """
    POST /doctor/api/notes/ — Doctor submits clinical notes for a session.
    Requires authenticated user with an associated DoctorProfile.
    """

    # API Permissions

    permission_classes = [IsAuthenticated]

    # HTTP POST Request Handler

    def post(self, request):
        """
        Processes incoming doctor note data and attaches it to the
        patient session using authenticated user.
        """

        # Verify Authenticated User Has a Doctor Profile

        try:
            doctor = request.user.doctor_profile
        except (AttributeError, DoctorProfile.DoesNotExist):
            return Response(
                {'error': 'Authenticated user does not have an associated doctor profile.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Extract Payload Data

        session_id = request.data.get('session_id')
        note_text = request.data.get('note_text')
        prescription_notes = request.data.get('prescription_notes', '')

        # Validate Mandatory Parameters

        if not session_id or not note_text:
            return Response(
                {'error': 'session_id and note_text are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retrieve Corresponding Patient Session Object

        try:
            session = PatientSession.objects.get(id=session_id)
        except PatientSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Create Doctor Note Record

        note = DoctorNote.objects.create(
            session=session,
            doctor=doctor,
            
            note_text=note_text,
            prescription_notes=prescription_notes
        )

        # Return Serialized Doctor Note Response

        return Response(DoctorNoteSerializer(note).data, status=status.HTTP_201_CREATED)


class MarkSessionReviewedView(APIView):
    """
    POST /doctor/api/session/<session_id>/review/ — Doctor marks a session as reviewed.
    Stamps clinician_reviewed = True on PatientSession and records doctor notes if provided.
    """
    permission_classes = [AllowAny]

    def post(self, request, session_id):
        try:
            session = PatientSession.objects.get(id=session_id)
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        session.clinician_reviewed = True
        session.status = 'completed'
        session.save()

        # Stamp any unverified terminology mappings for this session as clinician_confirmed if requested
        if request.data.get('confirm_terminology', False):
            if hasattr(session, 'terminology_mappings'):
                session.terminology_mappings.filter(review_status='needs_review').update(
                    review_status='clinician_confirmed',
                    provenance='clinician_confirmed'
                )

        return Response({
            'session_id': str(session.id),
            'status': session.status,
            'clinician_reviewed': session.clinician_reviewed,
            'message': f'Session #{session.token_number or session.id} marked as clinician reviewed.'
        }, status=status.HTTP_200_OK)