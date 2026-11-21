
from pathlib import Path
import fitz
import subprocess
import tempfile


def extract_pdf_sections(pdf_path: str) -> list[dict]:
    """Extract text from a PDF, preserving page references."""

    path = Path(pdf_path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported")

    sections = []

    with fitz.open(path) as document:
        if document.is_encrypted:
            raise ValueError("Password-protected PDF is not supported")

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text", sort=False).strip()

            if not text:
                continue

            sections.append({
                "heading": f"Page {page_number}",
                "page": page_number,
                "text": text
            })

    if not sections:
        raise ValueError(
            "No extractable text found. "
            "This PDF may require OCR."
        )

    return sections


def extract_pdf_sections_ocr(pdf_path: str) -> list[dict]:
    """Extract Persian PDF text using Tesseract OCR."""

    tesseract_exe = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    path = Path(pdf_path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported")

    sections = []

    with fitz.open(path) as document:
        if document.is_encrypted:
            raise ValueError("Password-protected PDF is not supported")

        for page_number, page in enumerate(document, start=1):
            pix = page.get_pixmap(dpi=300, alpha=False)

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "page.png"
                image_path.write_bytes(pix.tobytes("png"))

                result = subprocess.run(
                    [
                        tesseract_exe,
                        str(image_path),
                        "stdout",
                        "-l",
                        "fas",
                        "--psm",
                        "3",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=True,
                    timeout=120,
                )

            text = result.stdout.strip()

            if text:
                sections.append({
                    "heading": f"Page {page_number}",
                    "page": page_number,
                    "text": text,
                })

    if not sections:
        raise ValueError("OCR could not extract text from PDF")

    return sections




