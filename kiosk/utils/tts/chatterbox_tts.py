import sys
import os
from pathlib import Path
import torch
import base64
import io
import wave

# Add Chatterbox source directory to Python path
current_path = Path(__file__).resolve()
project_root = current_path.parents[4] if len(current_path.parents) > 4 else current_path.parent
for parent in current_path.parents:
    if (parent / "chatterbox-master").exists():
        project_root = parent
        break

chatterbox_src = project_root / "chatterbox-master" / "chatterbox-master" / "src"
if not chatterbox_src.exists():
    chatterbox_src = project_root / "chatterbox-master" / "src"

if str(chatterbox_src) not in sys.path:
    sys.path.append(str(chatterbox_src))

# Import the Chatterbox TTS class
try:
    from chatterbox.tts import ChatterboxTTS
except Exception as import_err:
    raise ImportError(f"Failed to import Chatterbox TTS: {import_err}")


class ChatterboxTTSProvider:
    """Thin wrapper around the Chatterbox TTS model.

    The interface mirrors the SarvamTTSProvider so that the rest of the codebase
    can call ``synthesize(text, language_code, speaker)`` and receive a dict with
    ``audio_base64``, ``language`` and ``provider`` keys.
    """

    def __init__(self, device: str = None):
        # Determine device – prefer CUDA if available
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        # Load the pretrained Chatterbox model (will download weights if missing)
        self.engine = ChatterboxTTS.from_pretrained(self.device)

    def synthesize(self, text: str, language_code: str = "en", speaker: str = None) -> dict:
        """Generate speech audio from ``text``.

        Parameters
        ----------
        text: str
            The utterance to be spoken.
        language_code: str, optional
            Retained for API compatibility; Chatterbox does not require a language
            parameter because the model is multilingual.
        speaker: str, optional
            Ignored – Chatterbox uses a single voice.

        Returns
        -------
        dict
            ``{"audio_base64": <base64-wav>, "language": language_code,
            "provider": "chatterbox_tts"}``
        """
        # Generate a waveform tensor (shape: [1, samples])
        wav_tensor = self.engine.generate(text)
        wav_np = wav_tensor.squeeze(0).cpu().numpy()

        # Convert numpy waveform to 16‑bit PCM WAV bytes
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16‑bit
            wf.setframerate(16000)
            wf.writeframes((wav_np * 32767).astype("int16").tobytes())
        audio_bytes = buf.getvalue()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return {
            "audio_base64": audio_b64,
            "language": language_code,
            "provider": "chatterbox_tts",
        }
