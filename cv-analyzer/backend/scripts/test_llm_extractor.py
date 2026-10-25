"""Test the LLM extractor in isolation — no endpoint involved."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_extractor import extract_text
from llm_extractor import extract_cv_data
from exceptions import LlmExtractionError

# Read CV text
pdf_path = Path("Mohamed_Feroz_CV_FDE_AI_Architect.pdf")
with open(pdf_path, "rb") as f:
    cv_text = extract_text(f)

print(f"CV text: {len(cv_text)} chars")
print("Calling Gemini...")

try:
    result = extract_cv_data(cv_text)
except LlmExtractionError as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

print(f"[PASS] Gemini returned valid CVAnalysis")
print(f"  technicalSkills: {len(result.technicalSkills)} items")
print(f"  experience: {len(result.experience)} items")
print(f"  projects: {len(result.projects)} items")
print()
print("First 3 skills:")
for skill in result.technicalSkills[:3]:
    print(f"  - {skill.title}: {skill.description[:80]}...")
print()
print("First 2 experiences:")
for exp in result.experience[:2]:
    print(f"  - {exp.title}: {exp.description[:80]}...")