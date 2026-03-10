"""
Flask blueprint for the AI Interview Playbook Avatar API.
Exposes the same endpoints as the FastAPI avatar backend so the main Flask app
can serve TTS for the avatar without a separate server.
"""

import asyncio
from pathlib import Path

from flask import Blueprint, request, jsonify, send_file

# Lazy imports to avoid loading TTS/config until first use
def _get_tts_service():
    from B3.avatar.services import get_tts_service
    return get_tts_service()

def _get_avatar_settings():
    from B3.avatar.config import settings
    return settings

avatar_api_bp = Blueprint("avatar_api", __name__)


@avatar_api_bp.get("/api/health")
def avatar_health():
    """Health check for the avatar TTS service."""
    try:
        tts = _get_tts_service()
        return jsonify({
            "status": "healthy",
            "tts_provider": tts.provider_name,
            "version": "1.0.0"
        })
    except Exception:
        return jsonify({
            "status": "degraded",
            "tts_provider": "unavailable",
            "version": "1.0.0"
        })


@avatar_api_bp.post("/api/interview-playbook")
def avatar_interview_playbook():
    """Generate speech from interview playbook text (same contract as FastAPI avatar)."""
    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Request failed", "detail": "text is required"}), 400

    lang_str = data.get("language", "fr-FR")
    try:
        from B3.avatar.config import SupportedLanguage
        lang = SupportedLanguage(lang_str)
    except (ValueError, TypeError):
        from B3.avatar.config import SupportedLanguage
        lang = SupportedLanguage.FRENCH

    sections = data.get("sections")
    if sections and isinstance(sections, list):
        sorted_sections = sorted(sections, key=lambda s: s.get("order", 0))
        text = " ".join((s.get("content") or "") for s in sorted_sections).strip()
        if not text:
            return jsonify({"error": "Request failed", "detail": "text is required"}), 400

    try:
        tts = _get_tts_service()
        filename, full_path, duration_ms = asyncio.run(
            tts.generate_audio(text=text, language=lang)
        )
        audio_url = f"/audio/{filename}"
        return jsonify({
            "audio_url": audio_url,
            "audio_duration_ms": duration_ms,
            "language": lang_str,
            "text_length": len(text)
        })
    except ValueError as e:
        return jsonify({"error": "Request failed", "detail": str(e)}), 503
    except Exception as e:
        return jsonify({"error": "Request failed", "detail": str(e)}), 500


@avatar_api_bp.get("/audio/<path:filename>")
def avatar_audio(filename):
    """Serve a generated audio file."""
    if ".." in filename or filename.startswith("/"):
        return "", 404
    settings = _get_avatar_settings()
    audio_path = Path(settings.audio_output_dir) / filename
    if not audio_path.is_file():
        return "", 404
    return send_file(
        str(audio_path),
        mimetype="audio/mpeg",
        as_attachment=False,
        max_age=3600
    )
