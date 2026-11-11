"""FastAPI wrapper for the RAG pipeline."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from generator import answer

app = FastAPI(title="RAG Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    top_k: int = 3


class ChunkInfo(BaseModel):
    id: int
    similarity: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[int]
    chunks: list[ChunkInfo]


@app.get("/")
def root():
    return {"message": "RAG Lab API is running"}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Answer a question using RAG."""
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        result = answer(request.query, top_k=request.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG pipeline error: {e}")

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        chunks=[{"id": c["id"], "similarity": c["similarity"]} for c in result["chunks"]],
    )