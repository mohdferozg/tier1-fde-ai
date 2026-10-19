"""FastAPI backend for the CV Analyzer.

Day 0 (Foundation): scaffold with health check + Pydantic models
Day 1: (module work, no endpoint changes)
Day 2: POST /cv-analysis now accepts a PDF upload and returns extracted text
"""

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from pdf_extractor import extract_text
from exceptions import PdfExtractionError

app = FastAPI()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    name: str


class CVItem(BaseModel):
    title: str
    description: str


class CVAnalysis(BaseModel):
    technicalSkills: list[CVItem]
    experience: list[CVItem]
    projects: list[CVItem]


class CVAnalysisResponse(BaseModel):
    """Response from POST /cv-analysis (Day 2 version: extracted text only)."""
    filename: str
    text_length: int
    text: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Tier-1 FDE AI backend is running"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    return {"message": f"Hello {request.name}"}


@app.post("/cv-analysis", response_model=CVAnalysisResponse)
async def cv_analysis(file: UploadFile = File(...)):
    """
    Accept a PDF upload and return the extracted text.

    Day 2: returns raw extracted text (no LLM yet).
    Day 3: this endpoint will call Gemini and return a validated CVAnalysis.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Expected a .pdf file, got: {file.filename!r}",
        )

    try:
        text = extract_text(file.file)
    except PdfExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while processing PDF: {e}",
        )

    return CVAnalysisResponse(
        filename=file.filename,
        text_length=len(text),
        text=text,
    )