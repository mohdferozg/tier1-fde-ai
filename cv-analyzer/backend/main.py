from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class AnalyzeRequest(BaseModel):
    name: str


# class Skill(BaseModel):
    title: str
    description: str

class CVItem(BaseModel):
    title: str
    description: str    


class CVAnalysis(BaseModel):
    technicalSkills: list[CVItem]
    experience: list[CVItem]
    projects: list[CVItem]
    

@app.get("/")
def root():
    return {"message": "Tier-1 FDE AI backend is running"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    return {"message": f"Hello {request.name}"}

@app.post("/cv-analysis")
def cv_analysis(cv_analysis_data: CVAnalysis):
    return cv_analysis_data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
