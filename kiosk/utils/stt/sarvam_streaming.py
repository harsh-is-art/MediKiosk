"""
Sarvam AI Real-Time WebSocket Streaming STT Client.

Provides streaming audio transcription over WebSockets (wss://api.sarvam.ai/speech-to-text/ws)
with near-zero latency, VAD signals (START_SPEECH / END_SPEECH), and multiple modes:
- transcribe
- translate
- verbatim
- translit
- codemix
"""


# Python & Standard Library Imports

import os
import json
import base64
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from django.conf import settings

try:
    import websockets
except ImportError:
    websockets = None

logger = logging.getLogger(__name__)


# Sarvam AI Language Mapping for WebSockets

SARVAM_WS_LANG_MAP = {
    'en': 'en-IN',
    'hi': 'hi-IN',
    'ta': 'ta-IN',
    'bn': 'bn-IN',
    'mr': 'mr-IN',
    'te': 'te-IN',
    'kn': 'kn-IN',
    'ml': 'ml-IN',
    'gu': 'gu-IN',
    'pa': 'pa-IN',
    'od': 'or-IN',
}


# Sarvam Streaming STT Client Definition

class SarvamStreamingSTTClient:
    """
    Manages a real-time WebSocket connection to Sarvam AI Streaming STT API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "saaras:v4",
        mode: str = "transcribe",
        language_code: str = "en",
        sample_rate: int = 16000,
        high_vad_sensitivity: bool = True,
        vad_signals: bool = True,
    ):
        if websockets is None:
            raise ImportError(
                "The 'websockets' package is required for streaming STT. "
                "Install it using: pip install websockets"
            )

        self.api_key = api_key or getattr(settings, 'SARVAM_API_KEY', '') or os.getenv('SARVAM_API_KEY', '')
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY not configured. Set it in your .env file.")

        self.model = model or getattr(settings, 'SARVAM_STT_MODEL', 'saaras:v4')
        self.mode = mode
        self.language_code = SARVAM_WS_LANG_MAP.get(
            language_code,
            f"{language_code}-IN" if '-' not in language_code else language_code
        )
        self.sample_rate = sample_rate
        self.high_vad_sensitivity = high_vad_sensitivity
        self.vad_signals = vad_signals

        self.websocket = None
        self._is_connected = False

    def build_ws_url(self) -> str:
        """Construct Sarvam WS URL with query parameters."""
        params = [
            f"model={self.model}",
            f"mode={self.mode}",
            f"language_code={self.language_code}",
            f"sample_rate={self.sample_rate}",
            f"high_vad_sensitivity={'true' if self.high_vad_sensitivity else 'false'}",
            f"vad_signals={'true' if self.vad_signals else 'false'}",
        ]
        query_string = "&".join(params)
        return f"wss://api.sarvam.ai/speech-to-text/ws?{query_string}"

    async def connect(self):
        """Establish WebSocket connection with Sarvam AI."""
        ws_url = self.build_ws_url()
        headers = {
            "api-subscription-key": self.api_key
        }

        try:
            self.websocket = await websockets.connect(ws_url, extra_headers=headers)
            self._is_connected = True
            logger.info(f"Connected to Sarvam Streaming STT WebSocket ({self.language_code}, mode={self.mode})")
        except Exception as e:
            logger.error(f"Failed to connect to Sarvam Streaming STT WebSocket: {e}", exc_info=True)
            self._is_connected = False
            raise

    async def send_audio_chunk(self, audio_data: bytes, encoding: str = "audio/wav"):
        """
        Send a chunk of audio bytes to the streaming WebSocket.

        Args:
            audio_data: Raw WAV or PCM audio bytes
            encoding: Audio encoding format ('audio/wav' or PCM format)
        """
        if not self._is_connected or not self.websocket:
            raise RuntimeError("WebSocket is not connected. Call connect() first.")

        b64_audio = base64.b64encode(audio_data).decode('utf-8')
        payload = {
            "audio": b64_audio,
            "encoding": encoding,
            "sample_rate": self.sample_rate,
        }

        await self.websocket.send(json.dumps(payload))

    async def flush(self):
        """Force immediate processing of buffered audio."""
        if self._is_connected and self.websocket:
            await self.websocket.send(json.dumps({"action": "flush"}))

    async def receive_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yield real-time events and transcripts as they arrive from Sarvam AI.
        """
        if not self._is_connected or not self.websocket:
            raise RuntimeError("WebSocket is not connected.")

        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    yield data
                except json.JSONDecodeError:
                    yield {"type": "raw", "data": message}
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Sarvam WebSocket connection closed: {e}")
            self._is_connected = False
        except Exception as e:
            logger.error(f"Error receiving from Sarvam WebSocket: {e}")
            self._is_connected = False
            raise

    async def close(self):
        """Close the WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self._is_connected = False
            logger.info("Closed Sarvam Streaming STT WebSocket.")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
