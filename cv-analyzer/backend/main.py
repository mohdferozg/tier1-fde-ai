"""FastAPI backend for the CV Analyzer.

Day 0 (Foundation): scaffold with health check + Pydantic models
Day 1: (module work, no endpoint changes)
Day 2: POST /cv-analysis accepts PDF upload, returns extracted text
Day 3: POST /cv-analysis now calls Gemini and returns validated CVAnalysis
"""

from fastapi import FastAPI, File, HTTPException, UploadFile

from models import AnalyzeRequest, CVAnalysisResponse
from pdf_extractor import extract_text
from llm_extractor import extract_cv_data
from exceptions import PdfExtractionError, LlmExtractionError

app = FastAPI()


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
    Accept a PDF upload, extract its text, send it to Gemini,
    and return a validated CVAnalysis object.

    Failure modes:
    - Wrong file extension → 400
    - Invalid PDF → 422
    - Gemini failure or invalid LLM output → 503
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

    try:
        analysis = extract_cv_data(text)
    except LlmExtractionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM extraction failed: {e}",
        )

        # Reject texts too short to be a real CV
    if len(text.strip()) < 100:
        raise HTTPException(
            status_code=422,
            detail=f"Extracted text is too short to be a CV ({len(text.strip())} chars). "
                   "The file may not be a valid CV.",
        )

    return CVAnalysisResponse(
        filename=file.filename,
        text_length=len(text),
        analysis=analysis,
    )