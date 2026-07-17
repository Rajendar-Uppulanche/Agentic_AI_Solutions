# SOC Triage Agent

An AI agent that takes a security alert, calls tools to enrich it with threat intelligence and historical context, and returns a structured verdict.

Built to be provider-agnostic and framework-agnostic: the **same agent logic** is exposed through both **Flask** and **FastAPI**, and can run against **OpenAI**, **Google Gemini**, or **Google Vertex AI**.

---

## Provider status

| **Provider** | **Status** |
|---|---|
| **Vertex AI** | ✅ **Working end to end** — returns real structured verdicts |
| OpenAI | ⚠️ Code verified correct; blocked by account billing/quota (`insufficient_quota`) |
| Gemini (AI Studio) | ⚠️ Code verified correct; key authenticates but the project has zero free-tier quota (`limit: 0`) |

## What it does

```
POST /triage  {"alert": "Blocked outbound connection from 10.20.30.40 to known C2 domain"}
      │
      ▼
  validate the request        (Pydantic)
      │
      ▼
  ask the LLM what to do
      │
      ├─► LLM requests tools  →  run them concurrently (asyncio.gather)
      │                          ip_reputation, splunk_query
      ├─► feed results back, ask again  (loop, max 6 steps)
      │
      ▼
  force the final answer into a strict schema
      │
      ▼
  {"severity": "high", "action": "block", "confidence": 0.9, "reasoning": "..."}
```

A real response:
```json
{
  "severity": "low",
  "src_ip": null,
  "action": "escalate",
  "confidence": 0.1,
  "reasoning": "The provided IP address '10.20.30.4000' is malformed and cannot be processed by threat intelligence tools. Escalating for a valid IP address."
}
```

---

## Quick start

```bash
# 1. install
pip install -r requirements.txt

# 2. configure — copy the template and fill in at least one provider's credentials
cp .env.example .env

# 3. run (FastAPI, port 8000)
python -m uvicorn app_fastapi:app --reload --port 8000
#    → interactive docs at http://127.0.0.1:8000/docs

# or run the Flask version instead (port 5000)
python app_flask.py

# 4. test
python -m pytest -v
```

---

## Endpoints

| Method | Endpoint | Provider | Agent implementation |
|---|---|---|---|
| `GET` | `/health` | — | — |
| `POST` | `/triage` | OpenAI | Hand-written loop (raw SDK) |
| `POST` | `/triage-langgraph` | OpenAI | LangChain / LangGraph `create_agent` |
| `POST` | `/triage-gemini` | Google Gemini (AI Studio) | Hand-written loop |
| `POST` | `/triage-vertex` | Google Vertex AI | Hand-written loop |

All `/triage*` endpoints take the same body — `{"alert": "<text>"}` — and (except `/triage-langgraph`, which returns free text) return the same `SecurityVerdict` schema.

Both `app_fastapi.py` and `app_flask.py` expose all five routes and call the exact same agent code underneath.

---

## Project structure

```
agentic_app/
├── app_fastapi.py            # FastAPI entry point
├── app_flask.py              # Flask entry point (async routes via asgiref)
├── config.py                 # all settings/credentials, loaded once from .env
│
├── api_fastapi/routes.py     # FastAPI routes
├── api_flask/routes.py       # Flask routes (same logic, manual validation)
│
├── agents/
│   ├── triage_agent.py       # the agent loop — OpenAI
│   ├── langgraph_agent.py    # same job via LangChain/LangGraph
│   ├── triage_agent_gemini.py# same loop — Gemini
│   └── triage_agent_vertex.py# same loop — Vertex AI
│
├── tools/
│   ├── registry.py           # tool schemas + dispatch + error handling
│   ├── ip_reputation.py      # threat-intel lookup  (MOCK)
│   └── splunk.py             # historical context   (MOCK)
│
├── llm/
│   ├── client.py             # OpenAI client
│   ├── gemini_client.py      # Gemini client (OpenAI-compatible endpoint)
│   └── vertex_client.py      # Vertex client (service account + token refresh)
│
├── schemas/models.py         # TriageRequest (in) / SecurityVerdict (out)
├── tests/                    # 14 tests
└── docs/                     # detailed walkthroughs — start with How_This_Project_Works.md
```

**The core idea:** only `api_*/routes.py` is framework-specific and only `llm/*_client.py` is provider-specific. The agent loop, tools, and schemas are shared by everything.

---

## Configuration

All credentials live in `.env` (never committed). See `.env.example` for the full template.

**OpenAI** — the default:
```
OPENAI_API_KEY=sk-...
```

**Gemini (Google AI Studio)** — uses Google's OpenAI-compatible endpoint, so it reuses the same client class:
```
GEMINI_API_KEY=AIza...
```

**Vertex AI (Google Cloud)** — uses a service account JSON file, *not* a simple key. Store the file **outside this repo** and point to it:
```
VERTEX_SERVICE_ACCOUNT_PATH=C:\path\outside\repo\service-account.json
VERTEX_PROJECT_ID=your-project-id
VERTEX_REGION=us-central1
VERTEX_MODEL=google/gemini-2.0-flash-001
```

> **Vertex gotchas:**
> - The model name **needs the publisher prefix** — `google/gemini-2.0-flash-001`, not `gemini-2.0-flash-001`.
> - The model must actually be provisioned for your project *in that region*, or you'll get a `404 NOT_FOUND`. Adjust `VERTEX_REGION` / `VERTEX_MODEL` to match what your project has access to.

---



The OpenAI and Gemini paths are confirmed correct up to the point the provider rejects the request for account reasons — both reach the provider and authenticate successfully.

---

## Security

- **`.env` is gitignored** — never commit credentials.
- **Vertex service account JSON must live outside this folder.** `.gitignore` blocks `*.json` and `*service-account*` as a safety net, but keeping the file outside the repo is the real protection.
- No authentication is enforced on any endpoint yet (see Limitations).

---

## Testing

```bash
python -m pytest -v
```
14 tests covering both frameworks' routes, request validation, tool dispatch, JSON parsing, and error handling. Tools are tested standalone (no LLM or network required).

---

## Known limitations

- **Tools return mock data.** `ip_reputation.py` attempts a real HTTP call and falls back to a mock; `splunk.py` is a pure mock. Neither is wired to a real backend yet.
- **No authentication** on any endpoint.
- **LlamaIndex / RAG is not implemented** — this project is agent + tools only, no document ingestion or retrieval.
- **`/triage-langgraph` is not at parity** with the hand-written agent: it has only one tool, no retry logic, no step cap, and returns free text rather than a structured verdict. It exists to compare the framework approach against the hand-written loop.

---

## Concepts demonstrated

Python async (`asyncio.gather` for concurrent tool calls) · FastAPI · Flask · Pydantic models & validation · REST API design · Calling LLM APIs (OpenAI / Azure-compatible / Gemini / Vertex) · JSON parsing & structured outputs · LangChain / LangGraph · Agent implementation · Tool development · API integration

---

## Docs

Start with **`docs/How_This_Project_Works.md`** — a file-by-file walkthrough following one request end to end.

| Doc | For |
|---|---|
| `How_This_Project_Works.md` | How the files connect — **start here** |
| `Start_Here_Beginner_Guide.md` | Tiny standalone examples of each concept (async, Pydantic, etc.) |
| `Vertex_Setup_Instructions.md` | Setting up the Vertex service account |
| `EASY_Agent_Project_Explained.md` | Plain-English concept overview |
| `TODAY_Agent_Project_Crash_Course.md` | Deep reference — full code, checklists, links |
