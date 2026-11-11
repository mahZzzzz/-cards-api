
from pathlib import Path
import subprocess
import tempfile

import pymupdf

TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
PDF_PATH = "sample_prds/sample.pdf"

extracted_pages = []

with pymupdf.open(PDF_PATH) as document:
    for page_number, page in enumerate(document, start=1):
        # Render each PDF page as a high-resolution image
        pix = page.get_pixmap(dpi=300, alpha=False)

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "page.png"
            image_path.write_bytes(pix.tobytes("png"))

            result = subprocess.run(
                [
                    TESSERACT,
                    str(image_path),
                    "stdout",
                    "-l",
                    "fas",
                    "--psm",
                    "6",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )

            extracted_pages.append(
                f"PAGE {page_number}\n\n{result.stdout.strip()}"
            )

        print(f"Page {page_number} processed")

Path("extracted_ocr_psm6.txt").write_text(
    "\n\n" + ("=" * 40) + "\n\n".join(extracted_pages),
    encoding="utf-8",
)

print("OCR completed!")
print("Text saved to extracted_ocr.txt")
