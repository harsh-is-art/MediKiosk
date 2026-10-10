# Module & Library Imports

import os
import uuid
import logging
import tempfile
import requests
from PIL import Image
from django.conf import settings
from django.db import transaction, models
from django.core.files import File
from django.http import StreamingHttpResponse
import json
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import PatientSession, ConversationLog, DocumentUpload, ClinicalSummary
from .serializers import (
    SessionStartSerializer, SessionSerializer, ChatInputSerializer,
    SymptomInputSerializer, ASRInputSerializer, TTSInputSerializer, ClinicalSummarySerializer,
    ConversationSerializer
)

logger = logging.getLogger(__name__)

# Constants
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/tiff']

MAX_AUDIO_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
ALLOWED_AUDIO_EXTENSIONS = ['.wav', '.webm', '.mp3', '.ogg', '.m4a', '.flac']


# Custom Rate Throttles


class HeavyAIThrottle(UserRateThrottle):
    scope = 'heavy_ai'


class HeavyAIAnonThrottle(AnonRateThrottle):
    scope = 'heavy_ai'


# Helper Functions

def get_active_session_or_response(session_id):
    """
    Retrieves and validates that a PatientSession exists and is active.
    Falls back to auto-creating an active session if missing or invalid.
    """
    if not session_id:
        session = PatientSession.objects.create(language='hi', consent_given=True, status='active')
        return session, None

    try:
        uuid_obj = uuid.UUID(str(session_id))
        session = PatientSession.objects.get(id=uuid_obj)
        if session.status != 'active':
            session.status = 'active'
            session.save()
        return session, None
    except Exception:
        session = PatientSession.objects.create(language='hi', consent_given=True, status='active')
        return session, None


from django.utils import timezone
from .models import PatientSession, DailyTokenCounter, ConversationLog, DocumentUpload, ClinicalSummary


# Session Start API View

class SessionStartView(APIView):
    """
    POST /api/session/start/ — Create a new active patient session with atomic token generation.
    Publicly accessible for patient kiosk initiation.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SessionStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not serializer.validated_data['consent']:
            return Response(
                {'error': 'Consent is required to proceed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        today = timezone.now().date()

        # Atomic transaction with row locking on DailyTokenCounter to prevent token collisions
        with transaction.atomic():
            counter, created = DailyTokenCounter.objects.select_for_update().get_or_create(
                date=today,
                defaults={'last_token': 0}
            )
            counter.last_token += 1
            counter.save()
            token = counter.last_token

            session = PatientSession.objects.create(
                language=serializer.validated_data['language'],
                consent_given=True,
                token_number=token,
                status='active',
            )

        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)



# Symptom Submission API View

class SymptomSubmitView(APIView):
    """
    POST /api/symptoms/ — Submit chief complaints and body regions for an active session.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SymptomInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data['session_id']
        session, error_response = get_active_session_or_response(session_id)
        if error_response:
            return error_response

        session.chief_complaints = serializer.validated_data.get('complaints', [])
        session.selected_body_regions = serializer.validated_data.get('body_regions', [])
        session.save()

        # Generate initial LLM question based on symptoms
        try:
            from .utils.llm import build_system_prompt, call_llm

            system_prompt = build_system_prompt(session.language)
            symptom_text = ', '.join(session.chief_complaints + session.selected_body_regions)

            # Log user symptom selection
            ConversationLog.objects.create(
                session=session,
                role='user',
                content=f"My symptoms: {symptom_text}",
                input_type='button'
            )

            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f"Patient reports these symptoms: {symptom_text}. Ask ONE follow-up question."}
            ]

            response_text = call_llm(messages)
            ConversationLog.objects.create(
                session=session,
                role='assistant',
                content=response_text
            )

            return Response({
                'session_id': str(session.id),
                'question': response_text,
                'symptoms_recorded': session.chief_complaints,
                'regions_recorded': session.selected_body_regions,
            })
        except Exception as e:
            logger.error(f"LLM error in SymptomSubmitView: {e}", exc_info=True)
            fallback = "Thank you. Can you tell me how long you have been experiencing these symptoms?"
            ConversationLog.objects.create(
                session=session, role='assistant', content=fallback
            )
            return Response({
                'session_id': str(session.id),
                'question': fallback,
                'symptoms_recorded': session.chief_complaints,
                'regions_recorded': session.selected_body_regions,
            })


# Chat API View

