"""Pydantic models shared across the CV Analyzer backend.

These were previously defined in main.py. They live here so that
llm_extractor.py and main.py can both import them without creating
a circular import.
"""
from pydantic import BaseModel


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
    """Response from POST /cv-analysis (Day 3 version: structured CVAnalysis)."""
    filename: str
    text_length: int
    analysis: CVAnalysis