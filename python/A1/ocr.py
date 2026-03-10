from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class OCRResult:
    text: str
    engine: str
    pages: Optional[int] = None
    warnings: Optional[List[str]] = None


def _normalize_whitespace(text: str) -> str:
    text = text or ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Tuple[str, List[str]]:
    """
    Deterministic PDF text extraction using pypdf (no OCR).
    Returns (text, warnings).
    """
    warnings: List[str] = []
    try:
        from pypdf import PdfReader
    except Exception as e:
        raise RuntimeError("Missing dependency: pypdf is required to parse PDF text.") from e

    try:
        import io

        reader = PdfReader(io.BytesIO(pdf_bytes))
        texts: List[str] = []
        for i, page in enumerate(reader.pages):
            try:
                t = page.extract_text() or ""
                if t:
                    texts.append(f"\n\n--- PAGE {i+1} ---\n{t}")
            except Exception:
                warnings.append(f"Failed to extract text from page {i+1}.")
        return _normalize_whitespace("\n".join(texts)), warnings
    except Exception as e:
        raise RuntimeError(f"PDF parsing failed: {e}") from e


def ocr_image_bytes(image_bytes: bytes, lang: str = "fra+eng") -> OCRResult:
    """
    OCR an image using Tesseract via pytesseract.
    """
    try:
        import pytesseract
    except Exception as e:
        raise RuntimeError("Missing dependency: pytesseract is required for OCR.") from e
    try:
        from PIL import Image
    except Exception as e:
        raise RuntimeError("Missing dependency: Pillow is required for OCR.") from e

    import io

    img = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(img, lang=lang)
    return OCRResult(text=_normalize_whitespace(text), engine=f"tesseract:{lang}", pages=1, warnings=None)


def ocr_pdf_bytes(pdf_bytes: bytes, lang: str = "fra+eng", max_pages: int = 15) -> OCRResult:
    """
    OCR a PDF by converting pages to images (pdf2image) then Tesseract.
    Production note:
    - pdf2image requires Poppler installed in the runtime.
    """
    warnings: List[str] = []
    try:
        from pdf2image import convert_from_bytes
    except Exception as e:
        raise RuntimeError("Missing dependency: pdf2image is required for PDF OCR.") from e

    try:
        import pytesseract
    except Exception as e:
        raise RuntimeError("Missing dependency: pytesseract is required for OCR.") from e

    try:
        pages = convert_from_bytes(pdf_bytes, dpi=250)
    except Exception as e:
        raise RuntimeError(
            "PDF->image conversion failed (pdf2image). Ensure Poppler is installed. "
            f"Details: {e}"
        ) from e

    if max_pages and len(pages) > max_pages:
        warnings.append(f"PDF has {len(pages)} pages; OCR limited to first {max_pages} pages.")
        pages = pages[:max_pages]

    texts: List[str] = []
    for i, img in enumerate(pages):
        try:
            t = pytesseract.image_to_string(img, lang=lang)
            texts.append(f"\n\n--- PAGE {i+1} (OCR) ---\n{t}")
        except Exception:
            warnings.append(f"OCR failed on page {i+1}.")

    return OCRResult(
        text=_normalize_whitespace("\n".join(texts)),
        engine=f"pdf2image+tesseract:{lang}",
        pages=len(pages),
        warnings=warnings or None,
    )


def extract_text_from_image_bytes(image_bytes: bytes, lang: str = "fra+eng") -> Tuple[str, List[str]]:
    """
    Deterministic image text extraction.

    For images, there is no embedded selectable text, so this is a thin wrapper around OCR.
    Returns (text, warnings) to match `extract_text_from_pdf_bytes`.
    """
    res = ocr_image_bytes(image_bytes, lang=lang)
    return res.text, res.warnings or []


def should_fallback_to_ocr(extracted_text: str, min_chars: int = 300) -> bool:
    """
    Heuristic: if PDF text extraction yields too little usable content, fall back to OCR.
    """
    t = (extracted_text or "").strip()
    if len(t) < min_chars:
        return True
    # If text is mostly punctuation/whitespace, likely scanned
    alpha = sum(1 for c in t if c.isalnum())
    return (alpha / max(len(t), 1)) < 0.2