class ChatView(APIView):
    """
    POST /api/chat/ — Send a message and get LLM response for an active session.
    """
    permission_classes = [AllowAny]
    throttle_classes = [HeavyAIThrottle, HeavyAIAnonThrottle]

    def post(self, request):
        serializer = ChatInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data['session_id']
        session, error_response = get_active_session_or_response(session_id)
        if error_response:
            return error_response

        # Save user message
        ConversationLog.objects.create(
            session=session,
            role='user',
            content=serializer.validated_data['message'],
            input_type=serializer.validated_data['input_type']
        )

        try:
            from .utils.llm import build_system_prompt, call_llm, detect_red_flags

            # Build conversation history
            system_prompt = build_system_prompt(session.language)
            history = ConversationLog.objects.filter(session=session).order_by('created_at')

            messages = [{'role': 'system', 'content': system_prompt}]
            for log in history:
                messages.append({'role': log.role, 'content': log.content})

            # Inject SpO2 sensor vitals into Gemini context if available
            latest_vital = session.vitals.filter(is_valid=True).order_by('-created_at').first()
            context_additions = []
            if latest_vital:
                context_additions.append(f"[VITALS: SpO2 {latest_vital.spo2}%, Heart Rate {latest_vital.heart_rate} BPM]")
            if session.selected_body_regions:
                context_additions.append(f"[POINTED_BODY_PART: {', '.join(session.selected_body_regions)}]")

            if context_additions and messages and messages[-1]['role'] == 'user':
                messages[-1]['content'] += "\n" + "\n".join(context_additions)

            response_text = call_llm(messages)

            # Check for triggers
            trigger_body_pointing = '[POINT_BODY]' in response_text
            trigger_ocr = '[SCAN_DOCUMENT]' in response_text
            display_response = response_text.replace('[POINT_BODY]', '').replace('[SCAN_DOCUMENT]', '').strip()

            # Check for emergency red flags via deterministic rules and LLM output token
            red_flags = detect_red_flags(serializer.validated_data['message'], latest_vital)
            if '[RED FLAG]' in response_text:
                red_flags.append("LLM Flagged Emergency: [RED FLAG]")

            if red_flags:
                session.red_flags = list(set(session.red_flags + red_flags))
                session.save()

            ConversationLog.objects.create(
                session=session, role='assistant', content=display_response
            )

            return Response({
                'response': display_response,
                'red_flags': red_flags,
                'trigger_body_pointing': trigger_body_pointing,
                'trigger_ocr': trigger_ocr,
                'conversation_length': history.count() + 1,
            })
        except Exception as e:
            logger.error(f"Chat LLM error: {e}", exc_info=True)
            fallback_msg = "Thank you. Could you please share more details about how you are feeling?"
            ConversationLog.objects.create(
                session=session, role='assistant', content=fallback_msg
            )
            return Response({
                'response': fallback_msg,
                'red_flags': [],
                'trigger_body_pointing': False,
                'trigger_ocr': False,
                'conversation_length': ConversationLog.objects.filter(session=session).count(),
            })


# Chat Real-Time Streaming API View (SSE)

