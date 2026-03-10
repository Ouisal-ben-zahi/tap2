"""
Text-to-Speech service abstraction layer.
Supports multiple TTS providers: ElevenLabs, Azure, and Google Cloud TTS.
"""

import os
import uuid
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import httpx

from ..config import settings, TTSProvider, SupportedLanguage


class BaseTTSService(ABC):
    """Abstract base class for TTS services."""
    
    @abstractmethod
    async def generate_speech(
        self, 
        text: str, 
        language: SupportedLanguage,
        output_path: str
    ) -> Tuple[str, Optional[int]]:
        """
        Generate speech from text.
        
        Args:
            text: The text to convert to speech
            language: Target language for TTS
            output_path: Path where audio file will be saved
            
        Returns:
            Tuple of (file_path, duration_ms)
        """
        pass


class ElevenLabsTTSService(BaseTTSService):
    """
    ElevenLabs TTS implementation.
    High-quality, natural-sounding voices with excellent French support.
    """
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    # Voice IDs for different languages (voix masculines par défaut)
    VOICE_MAP = {
        SupportedLanguage.FRENCH: "pNInz6obpgDQGcFmaJgB",   # Adam - masculin, FR/EN
        SupportedLanguage.ENGLISH: "pNInz6obpgDQGcFmaJgB",   # Adam
        SupportedLanguage.ENGLISH_UK: "pNInz6obpgDQGcFmaJgB",  # Adam
    }
    
    def __init__(self, api_key: str, default_voice_id: Optional[str] = None):
        self.api_key = api_key
        self.default_voice_id = default_voice_id
        
    async def generate_speech(
        self, 
        text: str, 
        language: SupportedLanguage,
        output_path: str
    ) -> Tuple[str, Optional[int]]:
        """Generate speech using ElevenLabs API."""
        
        # Select appropriate voice for language
        voice_id = self.default_voice_id or self.VOICE_MAP.get(
            language, 
            self.VOICE_MAP[SupportedLanguage.FRENCH]
        )
        
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Voice settings optimized for professional coaching tone
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",  # Best for French
            "voice_settings": {
                "stability": 0.75,  # Balanced stability
                "similarity_boost": 0.75,  # Natural sound
                "style": 0.5,  # Moderate expressiveness
                "use_speaker_boost": True
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            # Save audio to file
            with open(output_path, "wb") as f:
                f.write(response.content)
        
        # Estimate duration (rough calculation: ~150 words per minute)
        word_count = len(text.split())
        estimated_duration_ms = int((word_count / 150) * 60 * 1000)
        
        return output_path, estimated_duration_ms


class AzureTTSService(BaseTTSService):
    """
    Azure Cognitive Services TTS implementation.
    Enterprise-grade with excellent language support.
    """
    
    # Neural voices for different languages
    VOICE_MAP = {
        SupportedLanguage.FRENCH: "fr-FR-DeniseNeural",  # French female
        SupportedLanguage.ENGLISH: "en-US-JennyNeural",  # US English female
        SupportedLanguage.ENGLISH_UK: "en-GB-SoniaNeural",  # UK English female
    }
    
    def __init__(self, speech_key: str, speech_region: str):
        self.speech_key = speech_key
        self.speech_region = speech_region
        
    async def generate_speech(
        self, 
        text: str, 
        language: SupportedLanguage,
        output_path: str
    ) -> Tuple[str, Optional[int]]:
        """Generate speech using Azure TTS API."""
        
        voice_name = self.VOICE_MAP.get(
            language, 
            self.VOICE_MAP[SupportedLanguage.FRENCH]
        )
        
        # Construct SSML for better control
        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{language.value}'>
            <voice name='{voice_name}'>
                <prosody rate='0%' pitch='0%'>
                    {text}
                </prosody>
            </voice>
        </speak>
        """
        
        url = f"https://{self.speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.speech_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, content=ssml, headers=headers)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
        
        # Estimate duration
        word_count = len(text.split())
        estimated_duration_ms = int((word_count / 150) * 60 * 1000)
        
        return output_path, estimated_duration_ms


class GoogleTTSService(BaseTTSService):
    """
    Google Cloud TTS implementation.
    High-quality WaveNet voices with natural intonation.
    """
    
    # WaveNet voices for different languages
    VOICE_MAP = {
        SupportedLanguage.FRENCH: ("fr-FR", "fr-FR-Wavenet-C"),  # French female
        SupportedLanguage.ENGLISH: ("en-US", "en-US-Wavenet-F"),  # US English female
        SupportedLanguage.ENGLISH_UK: ("en-GB", "en-GB-Wavenet-F"),  # UK English female
    }
    
    def __init__(self):
        # Google client will use GOOGLE_APPLICATION_CREDENTIALS env var
        pass
        
    async def generate_speech(
        self, 
        text: str, 
        language: SupportedLanguage,
        output_path: str
    ) -> Tuple[str, Optional[int]]:
        """Generate speech using Google Cloud TTS API."""
        
        # Import here to avoid issues if Google SDK not installed
        from google.cloud import texttospeech
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        def _generate():
            client = texttospeech.TextToSpeechClient()
            
            lang_code, voice_name = self.VOICE_MAP.get(
                language, 
                self.VOICE_MAP[SupportedLanguage.FRENCH]
            )
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                name=voice_name
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0
            )
            
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            with open(output_path, "wb") as f:
                f.write(response.audio_content)
            
            return output_path
        
        await loop.run_in_executor(None, _generate)
        
        # Estimate duration
        word_count = len(text.split())
        estimated_duration_ms = int((word_count / 150) * 60 * 1000)
        
        return output_path, estimated_duration_ms


class CoquiTTSService(BaseTTSService):
    """
    Coqui TTS implementation.
    Open-source, runs locally, no API costs or privacy concerns.
    High-quality neural TTS with good French support.
    """

    # Model mapping for different languages
    MODEL_MAP = {
        SupportedLanguage.FRENCH: "tts_models/fr/css10/vits",  # High-quality French model
        SupportedLanguage.ENGLISH: "tts_models/en/ljspeech/tacotron2-DDC_ph",  # English model
        SupportedLanguage.ENGLISH_UK: "tts_models/en/ljspeech/tacotron2-DDC_ph",  # Use same English model for UK
    }

    def __init__(self, model_path: str = "", speaker_id: str = "0"):
        self.model_path = model_path
        self.speaker_id = speaker_id

    async def generate_speech(
        self,
        text: str,
        language: SupportedLanguage,
        output_path: str
    ) -> Tuple[str, Optional[int]]:
        """Generate speech using Coqui TTS."""

        # Import here to avoid issues if TTS not installed
        try:
            from TTS.api import TTS
        except ImportError as e:
            raise ValueError(
                "Coqui TTS n'est pas installé ou PyTorch est manquant. "
                "Installez avec: pip install torch TTS. "
                "Ou utilisez un autre fournisseur: TTS_PROVIDER=elevenlabs avec ELEVENLABS_API_KEY."
            ) from e

        # Select appropriate model for language
        model_name = self.model_path or self.MODEL_MAP.get(
            language,
            self.MODEL_MAP[SupportedLanguage.FRENCH]
        )

        # Run TTS generation in executor to avoid blocking
        loop = asyncio.get_event_loop()

        def _generate():
            try:
                # Initialize TTS with the specified model (requires PyTorch)
                tts = TTS(model_name).to("cpu")  # Use CPU for compatibility

                # Generate speech
                tts.tts_to_file(
                    text=text,
                    file_path=output_path,
                    speaker=self.speaker_id if hasattr(tts, 'speakers') and tts.speakers else None
                )

                return output_path
            except Exception as e:
                err_msg = str(e).lower()
                if "pytorch" in err_msg or "torch" in err_msg or "model" in err_msg:
                    raise ValueError(
                        "Coqui TTS nécessite PyTorch. Installez avec: pip install torch. "
                        "Puis réessayez ou utilisez TTS_PROVIDER=elevenlabs avec ELEVENLABS_API_KEY."
                    ) from e
                raise

        await loop.run_in_executor(None, _generate)

        # Estimate duration (rough calculation: ~150 words per minute)
        word_count = len(text.split())
        estimated_duration_ms = int((word_count / 150) * 60 * 1000)

        return output_path, estimated_duration_ms


class TTSService:
    """
    Main TTS service that delegates to the configured provider.
    Acts as a factory and facade for TTS operations.
    """
    
    def __init__(self):
        self.provider = settings.tts_provider
        self.output_dir = Path(settings.audio_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the appropriate service based on config
        self._service = self._create_service()
    
    def _create_service(self) -> BaseTTSService:
        """Create the appropriate TTS service based on configuration."""
        
        if self.provider == TTSProvider.ELEVENLABS:
            if not settings.elevenlabs_api_key:
                raise ValueError("ELEVENLABS_API_KEY is required for ElevenLabs TTS")
            return ElevenLabsTTSService(
                api_key=settings.elevenlabs_api_key,
                default_voice_id=settings.elevenlabs_voice_id
            )
            
        elif self.provider == TTSProvider.AZURE:
            if not settings.azure_speech_key:
                raise ValueError("AZURE_SPEECH_KEY is required for Azure TTS")
            return AzureTTSService(
                speech_key=settings.azure_speech_key,
                speech_region=settings.azure_speech_region
            )
            
        elif self.provider == TTSProvider.GOOGLE:
            return GoogleTTSService()

        elif self.provider == TTSProvider.COQUI:
            return CoquiTTSService(
                model_path=settings.coqui_model_path,
                speaker_id=settings.coqui_speaker_id
            )

        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")
    
    async def generate_audio(
        self, 
        text: str, 
        language: SupportedLanguage = SupportedLanguage.FRENCH
    ) -> Tuple[str, str, Optional[int]]:
        """
        Generate audio from text.
        
        Args:
            text: Text to convert to speech
            language: Target language
            
        Returns:
            Tuple of (filename, full_path, duration_ms)
        """
        # Generate unique filename
        filename = f"playbook_{uuid.uuid4().hex[:12]}.mp3"
        output_path = str(self.output_dir / filename)
        
        # Generate speech
        _, duration_ms = await self._service.generate_speech(
            text=text,
            language=language,
            output_path=output_path
        )
        
        return filename, output_path, duration_ms
    
    @property
    def provider_name(self) -> str:
        """Return the name of the active TTS provider."""
        return self.provider.value


# Singleton instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get or create the TTS service singleton."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
