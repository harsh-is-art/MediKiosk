# Module & Testing Framework Imports

import uuid
from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from .models import PatientSession, ClinicalSummary


# Kiosk API Test Cases

class KioskAPITests(APITestCase):

    # Session Creation Tests

    def test_start_session(self):
        url = reverse('kiosk:session-start')
        data = {'language': 'en', 'consent': True}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['token_number'], 1)

    def test_start_session_no_consent(self):
        url = reverse('kiosk:session-start')
        data = {'language': 'en', 'consent': False}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Session Status Validation Tests

    def test_nonexistent_session_returns_404(self):
        fake_uuid = str(uuid.uuid4())
        url = reverse('kiosk:symptoms')
        data = {'session_id': fake_uuid, 'complaints': ['fever']}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_completed_session_returns_400(self):
        session = PatientSession.objects.create(status='completed', language='en', consent_given=True)
        url = reverse('kiosk:symptoms')
        data = {'session_id': str(session.id), 'complaints': ['fever']}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no longer active', response.data['error'])

    def test_abandoned_session_returns_400(self):
        session = PatientSession.objects.create(status='abandoned', language='en', consent_given=True)
        url = reverse('kiosk:chat')
        data = {'session_id': str(session.id), 'message': 'Hello'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no longer active', response.data['error'])

    # Symptom & Chat Submission Tests

    @patch('kiosk.utils.llm.call_llm')
    def test_submit_symptoms(self, mock_llm):
        mock_llm.return_value = "How long have you had this fever?"
        session = PatientSession.objects.create(status='active', language='en', consent_given=True, token_number=1)
        url = reverse('kiosk:symptoms')
        data = {
            'session_id': str(session.id),
            'complaints': ['fever', 'headache'],
            'body_regions': ['head']
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question'], "How long have you had this fever?")
        session.refresh_from_db()
        self.assertEqual(session.chief_complaints, ['fever', 'headache'])

    @patch('kiosk.utils.llm.call_llm')
    def test_chat_view(self, mock_llm):
        mock_llm.return_value = "Please lie down and seek medical assistance immediately."
        session = PatientSession.objects.create(status='active', language='en', consent_given=True, token_number=1)
        url = reverse('kiosk:chat')
        data = {
            'session_id': str(session.id),
            'message': 'I have severe chest pain',
            'input_type': 'text'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['response'], "Please lie down and seek medical assistance immediately.")
        self.assertTrue(len(response.data['red_flags']) > 0)

    # ASR & Document Upload Tests

    @patch('kiosk.utils.stt.base.STTProvider.transcribe')
    @patch('kiosk.utils.stt.get_stt_provider')
    def test_asr_view_cleanup_and_validation(self, mock_get_provider, mock_transcribe):
        from kiosk.utils.stt.base import TranscriptionResult
        mock_provider = mock_get_provider.return_value
        mock_provider.transcribe.return_value = TranscriptionResult('hello', 0.9, 'en', 'mock')

        session = PatientSession.objects.create(status='active', language='en', consent_given=True)
        url = reverse('kiosk:asr')
        audio = SimpleUploadedFile("speech.webm", b"dummy audio content", content_type="audio/webm")
        response = self.client.post(url, {'audio': audio, 'session_id': str(session.id)}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'hello')

    def test_document_upload_invalid_type(self):
        session = PatientSession.objects.create(status='active', language='en', consent_given=True)
        url = reverse('kiosk:document-upload')
        invalid_file = SimpleUploadedFile("doc.pdf", b"pdf content", content_type="application/pdf")
        response = self.client.post(url, {'image': invalid_file, 'session_id': str(session.id)}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid image format', response.data['error'])

    # AI Provider & Confi. Tests

    def test_openrouter_missing_key_raises_configuration_error(self):
        from kiosk.utils.llm import call_llm
        from django.core.exceptions import ImproperlyConfigured
        with patch('django.conf.settings.OPENROUTER_API_KEY', ''):
            with patch('os.getenv', return_value=''):
                with self.assertRaises(ImproperlyConfigured):
                    call_llm([{'role': 'user', 'content': 'hi'}])

    def test_google_credentials_missing_raises_configuration_error(self):
        from kiosk.utils.stt.google_stt import GoogleSTTProvider
        from django.core.exceptions import ImproperlyConfigured
        with patch('django.conf.settings.GOOGLE_APPLICATION_CREDENTIALS', '/invalid/path.json'):
            with patch('os.path.exists', return_value=False):
                with self.assertRaises(ImproperlyConfigured):
                    GoogleSTTProvider()

    def test_invalid_stt_provider_raises_configuration_error(self):
        from kiosk.utils.stt import get_stt_provider
        from django.core.exceptions import ImproperlyConfigured
        with patch('django.conf.settings.STT_PROVIDER', 'invalid_stt'):
            with self.assertRaises(ImproperlyConfigured):
                get_stt_provider()

    def test_multilingual_red_flags_detection(self):
        from kiosk.utils.llm import detect_red_flags
        # Hindi
        flags_hi = detect_red_flags("saans nahi aal rahi hai aur seene mein dard hai")
        self.assertTrue(len(flags_hi) >= 2)
        # Tamil
        flags_ta = detect_red_flags("nenju vali irukkirathu")
        self.assertTrue(len(flags_ta) >= 1)
        # Marathi
        flags_mr = detect_red_flags("chatit dukhne khup aahe")
        self.assertTrue(len(flags_mr) >= 1)

    def test_anonymous_active_sessions_view_rejected(self):
        url = reverse('kiosk:active-sessions')
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_authenticated_active_sessions_view_allowed(self):
        user = User.objects.create_user(username='doc_user', password='password123')
        self.client.force_authenticate(user=user)
        PatientSession.objects.create(status='active', language='en', consent_given=True, token_number=1)
        url = reverse('kiosk:active-sessions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_anonymous_summary_access_rejected(self):
        session = PatientSession.objects.create(status='active', language='en', consent_given=True)
        url = reverse('kiosk:summary', kwargs={'session_id': str(session.id)})
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_authenticated_summary_access_allowed(self):
        user = User.objects.create_user(username='doc_summary', password='password123')
        self.client.force_authenticate(user=user)
        session = PatientSession.objects.create(status='active', language='en', consent_given=True)
        ClinicalSummary.objects.create(session=session, summary_text='Test summary')
        url = reverse('kiosk:summary', kwargs={'session_id': str(session.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('is_ai_generated', response.data)


    def test_asr_oversized_audio_rejected(self):
        session = PatientSession.objects.create(status='active', language='en', consent_given=True)
        url = reverse('kiosk:asr')
        # Create fake audio > 15MB
        huge_content = b"0" * (16 * 1024 * 1024)
        audio = SimpleUploadedFile("huge.wav", huge_content, content_type="audio/wav")
        response = self.client.post(url, {'audio': audio, 'session_id': str(session.id)}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('exceeds maximum allowable limit', response.data['error'])

    def test_concurrent_session_token_generation(self):
        url = reverse('kiosk:session-start')
        data = {'language': 'en', 'consent': True}
        res1 = self.client.post(url, data, format='json')
        res2 = self.client.post(url, data, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(res1.data['token_number'], res2.data['token_number'])

    def test_health_check_endpoint(self):
        url = reverse('health-check')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')

    # Sarvam AI STT & TTS Tests

    @patch('requests.post')
    def test_sarvam_stt_provider_transcribe(self, mock_post):
        import tempfile
        from kiosk.utils.stt.sarvam import SarvamSTTProvider

        mock_response = patch('requests.Response').start()
        mock_response.status_code = 200
        mock_response.json.return_value = {"transcript": "मुझे बुखार है"}
        mock_post.return_value = mock_response

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(b"RIFF....WAVEfmt ....data....")
            tmp_path = tmp.name

        try:
            with patch('django.conf.settings.SARVAM_API_KEY', 'test-sarvam-key'):
                provider = SarvamSTTProvider()
                result = provider.transcribe(tmp_path, 'hi')
                self.assertEqual(result.text, "मुझे बुखार है")
                self.assertEqual(result.provider_name, "sarvam_asr")
                self.assertEqual(result.language, "hi")
        finally:
            import os
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @patch('requests.post')
    def test_sarvam_tts_provider_synthesize(self, mock_post):
        from kiosk.utils.tts.sarvam_tts import SarvamTTSProvider

        mock_response = patch('requests.Response').start()
        mock_response.status_code = 200
        mock_response.json.return_value = {"audios": ["bWFrZWF1ZGlv"]}
        mock_post.return_value = mock_response

        with patch('django.conf.settings.SARVAM_API_KEY', 'test-sarvam-key'):
            provider = SarvamTTSProvider()
            result = provider.synthesize("नमस्ते", 'hi')
            self.assertEqual(result['audio_base64'], "bWFrZWF1ZGlv")
            self.assertEqual(result['provider'], "sarvam_tts")

    @patch('kiosk.utils.tts.sarvam_tts.SarvamTTSProvider.synthesize')
    def test_tts_view_success(self, mock_synth):
        mock_synth.return_value = {
            'audio_base64': 'mockbase64audio',
            'language': 'en-IN',
            'provider': 'sarvam_tts'
        }
        url = reverse('kiosk:tts')
        data = {'text': 'Hello patient, welcome to MediKiosk', 'language': 'en'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['audio_base64'], 'mockbase64audio')
        self.assertEqual(response.data['provider'], 'sarvam_tts')

    def test_tts_view_missing_text(self):
        url = reverse('kiosk:tts')
        data = {'language': 'en'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sarvam_streaming_stt_client_url_and_params(self):
        from kiosk.utils.stt.sarvam_streaming import SarvamStreamingSTTClient
        with patch('django.conf.settings.SARVAM_API_KEY', 'test-key'):
            client = SarvamStreamingSTTClient(
                model="saaras:v4",
                mode="transcribe",
                language_code="hi",
                high_vad_sensitivity=True,
                vad_signals=True
            )
            ws_url = client.build_ws_url()
            self.assertIn("wss://api.sarvam.ai/speech-to-text/ws", ws_url)
            self.assertIn("model=saaras:v4", ws_url)
            self.assertIn("mode=transcribe", ws_url)
            self.assertIn("language_code=hi-IN", ws_url)







