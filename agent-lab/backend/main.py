"""FastAPI wrapper for the delivery-ops agent."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import MAX_TURNS, run
from tools import TOOL_DECLARATIONS

app = FastAPI(title="Agent Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    max_turns: int = Field(default=MAX_TURNS, ge=1, le=12)


class ToolStep(BaseModel):
    turn: int
    model: str
    tool: str
    arguments: dict
    ok: bool
    duration_ms: int
    result: str


class AskResponse(BaseModel):
    answer: str
    steps: list[ToolStep]
    tools_used: list[str]
    models: list[str]
    turns: int
    latency_s: float
    truncated: bool


@app.get("/")
def root():
    return {"message": "Agent Lab API is running"}


@app.get("/tools")
def list_tools():
    """The exact tool contract the model is given."""
    return TOOL_DECLARATIONS


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    """Answer a question with a tool-calling agent.

    Declared `def` (not `async def`) on purpose: the agent makes blocking LLM
    calls, so FastAPI runs it in a worker thread instead of stalling the event
    loop.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = run(request.question, max_turns=request.max_turns, verbose=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")

    if result["error"]:
        raise HTTPException(status_code=502, detail=result["error"])

    return AskResponse(
        answer=result["answer"],
        steps=[ToolStep(**step) for step in result["steps"]],
        tools_used=result["tools_used"],
        models=result["models"],
        turns=result["turns"],
        latency_s=result["latency_s"],
        truncated=result["truncated"],
    )
