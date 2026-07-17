from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from agents.langgraph_agent import run_langgraph_agent
from agents.triage_agent import run_agent
from agents.triage_agent_gemini import run_agent_gemini
from agents.triage_agent_vertex import run_agent_vertex
from schemas.models import TriageRequest

api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@api_bp.route("/triage", methods=["POST"])
async def triage():
    # Flask has no built-in request validation like FastAPI, so we validate by hand.
    try:
        req = TriageRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    try:
        verdict = await run_agent(req.alert)   # same async agent FastAPI calls
        return jsonify(verdict.model_dump())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/triage-langgraph", methods=["POST"])
async def triage_langgraph():
    try:
        req = TriageRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    try:
        answer = await run_langgraph_agent(req.alert)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/triage-gemini", methods=["POST"])
async def triage_gemini():
    """Same as /triage, but calls Gemini instead of OpenAI. Needs GEMINI_API_KEY in .env."""
    try:
        req = TriageRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    try:
        verdict = await run_agent_gemini(req.alert)
        return jsonify(verdict.model_dump())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/triage-vertex", methods=["POST"])
async def triage_vertex():
    """Same as /triage, but calls Vertex AI instead of OpenAI. Needs VERTEX_SERVICE_ACCOUNT_PATH
    + VERTEX_PROJECT_ID in .env."""
    try:
        req = TriageRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    try:
        verdict = await run_agent_vertex(req.alert)
        return jsonify(verdict.model_dump())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
