# Configuration Gunicorn pour la production
import multiprocessing
import os

# Nombre de workers (2 * CPU cores + 1)
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# Adresse et port
bind = f"0.0.0.0:{os.getenv('PORT', '5002')}"

# Timeout pour les requêtes longues (OCR, génération de CV, etc.)
timeout = 300  # 5 minutes

# Worker class
worker_class = "sync"

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv('LOG_LEVEL', 'info')

# Process naming
proc_name = "tap_backend"

# Worker timeout
keepalive = 5

# Max requests per worker (pour éviter les fuites mémoire)
max_requests = 1000
max_requests_jitter = 50

# Preload app pour économiser la mémoire
preload_app = True
