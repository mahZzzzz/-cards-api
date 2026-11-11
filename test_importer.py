
from pathlib import Path
from importer import extract_pdf_sections

sections = extract_pdf_sections("sample_prds/sample_english.pdf")

output = []

for section in sections:
    output.append(
        f"PAGE {section['page']}\n\n{section['text']}"
    )

Path("extracted_text.txt").write_text(
    "\n\n" + "=" * 40 + "\n\n".join(output),
    encoding="utf-8"
)

print("Extracted pages:", len(sections))
print("Text saved to extracted_text.txt")

