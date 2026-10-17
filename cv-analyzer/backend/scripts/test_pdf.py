"""Diagnostic: extract text from the sample CV PDF and inspect the result."""
import sys
from pathlib import Path

# Add the backend/ directory (parent of scripts/) to Python's path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_extractor import extract_text

pdf_path = Path("Mohamed_Feroz_CV_FDE_AI_Architect.pdf")

print(f"File exists: {pdf_path.exists()}")
print(f"File size: {pdf_path.stat().st_size} bytes")
print("-" * 60)

with open(pdf_path, "rb") as f:
    text = extract_text(f)

print(f"Extracted length: {len(text)} characters")
print(f"First 500 chars:\n{text[:500]}")
print("-" * 60)
print(f"Last 300 chars:\n{text[-300:]}")