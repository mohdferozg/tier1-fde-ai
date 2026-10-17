"""Break-test: verify each failure mode raises the correct exception."""
import sys
from pathlib import Path
from io import BytesIO

# Add backend/ to path so we can import pdf_extractor
sys.path.insert(0, str(Path(__file__).parent.parent))

from pypdf import PdfWriter
from pdf_extractor import extract_text
from exceptions import PdfExtractionError


def expect_raise(label, func, expected_exception, message_contains=None):
    """Run func; verify it raises expected_exception with the right message."""
    try:
        func()
    except expected_exception as e:
        if message_contains and message_contains.lower() not in str(e).lower():
            print(f"[FAIL] {label}: raised {type(e).__name__} but message missing '{message_contains}': {e}")
            return False
        print(f"[PASS] {label}: raised {type(e).__name__}: {e}")
        return True
    except Exception as e:
        print(f"[FAIL] {label}: expected {expected_exception.__name__}, got {type(e).__name__}: {e}")
        return False
    else:
        print(f"[FAIL] {label}: no exception raised")
        return False


print("=" * 60)
print("Break test 1: file-like object that isn't a PDF")
print("=" * 60)
expect_raise(
    "Non-PDF bytes",
    lambda: extract_text(BytesIO(b"This is not a PDF, just plain text.")),
    PdfExtractionError,
    "not a valid pdf",
)

print()
print("=" * 60)
print("Break test 2: empty PDF (valid structure, zero pages)")
print("=" * 60)
empty_pdf = BytesIO()
writer = PdfWriter()
writer.write(empty_pdf)
empty_pdf.seek(0)
expect_raise(
    "Empty PDF",
    lambda: extract_text(empty_pdf),
    PdfExtractionError,
    "no extractable text",
)

print()
print("=" * 60)
print("Break test 3: PDF with blank page (no text)")
print("=" * 60)
blank_pdf = BytesIO()
writer = PdfWriter()
writer.add_blank_page(width=612, height=792)
writer.write(blank_pdf)
blank_pdf.seek(0)
expect_raise(
    "Blank page PDF",
    lambda: extract_text(blank_pdf),
    PdfExtractionError,
    "no extractable text",
)

print()
print("=" * 60)
print("Break test 4: encrypted PDF")
print("=" * 60)
encrypted_pdf = BytesIO()
writer = PdfWriter()
writer.add_blank_page(width=612, height=792)
writer.encrypt(user_password="secret", owner_password="owner")
writer.write(encrypted_pdf)
encrypted_pdf.seek(0)
expect_raise(
    "Encrypted PDF",
    lambda: extract_text(encrypted_pdf),
    PdfExtractionError,
    "encrypted",
)

print()
print("=" * 60)
print("Sanity check: happy path still works")
print("=" * 60)
cv_path = Path("Mohamed_Feroz_CV_FDE_AI_Architect.pdf")
if cv_path.exists():
    with open(cv_path, "rb") as f:
        text = extract_text(f)
    print(f"[PASS] CV extracted: {len(text)} chars")
else:
    print("[SKIP] CV file not found")

print()
print("=" * 60)
print("Break tests complete.")
print("=" * 60)