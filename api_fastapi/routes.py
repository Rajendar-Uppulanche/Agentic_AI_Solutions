from fastapi import APIRouter, HTTPException

from agents.langgraph_agent import run_langgraph_agent
from agents.triage_agent import run_agent
from agents.triage_agent_gemini import run_agent_gemini
from agents.triage_agent_vertex import run_agent_vertex
from schemas.models import SecurityVerdict, TriageRequest

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/triage", response_model=SecurityVerdict)
async def triage(req: TriageRequest):
    try:
        return await run_agent(req.alert)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/triage-langgraph")
async def triage_langgraph(req: TriageRequest):
    try:
        answer = await run_langgraph_agent(req.alert)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/triage-gemini", response_model=SecurityVerdict)
async def triage_gemini(req: TriageRequest):
    """Same as /triage, but calls Gemini instead of OpenAI. Needs GEMINI_API_KEY in .env."""
    try:
        return await run_agent_gemini(req.alert)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/triage-vertex", response_model=SecurityVerdict)
async def triage_vertex(req: TriageRequest):
    """Same as /triage, but calls Vertex AI instead of OpenAI. Needs VERTEX_SERVICE_ACCOUNT_PATH
    + VERTEX_PROJECT_ID in .env."""
    try:
        return await run_agent_vertex(req.alert)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
