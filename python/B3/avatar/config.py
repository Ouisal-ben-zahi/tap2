"""
Configuration management for the AI Interview Playbook Avatar backend.
Loads settings from environment variables with sensible defaults.
"""

import os
from enum import Enum
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class TTSProvider(str, Enum):
    """Supported Text-to-Speech providers."""
    ELEVENLABS = "elevenlabs"
    AZURE = "azure"
    GOOGLE = "google"
    COQUI = "coqui"


class SupportedLanguage(str, Enum):
    """Supported languages for TTS."""
    FRENCH = "fr-FR"
    ENGLISH = "en-US"
    ENGLISH_UK = "en-GB"


class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    
    # TTS Provider Configuration
    tts_provider: TTSProvider = TTSProvider(
        os.getenv("TTS_PROVIDER", "elevenlabs")
    )
    
    # ElevenLabs Settings
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv(
        "ELEVENLABS_VOICE_ID", 
        "pNInz6obpgDQGcFmaJgB"  # Adam - voix masculine, multilingue (FR/EN)
    )
    
    # Azure TTS Settings
    azure_speech_key: str = os.getenv("AZURE_SPEECH_KEY", "")
    azure_speech_region: str = os.getenv("AZURE_SPEECH_REGION", "westeurope")
    
    # Google TTS Settings
    google_credentials_path: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    # Coqui TTS Settings
    coqui_model_path: str = os.getenv("COQUI_MODEL_PATH", "")
    coqui_speaker_id: str = os.getenv("COQUI_SPEAKER_ID", "0")
    
    # Server Settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    cors_origins: List[str] = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:5173"
    ).split(",")
    
    # Audio Settings
    default_language: SupportedLanguage = SupportedLanguage(
        os.getenv("DEFAULT_LANGUAGE", "fr-FR")
    )
    audio_output_format: str = os.getenv("AUDIO_OUTPUT_FORMAT", "mp3")
    
    # Audio output directory
    audio_output_dir: str = os.getenv("AUDIO_OUTPUT_DIR", "audio_output")


# Global settings instance
settings = Settings()
