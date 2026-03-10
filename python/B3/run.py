"""
Development server runner for the AI Interview Playbook Avatar backend.
Run this file directly to start the FastAPI server with hot reload.
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("🚀 Starting AI Interview Playbook Avatar Backend...")
    print(f"📍 Server: http://{settings.host}:{settings.port}")
    print(f"📖 API Docs: http://localhost:{settings.port}/docs")
    print()
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )
