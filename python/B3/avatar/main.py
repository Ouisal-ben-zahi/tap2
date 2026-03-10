"""
AI Interview Playbook Avatar - Backend API
==========================================

A FastAPI backend that provides text-to-speech generation for an AI-powered
interview preparation coach avatar.

Main endpoints:
- POST /api/interview-playbook: Generate speech from interview playbook text
- GET /api/health: Health check endpoint
- GET /audio/{filename}: Serve generated audio files

Ethical considerations:
- This system generates synthetic voice only (no real person imitation)
- No biometric data processing
- Clearly labeled as AI-generated content
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models import (
    InterviewPlaybookRequest, 
    AudioResponse, 
    HealthResponse, 
    ErrorResponse
)
from .services import get_tts_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initializes services on startup and cleans up on shutdown.
    """
    # Startup: Ensure audio output directory exists
    audio_dir = Path(settings.audio_output_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🎤 AI Interview Avatar Backend starting...")
    print(f"📢 TTS Provider: {settings.tts_provider.value}")
    print(f"🌍 Default Language: {settings.default_language.value}")
    print(f"📁 Audio Output: {audio_dir.absolute()}")
    
    yield
    
    # Shutdown: Clean up if needed
    print("👋 AI Interview Avatar Backend shutting down...")


# Initialize FastAPI application
app = FastAPI(
    title="AI Interview Playbook Avatar API",
    description="""
    Backend API for the AI Interview Playbook Avatar.
    
    This service provides:
    - Text-to-Speech generation for interview preparation content
    - Support for French (default) and English languages
    - Multiple TTS provider support (ElevenLabs, Azure, Google)
    
    **Ethical Notice**: This system generates fully synthetic voices.
    No real person imitation or biometric processing is performed.
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================
# API Endpoints
# ============================================

@app.get(
    "/api/health", 
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check endpoint"
)
async def health_check():
    """
    Check if the API is running and which TTS provider is active.
    Useful for monitoring and load balancer health checks.
    """
    try:
        tts_service = get_tts_service()
        return HealthResponse(
            status="healthy",
            tts_provider=tts_service.provider_name,
            version="1.0.0"
        )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            tts_provider="unavailable",
            version="1.0.0"
        )


@app.post(
    "/api/interview-playbook",
    response_model=AudioResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    tags=["Interview Playbook"],
    summary="Generate speech from interview playbook text"
)
async def generate_interview_playbook(
    request: InterviewPlaybookRequest,
    http_request: Request
):
    """
    Generate AI-synthesized speech from interview playbook text.
    
    This endpoint accepts text content that the AI avatar should speak,
    generates audio using the configured TTS provider, and returns
    a URL to access the generated audio file.
    
    **Parameters:**
    - `text`: The content for the avatar to speak (1-5000 characters)
    - `language`: Language code (fr-FR for French, en-US for English)
    - `sections`: Optional structured sections for multi-part content
    
    **Returns:**
    - `audio_url`: URL path to the generated audio file
    - `audio_duration_ms`: Estimated duration in milliseconds
    - `language`: The language used for generation
    - `text_length`: Character count of input text
    
    **Example usage:**
    ```json
    {
        "text": "Bonjour, bienvenue dans votre préparation d'entretien.",
        "language": "fr-FR"
    }
    ```
    """
    try:
        tts_service = get_tts_service()
        
        # If sections are provided, concatenate them in order
        if request.sections:
            sorted_sections = sorted(request.sections, key=lambda s: s.order)
            text = " ".join([s.content for s in sorted_sections])
        else:
            text = request.text
        
        # Generate audio
        filename, full_path, duration_ms = await tts_service.generate_audio(
            text=text,
            language=request.language
        )
        
        # Build audio URL (relative to API base)
        audio_url = f"/audio/{filename}"
        
        return AudioResponse(
            audio_url=audio_url,
            audio_duration_ms=duration_ms,
            language=request.language,
            text_length=len(text)
        )
        
    except ValueError as e:
        # TTS misconfiguration (e.g. missing API key) → 503 Service Unavailable
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate speech: {str(e)}"
        )


@app.get(
    "/audio/{filename}",
    tags=["Audio"],
    summary="Retrieve generated audio file"
)
async def get_audio(filename: str):
    """
    Serve a generated audio file.
    
    Audio files are stored temporarily and may be cleaned up periodically.
    The URL returned by /api/interview-playbook should be used promptly.
    """
    audio_path = Path(settings.audio_output_dir) / filename
    
    if not audio_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Audio file not found"
        )
    
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=filename,
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff"
        }
    )


@app.get(
    "/",
    tags=["System"],
    summary="API root - returns basic info"
)
async def root():
    """
    API root endpoint providing basic information about the service.
    """
    return {
        "service": "AI Interview Playbook Avatar API",
        "version": "1.0.0",
        "status": "running",
        "notice": "This service generates fully synthetic AI voices. No real person imitation.",
        "endpoints": {
            "health": "/api/health",
            "generate_speech": "/api/interview-playbook",
            "audio_files": "/audio/{filename}"
        }
    }


# ============================================
# Error Handlers
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request failed",
            "detail": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unexpected errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again."
        }
    )


# ============================================
# Run with Uvicorn (for development)
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
