from pathlib import Path

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    if suffix in {".png", ".jpg", ".jpeg"}:
        return pytesseract.image_to_string(Image.open(path))
    return ""


def _extract_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    if text.strip():
        return text
    images = convert_from_path(str(path))
    return "\n".join(pytesseract.image_to_string(image) for image in images)
