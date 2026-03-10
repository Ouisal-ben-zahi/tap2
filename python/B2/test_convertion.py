# Test de la conversion HTML -> PDF uniquement (sans génération).
# Lancer depuis backend/ :  python B2/test_convertion.py   ou   python -m B2.test_convertion
import os
import sys

_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from B2.agent_portfolio import convert_html_to_pdf

# Chemin vers ton fichier HTML one-page (à adapter)
HTML_FILE = "/Users/ryanelakhdari/Downloads/portfolio_d51b0200-3265-42d8-9fb1-34ea2ca3b1e0_one-page_fr (5).html"
CANDIDATE_ID = 1
CANDIDATE_UUID = "34ec44bf-fe2a-49f2-9d9b-734af1b22fa1"

if not os.path.isfile(HTML_FILE):
    print(f"Fichier introuvable: {HTML_FILE}")
    sys.exit(1)

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html_content = f.read()

pdf_ok, pdf_url, pdf_err = convert_html_to_pdf(
    html_content,
    CANDIDATE_ID,
    CANDIDATE_UUID,
    base_url="http://localhost:5002",
    pdf_page_format="one-page"
)
if pdf_ok:
    print("PDF généré:", pdf_url)
else:
    print("Erreur PDF:", pdf_err)