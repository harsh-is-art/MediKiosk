
class GoogleSTTProvider(STTProvider):
    """Wraps Google Cloud Speech-to-Text API."""

    def __init__(self):
        cred_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', '') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
        if not cred_path or not os.path.exists(cred_path):
            logger.error(f"Google Cloud credential file not found at: '{cred_path}'")
            raise ImproperlyConfigured(
                f"GOOGLE_APPLICATION_CREDENTIALS path is invalid or file does not exist: '{cred_path}'. "
                "Please configure a valid service account JSON file path in your .env file."
            )

        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cred_path

        try:
            from google.cloud import speech
            self.client = speech.SpeechClient()
            self.speech = speech
        except Exception as e:
            logger.error(f"Failed to initialize Google SpeechClient: {e}")
            raise ImproperlyConfigured(f"Failed to initialize Google SpeechClient: {e}")

    def transcribe(self, audio_path: str, language_code: str = 'en') -> TranscriptionResult:
        google_lang = GOOGLE_LANG_MAP.get(language_code, f'{language_code}-IN')

        with open(audio_path, 'rb') as f:
            audio_content = f.read()

        # Determine audio encoding dynamically from file extension or content signature
        ext = os.path.splitext(audio_path)[1].lower()
        if ext == '.webm':
            encoding = self.speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
            sample_rate = 48000
        elif ext == '.mp3':
            encoding = self.speech.RecognitionConfig.AudioEncoding.MP3
            sample_rate = 16000
        elif ext == '.flac':
            encoding = self.speech.RecognitionConfig.AudioEncoding.FLAC
            sample_rate = 16000
        else:
            encoding = self.speech.RecognitionConfig.AudioEncoding.LINEAR16
            sample_rate = 16000

        audio = self.speech.RecognitionAudio(content=audio_content)
        config = self.speech.RecognitionConfig(
            encoding=encoding,
            sample_rate_hertz=sample_rate,
            language_code=google_lang,
            enable_automatic_punctuation=True,
        )

        response = self.client.recognize(config=config, audio=audio)


        if not response.results:
            return TranscriptionResult(
                text='', confidence=0.0,
                language=language_code, provider_name='google_cloud_stt'
            )

        best = response.results[0].alternatives[0]
        return TranscriptionResult(
            text=best.transcript,
            confidence=best.confidence,
            language=language_code,
            provider_name='google_cloud_stt'
        )