class ChatStreamView(APIView):
    """
    POST /api/chat/stream/ — Stream Gemini LLM response token-by-token using SSE.
    """
    permission_classes = [AllowAny]
    throttle_classes = [HeavyAIThrottle, HeavyAIAnonThrottle]

    def post(self, request):
        session_id = request.data.get('session_id') if hasattr(request.data, 'get') else None
        session, error_response = get_active_session_or_response(session_id)

        user_message = request.data.get('message', 'SESSION_START') if hasattr(request.data, 'get') else 'SESSION_START'
        input_type = request.data.get('input_type', 'text') if hasattr(request.data, 'get') else 'text'

        if not user_message:
            user_message = 'SESSION_START'

        # Save user message
        ConversationLog.objects.create(
            session=session,
            role='user',
            content=user_message,
            input_type=input_type
        )

        from .utils.llm import build_system_prompt, stream_call_llm, call_llm, detect_red_flags

        system_prompt = build_system_prompt(session.language)
        history = ConversationLog.objects.filter(session=session).order_by('created_at')

        messages = [{'role': 'system', 'content': system_prompt}]
        for log in history:
            messages.append({'role': log.role, 'content': log.content})

        latest_vital = session.vitals.filter(is_valid=True).order_by('-created_at').first()
        context_additions = []
        if latest_vital:
            context_additions.append(f"[VITALS: SpO2 {latest_vital.spo2}%, Heart Rate {latest_vital.heart_rate} BPM]")
        if session.selected_body_regions:
            context_additions.append(f"[POINTED_BODY_PART: {', '.join(session.selected_body_regions)}]")

        if context_additions and messages and messages[-1]['role'] == 'user':
            messages[-1]['content'] += "\n" + "\n".join(context_additions)

        def event_stream():
            full_response = []
            try:
                for chunk in stream_call_llm(messages):
                    full_response.append(chunk)
                    data_str = json.dumps({'text': chunk})
                    yield f"data: {data_str}\n\n"
            except Exception as stream_err:
                logger.warning(f"ChatStreamView stream exception: {stream_err}. Falling back to call_llm...")
                try:
                    fallback_text = call_llm(messages)
                    full_response = [fallback_text]
                    data_str = json.dumps({'text': fallback_text})
                    yield f"data: {data_str}\n\n"
                except Exception as fallback_err:
                    logger.error(f"ChatStreamView fallback failed: {fallback_err}")
                    fallback_text = "Thank you. Could you please share more details about how you are feeling?"
                    full_response = [fallback_text]
                    data_str = json.dumps({'text': fallback_text})
                    yield f"data: {data_str}\n\n"

            final_text = "".join(full_response)
            trigger_body_pointing = '[POINT_BODY]' in final_text
            trigger_ocr = '[SCAN_DOCUMENT]' in final_text
            clean_text = final_text.replace('[POINT_BODY]', '').replace('[SCAN_DOCUMENT]', '').strip()

            # Log complete assistant message
            ConversationLog.objects.create(session=session, role='assistant', content=clean_text)

            # Check red flags
            red_flags = detect_red_flags(user_message, latest_vital)
            if '[RED FLAG]' in final_text:
                red_flags.append("LLM Flagged Emergency: [RED FLAG]")
            if red_flags:
                session.red_flags = list(set(session.red_flags + red_flags))
                session.save()

            # Final metadata frame
            meta = json.dumps({
                'done': True,
                'trigger_body_pointing': trigger_body_pointing,
                'trigger_ocr': trigger_ocr,
                'red_flags': red_flags
            })
            yield f"data: {meta}\n\n"

        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


# Body Pointing API View

