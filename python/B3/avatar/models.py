"""
Pydantic models for API request/response validation.
Defines the data structures for the Interview Playbook API.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class Language(str, Enum):
    """Supported languages for the avatar."""
    FRENCH = "fr-FR"
    ENGLISH = "en-US"
    ENGLISH_UK = "en-GB"


class InterviewSection(BaseModel):
    """
    A section of the interview playbook.
    Each section contains content that the avatar will speak.
    """
    title: str = Field(..., description="Section title (e.g., 'Introduction', 'Conseils')")
    content: str = Field(..., description="Text content for the avatar to speak")
    order: int = Field(default=0, description="Order in which to present sections")


class InterviewPlaybookRequest(BaseModel):
    """
    Request model for the /interview-playbook endpoint.
    Contains the text that the avatar should speak.
    """
    text: str = Field(
        ..., 
        description="The text content for the avatar to speak",
        min_length=1,
        max_length=5000
    )
    language: Language = Field(
        default=Language.FRENCH,
        description="Language for text-to-speech generation"
    )
    sections: Optional[List[InterviewSection]] = Field(
        default=None,
        description="Optional structured sections for multi-part playbooks"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Bonjour et bienvenue dans votre session de préparation à l'entretien. Je suis votre coach IA et je vais vous guider à travers les étapes clés pour réussir votre entretien.",
                "language": "fr-FR",
                "sections": [
                    {
                        "title": "Introduction",
                        "content": "Commençons par les bases de la préparation.",
                        "order": 1
                    }
                ]
            }
        }


class AudioResponse(BaseModel):
    """
    Response model containing the generated audio information.
    """
    audio_url: str = Field(..., description="URL to access the generated audio file")
    audio_duration_ms: Optional[int] = Field(
        default=None, 
        description="Duration of the audio in milliseconds"
    )
    language: Language = Field(..., description="Language used for generation")
    text_length: int = Field(..., description="Length of the input text in characters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "audio_url": "/audio/playbook_abc123.mp3",
                "audio_duration_ms": 15000,
                "language": "fr-FR",
                "text_length": 150
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(default="healthy")
    tts_provider: str = Field(..., description="Active TTS provider")
    version: str = Field(default="1.0.0")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
