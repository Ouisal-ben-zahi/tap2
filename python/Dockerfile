# Dockerfile pour le backend Python TAP
FROM python:3.10-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Outils de compilation (nécessaires pour TTS, simpleaudio, webrtcvad)
    build-essential \
    gcc \
    g++ \
    make \
    # Tesseract OCR et langues
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    # Poppler pour pdf2image
    poppler-utils \
    # LibreOffice pour conversion DOCX -> PDF
    libreoffice \
    libreoffice-writer \
    # Fonts pour WeasyPrint et LibreOffice
    fonts-liberation \
    fonts-dejavu \
    fonts-liberation2 \
    fonts-noto \
    # Dépendances pour Playwright
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    # Dépendances audio pour simpleaudio
    portaudio19-dev \
    python3-dev \
    # ffmpeg requis par Whisper pour charger les fichiers audio (webm, etc.)
    ffmpeg \
    # Utilitaires
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Installer Rust via rustup (plus fiable que via apt)
# Note: Rust est nécessaire pour sudachipy, mais peut être ignoré si non utilisé
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    export PATH="$HOME/.cargo/bin:$PATH" && \
    rustup default stable || echo "⚠️  Rust installation failed, sudachipy may not work"

# Installation de Playwright et Chromium
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# Créer le répertoire de travail
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer les dépendances supplémentaires pour TTS et Whisper
# Ajouter Rust au PATH pour les packages qui en ont besoin
ENV PATH="/root/.cargo/bin:${PATH}"

# Installer les packages de base sans upgrader numpy en 2.x
RUN pip install --no-cache-dir \
    "numpy>=1.24.0,<2.0.0" \
    scipy \
    openai-whisper \
    sounddevice

# Installer TTS (nécessaire pour l'entretien vocal)
# TTS nécessite une compilation, peut prendre du temps
RUN pip install --no-cache-dir TTS || (echo "⚠️  TTS installation failed" && exit 0)

# Installer simpleaudio et webrtcvad (nécessaires pour l'entretien)
RUN pip install --no-cache-dir simpleaudio || (echo "⚠️  simpleaudio installation failed" && exit 0)
RUN pip install --no-cache-dir webrtcvad || (echo "⚠️  webrtcvad installation failed" && exit 0)

# Copier le code de l'application backend
COPY backend/ .

# Copier le template portfolio depuis le frontend (pour génération PDF)
# Créer la structure de répertoires d'abord
RUN mkdir -p /app/frontend/src
# Copier le dossier portfolio html en utilisant la syntaxe avec crochets pour gérer les espaces
COPY ["frontend/src/portfolio html", "/app/frontend/src/portfolio html"]

# Créer les dossiers nécessaires
RUN mkdir -p uploads generated corrected_cv corrected_cv_pdf

# Exposer le port Flask
EXPOSE 5002

# Commande par défaut (peut être surchargée dans docker-compose)
CMD ["python", "app.py"]
