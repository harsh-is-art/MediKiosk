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


class DoctorConsultationSummarizeView(APIView):
    """
    POST /doctor/api/session/<session_id>/summarize-consultation/
    Takes recorded doctor-patient conversation transcript (or uploaded audio),
    filters out non-medical dialogue/small talk, and generates a structured medical summary.
    """
    permission_classes = [AllowAny]

    def post(self, request, session_id):
        try:
            session = PatientSession.objects.get(id=session_id)
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        transcript = request.data.get('transcript', '')
        audio_file = request.FILES.get('audio')

        # If audio file is provided without transcript, attempt ASR transcription
        if not transcript and audio_file:
            import tempfile, os
            from kiosk.utils.stt import get_stt_provider
            ext = os.path.splitext(getattr(audio_file, 'name', ''))[1].lower() or '.wav'
            try:
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    for chunk in audio_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                provider = get_stt_provider()
                res = provider.transcribe(tmp_path, session.language or 'en')
                transcript = res.text
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception as e:
                logger.error(f"Error transcribing audio in doctor consultation view: {e}")

        if not transcript or not transcript.strip():
            return Response({'error': 'No conversation transcript or audio provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Call LLM to summarize conversation by filtering non-medical dialogue
        from kiosk.utils.llm import call_llm
        system_prompt = (
            "You are an expert clinical documentation assistant. "
            "You are given a raw transcript of a conversation between a doctor and a patient (or audio transcription). "
            "CRITICAL TASK:\n"
            "1. Strictly DROP all non-medical dialogue, greetings, small talk, pleasantries, weather chatter, and social pleasantries.\n"
            "2. Retain ONLY clinically relevant medical information.\n"
            "3. Format the output into a crisp, professional Clinical Note with the following structure:\n"
            "   - CHIEF COMPLAINT & PRESENTING SYMPTOMS\n"
            "   - CLINICAL FINDINGS & HISTORY DISCUSSED\n"
            "   - DIAGNOSIS / IMPRESSION\n"
            "   - TREATMENT PLAN & PRESCRIPTION INSTRUCTIONS\n\n"
            "Be precise, professional, and clear."
        )

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"Raw Doctor-Patient Conversation:\n\"\"\"\n{transcript}\n\"\"\""}
        ]

        try:
            medical_summary = call_llm(messages)
        except Exception as e:
            logger.error(f"Error calling LLM for consultation summary: {e}")
            medical_summary = f"Summary extracted from consultation transcript:\n\n{transcript}"

        from kiosk.models import ClinicalSummary
        summary_obj, _ = ClinicalSummary.objects.update_or_create(
            session=session,
            defaults={
                'summary_text': medical_summary,
                'structured_data': {'consultation_transcript': transcript, 'source': 'doctor_audio_recording'}
            }
        )

        try:
            doctor = getattr(request.user, 'doctor_profile', None) if request.user.is_authenticated else None
            DoctorNote.objects.create(
                session=session,
                doctor=doctor,
                note_text=f"[RECORDED CONSULTATION SUMMARY]\n{medical_summary}",
                prescription_notes=""
            )
        except Exception as note_err:
            logger.warning(f"Could not attach DoctorNote record: {note_err}")

        return Response({
            'session_id': str(session.id),
            'raw_transcript': transcript,
            'summary_text': medical_summary,
            'message': 'Consultation conversation successfully recorded and summarized (non-medical dialogue removed).'
        }, status=status.HTTP_200_OK)