class TriggerBodyPointingView(APIView):
    """
    POST /api/body-pointing/ — Launch body pointing tracker to detect patient's finger location.
    """
    permission_classes = [AllowAny]
    throttle_classes = [HeavyAIThrottle, HeavyAIAnonThrottle]

    def post(self, request):
        session_id = request.data.get('session_id')
        session, error_response = get_active_session_or_response(session_id)
        if error_response:
            return error_response

        try:
            from .utils.body_pointing_helper import execute_body_pointing
            result = execute_body_pointing(session=session)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Body pointing view execution error: {e}", exc_info=True)
            return Response(
                {'success': False, 'region': 'unknown', 'error': 'Failed to run body pointing tracker.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



# Speech-To-Text (ASR) API View

class ASRView(APIView):
    """
    POST /api/asr/ — Transcribe audio via swappable STT provider for an active session.
    """
    permission_classes = [AllowAny]
    throttle_classes = [HeavyAIThrottle, HeavyAIAnonThrottle]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({'error': 'No audio file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        language = request.data.get('language', 'en')
        session_id = request.data.get('session_id')

        # Optional active session validation
        session, error_response = get_active_session_or_response(session_id)
        if error_response:
            return error_response

        # Audio file size validation
        if audio_file.size > MAX_AUDIO_SIZE_BYTES:
            return Response(
                {'error': 'Audio recording exceeds maximum allowable limit of 15MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Infer file extension from audio file name or default to wav
        original_name = getattr(audio_file, 'name', '')
        ext = os.path.splitext(original_name)[1].lower() if original_name else '.wav'
        if not ext or ext not in ALLOWED_AUDIO_EXTENSIONS:
            ext = '.wav'


        tmp_path = None
        try:
            from .utils.stt import get_stt_provider
            provider = get_stt_provider()

            # Save uploaded audio safely to temporary storage
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                for chunk in audio_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            # Perform transcription via provider
            result = provider.transcribe(tmp_path, language)

            return Response({
                'text': result.text,
                'confidence': result.confidence,
                'provider': result.provider_name,
                'language': result.language,
            })
        except Exception as e:
            logger.error(f"ASR processing error: {e}", exc_info=True)
            return Response(
                {'error': 'Audio transcription failed. Please try speaking again or typing.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to remove temp ASR file {tmp_path}: {cleanup_err}")


# Document Scanning & Upload API View

class DocumentUploadView(APIView):
    """
    POST /api/document/ — Upload or scan a document for OCR in an active session.
    """
    permission_classes = [AllowAny]
    throttle_classes = [HeavyAIThrottle, HeavyAIAnonThrottle]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        session_id = request.data.get('session_id')
        session, error_response = get_active_session_or_response(session_id)
        if error_response:
            return error_response

        image_file = request.FILES.get('image')
        webcam_tmp_path = None

        # If no image uploaded, fetch from IP Webcam URL
        if not image_file:
            try:
                snapshot_url = f"{settings.IP_WEBCAM_URL}/photo.jpg"
                resp = requests.get(snapshot_url, timeout=5)
                resp.raise_for_status()

                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp.write(resp.content)
                    webcam_tmp_path = tmp.name

                with open(webcam_tmp_path, 'rb') as f:
                    image_file = File(f, name='webcam_scan.jpg')
                    return self._process_ocr(session, image_file)
            except Exception as e:
                logger.error(f"IP Webcam fetch failed: {e}", exc_info=True)
                return Response(
                    {'error': 'No image provided and IP Webcam scanner is unavailable.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            finally:
                if webcam_tmp_path and os.path.exists(webcam_tmp_path):
                    try:
                        os.remove(webcam_tmp_path)
                    except Exception as err:
                        logger.warning(f"Failed to delete temp webcam snapshot {webcam_tmp_path}: {err}")

        # Validate uploaded image file size & format
        if image_file.size > MAX_IMAGE_SIZE_BYTES:
            return Response(
                {'error': 'Image file exceeds maximum allowable limit of 10MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        content_type = getattr(image_file, 'content_type', '')
        if content_type and content_type.lower() not in ALLOWED_IMAGE_CONTENT_TYPES:
            return Response(
                {'error': 'Invalid image format. Supported formats are JPG, PNG, WEBP, BMP, and TIFF.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Actual image verification using Pillow to reject corrupt files or decompression bombs
        try:
            img = Image.open(image_file)
            img.verify()
            image_file.seek(0)
        except Exception as img_err:
            logger.warning(f"Invalid or corrupt image uploaded: {img_err}")
            return Response(
                {'error': 'Uploaded file is not a valid or readable image.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return self._process_ocr(session, image_file)

    def _process_ocr(self, session, image_file):
        """Internal helper to create document record and run Qwen-VL + PaddleOCR engine."""
        doc = DocumentUpload.objects.create(session=session, image=image_file)

        try:
            from .utils.ocr.qwen_paddle_engine import QwenPaddleEngine
            engine = QwenPaddleEngine()
            ocr_res = engine.process_image(doc.image.path)

            status_val = ocr_res.get('status', 'accepted')
            confidence_val = ocr_res.get('confidence', 0.90)
            extracted_text = ocr_res.get('text')
            cropped_img_url = ocr_res.get('cropped_image')

            doc.raw_ocr_text = extracted_text or "Low confidence document scan — Manual verification required."
            doc.ocr_confidence = confidence_val
            doc.ocr_provider = 'qwen_paddle_local'

            # Extract medical entities from OCR text if accepted
            if extracted_text:
                from .utils.ocr.medical_entities import extract_medical_entities
                raw_entities = extract_medical_entities(extracted_text)
                threshold = getattr(settings, 'DOCUMENT_CONFIDENCE_THRESHOLD', 0.75)

                structured_entities = {}
                for k, v in raw_entities.items():
                    structured_entities[k] = {
                        'value': v,
                        'confidence': confidence_val,
                        'provenance': 'ai_extracted',
                        'needs_review': (confidence_val < threshold)
                    }
                doc.extracted_entities = structured_entities
            doc.save()

            return Response({
                'document_id': doc.id,
                'success': True,
                'confidence': confidence_val,
                'status': status_val,
                'text': extracted_text,
                'cropped_image': cropped_img_url,
                'raw_text': doc.raw_ocr_text,
                'entities': doc.extracted_entities,
                'provider': doc.ocr_provider,
            })
        except Exception as e:
            logger.error(f"OCR execution error: {e}", exc_info=True)
            doc.raw_ocr_text = "OCR processing failed."
            doc.save()
            return Response(
                {'error': 'Failed to perform OCR scan on the document.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Clinical Summary API View (Protected for Doctors/Staff)

class SessionSummaryView(APIView):
    """
    GET/POST /api/summary/<session_id>/ — Retrieve or generate clinical summary.
    Publicly accessible for patient kiosk summary generation.
    """
    permission_classes = [AllowAny]

    def get(self, request, session_id):

        # Session lookup
        try:
            uuid_obj = uuid.UUID(str(session_id))
            session = PatientSession.objects.get(id=uuid_obj)
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            summary = session.summary
            data = ClinicalSummarySerializer(summary).data
            data['is_ai_generated'] = True
            data['doctor_reviewed'] = False
            return Response(data)
        except ClinicalSummary.DoesNotExist:
            return Response({'error': 'Summary not yet generated.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, session_id):
        # Validate active session
        session, error_response = get_active_session_or_response(session_id)
        if error_response:
            return error_response

        try:
            from .utils.llm import generate_summary
            summary_data = generate_summary(session)

            summary_text = summary_data.get('summary_text', '')
            if not summary_text.startswith('[AI-GENERATED SUMMARY]'):
                summary_text = f"[AI-GENERATED SUMMARY — PENDING DOCTOR REVIEW]\n{summary_text}"

            summary, created = ClinicalSummary.objects.update_or_create(
                session=session,
                defaults={
                    'summary_text': summary_text,
                    'structured_data': summary_data.get('structured_data', {}),
                }
            )

            session.status = 'completed'
            session.save()

            res_data = ClinicalSummarySerializer(summary).data
            res_data['is_ai_generated'] = True
            res_data['doctor_reviewed'] = False
            return Response(res_data)
        except Exception as e:
            logger.error(f"Summary generation error: {e}", exc_info=True)

            conversations = session.conversations.filter(role='user')
            basic_text = "[AI-GENERATED SUMMARY — PENDING DOCTOR REVIEW]\nPatient reported: " + "; ".join([c.content for c in conversations[:5]])

            summary, _ = ClinicalSummary.objects.update_or_create(
                session=session,
                defaults={'summary_text': basic_text, 'structured_data': {}}
            )
            session.status = 'completed'
            session.save()

            res_data = ClinicalSummarySerializer(summary).data
            res_data['is_ai_generated'] = True
            res_data['doctor_reviewed'] = False
            return Response(res_data)


# Active & All Sessions Listing API Views (Protected for Doctors)

class ActiveSessionsView(APIView):
    """
    GET /api/sessions/active/ — List active sessions for doctor dashboard.
    Protected: Requires authenticated doctor/staff user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = PatientSession.objects.filter(status='active').order_by('-created_at')
        return Response(SessionSerializer(sessions, many=True).data)


class AllSessionsView(APIView):
    """
    GET /api/sessions/ — List all sessions.
    Protected: Requires authenticated doctor/staff user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get('status', None)
        sessions = PatientSession.objects.all()
        if status_filter:
            sessions = sessions.filter(status=status_filter)
        return Response(SessionSerializer(sessions[:50], many=True).data)


# Text-to-Speech API View (Sarvam AI)

class TTSView(APIView):
    """
    POST /api/tts/ — Convert text to speech audio using Sarvam AI TTS (bulbul:v1).
    Publicly accessible for patient kiosk audio playback.
    """
    permission_classes = [AllowAny]
    throttle_classes = [HeavyAIThrottle, HeavyAIAnonThrottle]

    def post(self, request):
        serializer = TTSInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data['text']
        language = serializer.validated_data.get('language', 'en')
        speaker = serializer.validated_data.get('speaker', None)

        try:
            from .utils.tts import get_tts_provider
            provider = get_tts_provider()
            result = provider.synthesize(text=text, language_code=language, speaker=speaker)

            return Response({
                'audio_base64': result['audio_base64'],
                'language': result['language'],
                'provider': result['provider'],
            }, status=status.HTTP_200_OK)

        except ValueError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}", exc_info=True)
            return Response(
                {'error': 'Text-to-speech synthesis failed.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )





# ─────────────────────────────────────────────
# Health-Check API Views
# ─────────────────────────────────────────────

class LLMHealthView(APIView):
    """GET /api/llm/health/ — Verify Gemini LLM is reachable & report privacy mode."""
    permission_classes = [AllowAny]

    def get(self, request):
        from django.conf import settings
        from .models import AuditLog
        privacy_mode = getattr(settings, 'MEDIKIOSK_PRIVACY_MODE', False)

        try:
            from .utils.llm import call_llm
            probe = [
                {'role': 'system', 'content': 'You are a health probe.'},
                {'role': 'user', 'content': 'Reply with only the word: OK'},
            ]
            text = call_llm(probe)

            if privacy_mode:
                AuditLog.objects.create(
                    action='outbound_llm_call',
                    step='health_probe',
                    model_used=getattr(settings, 'GEMINI_MODEL', 'gemini-flash-latest'),
                    details={'probe': True, 'privacy_mode': True}
                )

            return Response({
                'status': 'ok',
                'provider': 'gemini',
                'privacy_mode': privacy_mode,
                'preview': text[:60]
            })
        except Exception as e:
            logger.error(f"LLM health-check failed: {e}", exc_info=True)
            return Response({'status': 'error', 'detail': str(e), 'privacy_mode': privacy_mode}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class TTSHealthView(APIView):
    """GET /api/tts/health/ — Verify active TTS provider (Chatterbox/Sarvam) works."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from .utils.tts import get_tts_provider
            provider = get_tts_provider()
            result = provider.synthesize(text='hello', language_code='en')
            return Response({
                'status': 'ok',
                'provider': result.get('provider', 'unknown'),
                'audio_bytes': len(result.get('audio_base64', '')) * 3 // 4,
            })
        except Exception as e:
            logger.error(f"TTS health-check failed: {e}", exc_info=True)
            return Response({'status': 'error', 'detail': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class OCRHealthView(APIView):
    """GET /api/ocr/health/ — Verify configured OCR engine loads."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from .utils.ocr import get_ocr_provider
            provider = get_ocr_provider()
            return Response({
                'status': 'ok',
                'provider': type(provider).__name__,
                'ocr_engine': 'qwen_paddle_local' if 'Qwen' in type(provider).__name__ else 'other',
            })
        except Exception as e:
            logger.error(f"OCR health-check failed: {e}", exc_info=True)
            return Response({'status': 'error', 'detail': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class SensorHealthView(APIView):
    """GET /api/sensor/health/ — Report sensor subsystem status (demo when hardware absent)."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'ok',
            'mode': 'demo',
            'demo_spo2': 98,
            'demo_heart_rate': 72,
            'demo_temperature': 36.6,
            'note': 'No physical sensor required — demo data returned.',
        })


class DemoSensorTriggerView(APIView):
    """POST /api/sensor/trigger/ — Inject synthetic vitals for a session (no hardware needed)."""
    permission_classes = [AllowAny]

    def post(self, request):
        import random
        session_id = request.data.get('session_id')
        demo_spo2 = round(random.uniform(96.0, 99.5), 1)
        demo_hr = random.randint(65, 90)
        demo_temp = round(random.uniform(36.2, 37.4), 1)

        if session_id:
            try:
                from sensors.models import VitalReading
                session, err = get_active_session_or_response(session_id)
                if not err:
                    VitalReading.objects.create(
                        session=session,
                        spo2=demo_spo2,
                        heart_rate=demo_hr,
                        temperature=demo_temp,
                        is_valid=True,
                    )
                    logger.info(f"Demo vitals injected — SpO2={demo_spo2}, HR={demo_hr}")
            except Exception as e:
                logger.warning(f"Demo sensor DB write skipped: {e}")

        return Response({
            'status': 'ok',
            'mode': 'demo',
            'spo2': demo_spo2,
            'heart_rate': demo_hr,
            'temperature': demo_temp,
            'note': 'Synthetic vitals injected — no physical sensor required.',
        }, status=status.HTTP_201_CREATED)

class LLMHealthView(APIView):
    """GET /api/llm/health/ — Verify Gemini LLM is reachable."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from .utils.llm import call_llm
            probe = [
                {'role': 'system', 'content': 'You are a health probe.'},
                {'role': 'user', 'content': 'Reply with only the word: OK'},
            ]
            text = call_llm(probe)
            return Response({'status': 'ok', 'provider': 'gemini', 'preview': text[:60]})
        except Exception as e:
            logger.error(f"LLM health-check failed: {e}", exc_info=True)
            return Response({'status': 'error', 'detail': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class TTSHealthView(APIView):
    """GET /api/tts/health/ — Verify active TTS provider (Chatterbox/Sarvam) works."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from .utils.tts import get_tts_provider
            provider = get_tts_provider()
            result = provider.synthesize(text='hello', language_code='en')
            return Response({
                'status': 'ok',
                'provider': result.get('provider', 'unknown'),
                'audio_bytes': len(result.get('audio_base64', '')) * 3 // 4,
            })
        except Exception as e:
            logger.error(f"TTS health-check failed: {e}", exc_info=True)
            return Response({'status': 'error', 'detail': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class OCRHealthView(APIView):
    """GET /api/ocr/health/ — Verify configured OCR engine loads."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from .utils.ocr import get_ocr_provider
            provider = get_ocr_provider()
            return Response({
                'status': 'ok',
                'provider': type(provider).__name__,
                'ocr_engine': 'qwen_paddle_local' if 'Qwen' in type(provider).__name__ else 'other',
            })
        except Exception as e:
            logger.error(f"OCR health-check failed: {e}", exc_info=True)
            return Response({'status': 'error', 'detail': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class SensorHealthView(APIView):
    """GET /api/sensor/health/ — Report sensor subsystem status (demo when hardware absent)."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'ok',
            'mode': 'demo',
            'demo_spo2': 98,
            'demo_heart_rate': 72,
            'demo_temperature': 36.6,
            'note': 'No physical sensor required — demo data returned.',
        })


class DemoSensorTriggerView(APIView):
    """POST /api/sensor/trigger/ — Inject synthetic vitals for a session (no hardware needed)."""
    permission_classes = [AllowAny]

    def post(self, request):
        import random
        session_id = request.data.get('session_id')
        demo_spo2 = round(random.uniform(96.0, 99.5), 1)
        demo_hr = random.randint(65, 90)
        demo_temp = round(random.uniform(36.2, 37.4), 1)

        if session_id:
            try:
                from sensors.models import VitalReading
                session, err = get_active_session_or_response(session_id)
                if not err:
                    VitalReading.objects.create(
                        session=session,
                        spo2=demo_spo2,
                        heart_rate=demo_hr,
                        temperature=demo_temp,
                        is_valid=True,
                    )
                    logger.info(f"Demo vitals injected — SpO2={demo_spo2}, HR={demo_hr}")
            except Exception as e:
                logger.warning(f"Demo sensor DB write skipped: {e}")

        return Response({
            'status': 'ok',
            'mode': 'demo',
            'spo2': demo_spo2,
            'heart_rate': demo_hr,
            'temperature': demo_temp,
            'note': 'Synthetic vitals injected — no physical sensor required.',
        }, status=status.HTTP_201_CREATED)


class LatestVitalsView(APIView):
    """GET /api/vitals/latest/<session_id>/ — Fetch latest recorded vitals for active session."""
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            from sensors.models import VitalReading
            session, err = get_active_session_or_response(session_id)
            latest = VitalReading.objects.filter(session=session, is_valid=True).order_by('-created_at').first()
            if latest:
                return Response({
                    'spo2': latest.spo2,
                    'heart_rate': latest.heart_rate,
                    'temperature': latest.temperature,
                    'is_valid': latest.is_valid,
                    'created_at': latest.created_at
                })
            else:
                return Response({'spo2': 98.0, 'heart_rate': 72, 'temperature': 36.6, 'is_demo': True})
        except Exception as e:
            return Response({'spo2': 98.0, 'heart_rate': 72, 'temperature': 36.6, 'is_demo': True})


# =====================================================================
# V1: STRUCTURED HISTORY & REGIONS ENDPOINTS
# =====================================================================

from .models import StructuredHistory, MedicalDocument, DocumentField
from .serializers import (
    StructuredHistorySerializer, MedicalDocumentSerializer,
    DocumentFieldSerializer
)

class StructuredHistoryView(APIView):
    """
    GET /api/session/<session_id>/history/ — Fetch structured clinical history.
    """
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            session = PatientSession.objects.get(id=uuid.UUID(str(session_id)))
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        history, _ = StructuredHistory.objects.get_or_create(session=session)
        return Response(StructuredHistorySerializer(history).data)


class StructuredHistoryUpdateView(APIView):
    """
    POST /api/session/<session_id>/history/update/ — Update structured clinical history.
    """
    permission_classes = [AllowAny]

    def post(self, request, session_id):
        try:
            session = PatientSession.objects.get(id=uuid.UUID(str(session_id)))
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        history, _ = StructuredHistory.objects.get_or_create(session=session)

        # Update fields if provided
        for field in ['chief_complaint', 'hpi', 'past_medical_history', 'medications', 'allergies', 'family_history', 'social_history', 'missing_fields']:
            if field in request.data:
                setattr(history, field, request.data[field])

        history.save()
        return Response(StructuredHistorySerializer(history).data, status=status.HTTP_200_OK)


CANONICAL_BODY_REGIONS = [
    {"id": "head", "name": "Head / Forehead", "category": "cranial"},
    {"id": "neck", "name": "Neck / Throat", "category": "cranial"},
    {"id": "chest", "name": "Chest / Thorax", "category": "thoracic"},
    {"id": "left_arm", "name": "Left Arm", "category": "upper_limb"},
    {"id": "right_arm", "name": "Right Arm", "category": "upper_limb"},
    {"id": "abdomen", "name": "Abdomen / Stomach", "category": "abdominal"},
    {"id": "pelvis", "name": "Pelvis / Groin", "category": "pelvic"},
    {"id": "left_leg", "name": "Left Leg / Knee", "category": "lower_limb"},
    {"id": "right_leg", "name": "Right Leg / Knee", "category": "lower_limb"},
    {"id": "back", "name": "Spine / Upper-Lower Back", "category": "posterior"},
]

class BodyPointingRegionsView(APIView):
    """
    GET /api/body-pointing/regions/ — Canonical body region list.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'regions': CANONICAL_BODY_REGIONS,
            'count': len(CANONICAL_BODY_REGIONS)
        })


# =====================================================================
# V2: DOCUMENT INTELLIGENCE APIS
# =====================================================================

class DocumentUploadPipelineView(APIView):
    """
    POST /api/document/upload/ — Multipart upload for medical slip with automated pipeline processing.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        session_id = request.data.get('session_id')
        document_type = request.data.get('document_type', 'prescription')
        image_file = request.FILES.get('image')

        if not session_id or not image_file:
            return Response(
                {'error': 'session_id and image file are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = PatientSession.objects.get(id=uuid.UUID(str(session_id)))
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        med_doc = MedicalDocument.objects.create(
            session=session,
            document_type=document_type,
            image_file=image_file,
            status='uploaded'
        )

        # Run Document Pipeline
        from .services.document_pipeline import run_document_pipeline
        processed_doc = run_document_pipeline(med_doc)

        return Response(MedicalDocumentSerializer(processed_doc).data, status=status.HTTP_201_CREATED)


class MedicalDocumentDetailView(APIView):
    """
    GET /api/document/<document_id>/ — Fetch single medical document details.
    """
    permission_classes = [AllowAny]

    def get(self, request, document_id):
        try:
            doc = MedicalDocument.objects.get(id=uuid.UUID(str(document_id)))
        except (ValueError, TypeError, MedicalDocument.DoesNotExist):
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(MedicalDocumentSerializer(doc).data)


class DocumentFieldsListView(APIView):
    """
    GET /api/document/<document_id>/fields/ — List all extracted fields for a document.
    """
    permission_classes = [AllowAny]

    def get(self, request, document_id):
        try:
            doc = MedicalDocument.objects.get(id=uuid.UUID(str(document_id)))
        except (ValueError, TypeError, MedicalDocument.DoesNotExist):
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        fields = doc.fields.all()
        return Response(DocumentFieldSerializer(fields, many=True).data)


class VerifyDocumentFieldView(APIView):
    """
    POST /api/document/<document_id>/field/<field_id>/verify/ — Doctor verifies/confirms an extracted field.
    """
    permission_classes = [AllowAny]

    def post(self, request, document_id, field_id):
        from django.utils import timezone
        try:
            field = DocumentField.objects.get(id=field_id, document__id=uuid.UUID(str(document_id)))
        except (ValueError, TypeError, DocumentField.DoesNotExist):
            return Response({'error': 'Document field not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Update field value if doctor edited it
        new_val = request.data.get('field_value')
        if new_val:
            field.field_value = new_val

        field.needs_review = False
        field.provenance = 'clinician_confirmed'
        field.verified_at = timezone.now()

        # Link doctor profile if authenticated
        if request.user.is_authenticated and hasattr(request.user, 'doctor_profile'):
            field.verified_by = request.user.doctor_profile

        field.save()

        # Update parent document status if all fields verified
        doc = field.document
        if not doc.fields.filter(needs_review=True).exists():
            doc.status = 'verified'
            doc.save()

        return Response(DocumentFieldSerializer(field).data, status=status.HTTP_200_OK)


class RejectDocumentFieldView(APIView):
    """
    POST /api/document/<document_id>/field/<field_id>/reject/ — Doctor rejects an extracted field.
    """
    permission_classes = [AllowAny]

    def post(self, request, document_id, field_id):
        try:
            field = DocumentField.objects.get(id=field_id, document__id=uuid.UUID(str(document_id)))
        except (ValueError, TypeError, DocumentField.DoesNotExist):
            return Response({'error': 'Document field not found.'}, status=status.HTTP_404_NOT_FOUND)

        rejection_reason = request.data.get('rejection_reason', 'Rejected by clinician')
        field.needs_review = False
        field.rejection_reason = rejection_reason
        field.save()

        return Response(DocumentFieldSerializer(field).data, status=status.HTTP_200_OK)


class SessionMedicalDocumentsView(APIView):
    """
    GET /api/document/session/<session_id>/ — Fetch all medical documents for a patient session.
    """
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            session = PatientSession.objects.get(id=uuid.UUID(str(session_id)))
        except (ValueError, TypeError, PatientSession.DoesNotExist):
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        docs = session.medical_documents.all()
        return Response(MedicalDocumentSerializer(docs, many=True).data)

