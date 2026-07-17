# How This Project Works — Every File, Explained Simply

> This is the one file to read to understand `Agent\agentic_app\`. It walks through every file in the order a request actually travels through them, in plain language.
> **All code below is copied directly from the real files** — the function names here (`run_agent`, `call_llm`, `execute_tool`, etc.) are the actual names in the code, so you can match them up one-to-one.

---

## The whole project in one sentence

Someone sends a security alert to your server → an AI decides what to check → your code runs those checks → the AI gives a final verdict → your server sends it back.

You saw this working in the browser — `/health`, `/triage`, `/triage-langgraph`, `/triage-gemini`, and `/triage-vertex` are the five doorways into this.

---

## The map — every file and its one-line job

```
Agent/agentic_app/
│
├── app_fastapi.py         → starts the web server (the "front door")
├── app_flask.py             → a second front door, same building
├── config.py                  → reads your API key(s)/credentials and settings once, shares them everywhere
│
├── api_fastapi/routes.py        → decides what happens when /health, /triage, etc. is called
├── api_flask/routes.py            → the same thing, Flask version
│
├── schemas/models.py                → the strict "forms": what a request must look like, what the answer must look like
│
├── agents/triage_agent.py             → THE BRAIN — the loop that decides what to do with the alert (OpenAI)
├── agents/langgraph_agent.py            → a second brain, same job, built with the LangChain library
├── agents/triage_agent_gemini.py          → a third brain, same loop, but calls Gemini instead of OpenAI
├── agents/triage_agent_vertex.py            → a fourth brain, same loop, but calls Vertex AI (service account auth)
│
├── tools/registry.py                          → the switchboard — runs whichever tool the brain asks for
├── tools/ip_reputation.py                       → one tool: "is this IP dangerous?"
├── tools/splunk.py                                → another tool: "has this happened before?"
│
├── llm/client.py                                    → the connection object that talks to OpenAI
├── llm/gemini_client.py                               → the connection object that talks to Gemini
├── llm/vertex_client.py                                 → builds a fresh-token connection to Vertex AI per call
│
├── docs/                                                  → explanations like this one
└── tests/                                                   → automated checks that everything still works
```

Now let's walk through them **in the order a real request visits them.**

---

## Step 1 — `app_fastapi.py`: the front door opens

Here is the **entire file**:
```python
import logging

from fastapi import FastAPI

from api_fastapi.routes import router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SOC Triage Agent (FastAPI)", version="1.0.0")
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

Line by line:
- `app = FastAPI(...)` — creates the web application. The `title` is what you saw at the top of the `/docs` page.
- `app.include_router(router)` — "the actual endpoints (`/health`, `/triage`, …) are defined over in `api_fastapi/routes.py` — go use those." `router` is imported on the line above.
- The `if __name__ == "__main__":` block only runs if you launch this file directly; `uvicorn` is the program that actually runs the server.

**This file does no real work.** It's the front door — it opens the building and points visitors to the right office (`routes.py`).

---

## Step 2 — `config.py`: settings get loaded once, at startup

Entire file:
```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Reuse the same .env that lives one folder up (Agent/.env) — no duplicated secrets.
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH)

    openai_api_key: str
    llm_base_url: str | None = None
    model: str = "gpt-4o-mini"
    max_agent_steps: int = 6


settings = Settings()
```

- `ENV_PATH` points at `Agent/.env` (one folder up), where your real OpenAI key is stored.
- The `Settings` class lists what settings exist: the API key, an optional base URL (for Azure/gateway), which model to use, and a safety limit `max_agent_steps` (more on that in Step 4).
- `settings = Settings()` — the last line **runs once** when the program starts. It reads the `.env` file and fills in these values. Every other file just imports this `settings` object instead of reading files itself.

This isn't part of the request flow — it happens once, at startup, before any request arrives.

---

## Step 3 — `api_fastapi/routes.py`: the request is received and checked

Entire file:
```python
from fastapi import APIRouter, HTTPException

from agents.langgraph_agent import run_langgraph_agent
from agents.triage_agent import run_agent
from schemas.models import TriageRequest

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/triage")
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
```

- `@router.get("/health")` — the simplest endpoint. Someone visits `/health`, they get `{"status": "ok"}`. This is just a "is the server alive?" check.
- `@router.post("/triage")` — the real one. Notice the parameter: `req: TriageRequest`. **That is the validation.** Before your code runs, FastAPI checks the incoming JSON matches the `TriageRequest` shape (defined in Step 3b). If it doesn't (like the empty `{}` you tested), FastAPI rejects it with a `422` automatically — `run_agent` never even runs.
- `return await run_agent(req.alert)` — pulls the `alert` text out of the request and hands it to the brain. `await` means "wait for the brain to finish, without freezing the server."
- The `try/except` — if anything goes wrong inside, return a `500` error instead of crashing.
- `/triage-langgraph` is identical but calls the other brain (`run_langgraph_agent`). That's the second POST box you saw in `/docs`.

### Step 3b — `schemas/models.py`: the "forms" being checked

Entire file:
```python
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    alert: str = Field(description="Raw security alert text")


class SecurityVerdict(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    src_ip: Optional[str] = Field(None, description="Source IP if present")
    action: Literal["block", "monitor", "ignore", "escalate"]
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(description="Short justification")
```

- `TriageRequest` is the **incoming** form: a request must have an `alert` field, and it must be text. That's what Step 3 checks.
- `SecurityVerdict` is the **outgoing** form: the final answer must have exactly these five fields. `Literal[...]` means `severity` can *only* be one of those four exact words — the AI physically cannot return anything else. `confidence: float = Field(ge=0, le=1)` means it must be a number between 0 and 1. This form gets used at the very end of Step 4.

---

## Step 4 — `agents/triage_agent.py`: the brain (the most important file)

This is the whole point of the project. Here is the **real, complete file**, then a line-by-line breakdown.

```python
import asyncio
import logging

from openai import APITimeoutError, RateLimitError

from config import settings
from llm.client import client
from schemas.models import SecurityVerdict
from tools.registry import TOOL_SCHEMAS, execute_tool

log = logging.getLogger("agent")

SYSTEM_PROMPT = (
    "You are a SOC triage agent. Use the available tools to enrich the alert with "
    "threat intelligence and historical context, then give a final structured verdict. "
    "Call tools in parallel when possible. Be concise."
)


async def call_llm(**kwargs):
    """Retry on rate limits / timeouts; anything else bubbles up immediately."""
    for attempt in range(3):
        try:
            return await client.chat.completions.create(**kwargs)
        except (RateLimitError, APITimeoutError):
            await asyncio.sleep(min(2 ** attempt, 3))
    raise RuntimeError("LLM unavailable after retries")


async def run_agent(alert: str) -> SecurityVerdict:
    messages: list = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Triage this alert:\n{alert}"},
    ]

    for step in range(settings.max_agent_steps):
        resp = await call_llm(model=settings.model, messages=messages, tools=TOOL_SCHEMAS, temperature=0)
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            break

        results = await asyncio.gather(
            *[execute_tool(tc) for tc in msg.tool_calls], return_exceptions=True
        )
        for tc, result in zip(msg.tool_calls, results):
            content = f"ERROR: {result}" if isinstance(result, Exception) else str(result)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": content})
    else:
        log.warning("agent hit max_steps=%d", settings.max_agent_steps)

    final = await client.chat.completions.parse(
        model=settings.model,
        messages=messages + [{"role": "user", "content": "Give your final verdict."}],
        response_format=SecurityVerdict,
    )
    verdict = final.choices[0].message.parsed
    if verdict is None:
        raise RuntimeError("LLM refused or returned invalid output")
    return verdict
```

Now the breakdown.

**`SYSTEM_PROMPT`** — the standing instructions given to the AI every time. It tells the AI what role to play ("you are a SOC triage agent") and what to do.

**`call_llm(**kwargs)`** — a small helper that actually sends the request to OpenAI (`client.chat.completions.create`). It wraps it in a retry: if OpenAI says "too many requests" or times out, it waits and tries again, up to 3 times. (This is the function that keeps hitting the billing error right now — it retries 3 times, then raises `"LLM unavailable after retries"`.)

**`messages`** — a list, like a chat transcript. It starts with two entries:
- the `system` message (the standing instructions)
- the `user` message (the actual alert)

Every time a tool runs, its result gets **added** to this list, and the whole list is sent again. That growing list *is* the conversation.

**`for step in range(settings.max_agent_steps):`** — the loop. It runs at most 6 times (from `config.py`). This limit exists so the agent can't loop forever and run up a huge bill.

Inside the loop:
- `resp = await call_llm(...)` — ask the AI. Note `tools=TOOL_SCHEMAS` — this tells the AI what tools it's allowed to use.
- `msg = resp.choices[0].message` — the AI's reply is buried a couple levels deep; `resp.choices[0].message` is how you dig it out. (This is just how the OpenAI library structures its response — you always reach in the same way.)
- `messages.append(msg)` — add the AI's reply to the transcript.
- `if not msg.tool_calls: break` — **the exit condition.** If the AI did *not* ask to use any tools, it's ready to give a final answer, so we stop the loop.
- If it *did* ask for tools:
  ```python
  results = await asyncio.gather(
      *[execute_tool(tc) for tc in msg.tool_calls], return_exceptions=True
  )
  ```
  This runs **all** requested tools at the same time (that's `asyncio.gather`). `msg.tool_calls` is the list of tools the AI wants; `execute_tool(tc)` runs each one (Step 5). `return_exceptions=True` means "if one tool crashes, don't kill the others — just record the error."
- Then the `for tc, result in zip(...)` loop adds each tool's result back into `messages`, tagged with `role: "tool"` and the `tool_call_id` (so the AI knows which result answers which request). Then the outer loop goes around again — the AI sees the tool results and decides what's next.

**`else:` (attached to the `for` loop)** — this is an unusual Python feature: a `for` loop can have an `else` that runs only if the loop finished *without* hitting `break`. So this line runs only if the agent used all 6 steps without the AI ever settling — it just logs a warning.

**The final block:**
```python
final = await client.chat.completions.parse(
    model=settings.model,
    messages=messages + [{"role": "user", "content": "Give your final verdict."}],
    response_format=SecurityVerdict,
)
verdict = final.choices[0].message.parsed
```
- `.parse(...)` (instead of `.create(...)`) plus `response_format=SecurityVerdict` — this **forces** the AI's answer into the `SecurityVerdict` shape from Step 3b. No free-form sentences; it must fill in `severity`, `action`, `confidence`, etc.
- `final.choices[0].message.parsed` — the already-validated `SecurityVerdict` object, ready to return.

**That's the entire "agent."** A loop: ask → if it wants tools, run them and loop again → if not, force a clean final answer.

### `llm/client.py` — the connection `call_llm` uses

Entire file:
```python
from openai import AsyncOpenAI

from config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.llm_base_url)
```
One line of real work: build the OpenAI connection object using the key from `config.py`. This `client` is what `call_llm` and the final `.parse` call both use. Because `base_url` comes from settings, pointing at Azure or an internal gateway later needs no code change — just an `.env` edit.

---

## Step 5 — `tools/registry.py`: running whatever the AI asked for

The AI can't run code itself — it can only *say* "please run `get_ip_reputation` with `ip=10.20.30.40`." This file turns that request into an actual function call.

```python
TOOL_REGISTRY = {
    "get_ip_reputation": get_ip_reputation,
    "query_splunk": query_splunk,
}

# (TOOL_SCHEMAS is a list describing each tool to the AI — its name, what it does,
#  and what arguments it takes. This is what gets passed as tools=TOOL_SCHEMAS in Step 4.)

async def execute_tool(tool_call) -> str:
    name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        return f"ERROR: bad tool arguments: {e}"

    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return f"ERROR: unknown tool '{name}'"
    try:
        return await asyncio.wait_for(fn(**args), timeout=10)
    except asyncio.TimeoutError:
        return f"ERROR: tool '{name}' timed out"
    except Exception as e:
        log.exception("tool %s failed", name)
        return f"ERROR: {e}"
```

- `TOOL_REGISTRY` — a lookup table mapping a tool's **name** (text the AI uses) to the **actual function**.
- `TOOL_SCHEMAS` — the *description* of the tools that gets shown to the AI (so it knows they exist and how to call them). This is the `tools=TOOL_SCHEMAS` you saw passed in Step 4.
- `execute_tool(tool_call)`:
  - `name = tool_call.function.name` — which tool the AI asked for.
  - `args = json.loads(tool_call.function.arguments)` — the AI sends arguments as a **JSON string** (text), so `json.loads` turns it back into real Python data.
  - `fn = TOOL_REGISTRY.get(name)` — look up the real function.
  - `await asyncio.wait_for(fn(**args), timeout=10)` — run it, but give up after 10 seconds so a slow tool can't hang forever.
  - Every failure path returns `"ERROR: ..."` **as text** instead of crashing. That's deliberate — the error goes back to the AI (Step 4), so the AI can read "that failed" and try something else.

### The two actual tools

`tools/ip_reputation.py`:
```python
async def get_ip_reputation(ip: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            r = await http.get(f"https://ti.internal/api/ip/{ip}")
            r.raise_for_status()
            d = r.json()
            return f"IP {ip}: score={d['score']}/100, verdict={d['verdict']}"
    except httpx.HTTPError:
        # no real threat-intel API wired up yet — mock so the demo runs end to end
        return f"IP {ip}: score=87/100, verdict=malicious, last_seen=2h ago (mock)"
```
It *tries* to call a real internal API (`https://ti.internal/...`), but since that doesn't exist yet, the call fails and it falls back to returning **fake data** (note the `(mock)`). When there's a real API, you'd delete the fallback.

`tools/splunk.py`:
```python
async def query_splunk(query: str) -> str:
    await asyncio.sleep(0.3)  # simulate network latency
    return f"Splunk[{query}] -> 42 events in last 24h, 3 distinct dest hosts (mock)"
```
Pure mock — waits a moment to imitate a real network call, then returns fake data.

**So right now both tools return pretend data.** The whole loop works end to end; it just isn't wired to real Cisco systems yet.

---

## Step 6 — the answer travels back out

`run_agent` returns the finished `SecurityVerdict` → back up to `api_fastapi/routes.py` (Step 3), which returns it → FastAPI turns it into JSON → out to whoever made the request.

---

## The one picture, all the steps

```
app_fastapi.py            starts the server
     │
config.py                 (loads settings once, at startup)
     │
api_fastapi/routes.py     receives + validates the request      (schemas/models.py: TriageRequest)
     │
agents/triage_agent.py    run_agent(): loop → call_llm() → if tool_calls, execute them → repeat
     │           │                                          → else: force final answer
     │      tools/registry.py: execute_tool() → tools/ip_reputation.py, tools/splunk.py
     │           │
     │      llm/client.py: the AsyncOpenAI connection
     │
schemas/models.py         (SecurityVerdict: forces the final answer into a strict shape)
     │
back out through routes → app → whoever asked
```

---

## The extras you'll notice

**Two front doors:** `app_fastapi.py` (port 8000) and `app_flask.py` (port 5000). `api_flask/routes.py` does the same thing as the FastAPI one, just with Flask's syntax — and it calls the exact same `run_agent`. One difference: Flask doesn't auto-validate, so it does it by hand:
```python
req = TriageRequest.model_validate(request.get_json(silent=True) or {})
```

**Four brains:** `agents/triage_agent.py` (everything above), `agents/langgraph_agent.py`, `agents/triage_agent_gemini.py`, and `agents/triage_agent_vertex.py`.

The LangGraph one does the same job but lets the LangChain library run the loop instead of the hand-written `for step in range(...)`:
```python
_graph_agent = create_agent(_llm, tools=[get_ip_reputation_tool])

async def run_langgraph_agent(alert: str) -> str:
    result = await _graph_agent.ainvoke({"messages": [("user", f"Triage this alert: {alert}")]})
    return result["messages"][-1].content
```
`create_agent(...)` builds the whole loop for you — you just hand it the model and the tools. That's the point of a framework: less code, but the loop is hidden. Reachable at `/triage-langgraph`.

The Gemini one is a **copy of `triage_agent.py`, line for line the same loop** — the only two things that changed are which client it imports and which model name it passes:
```python
from llm.gemini_client import client   # instead of llm.client

resp = await call_llm(model=settings.gemini_model, ...)   # instead of settings.model
```
This works because Google's Gemini API has an **OpenAI-compatible endpoint** — `llm/gemini_client.py` builds the exact same `AsyncOpenAI` class as `llm/client.py`, just pointed at Google's URL with a Gemini key instead of an OpenAI key:
```python
client = AsyncOpenAI(
    api_key=settings.gemini_api_key or "not-set-yet",
    base_url=settings.gemini_base_url,   # https://generativelanguage.googleapis.com/v1beta/openai/
)
```
Reachable at `/triage-gemini`. **✅ Live-tested with a real key** — the key authenticates and reaches Gemini successfully. It's currently blocked by a `RESOURCE_EXHAUSTED` / `limit: 0` quota error on the Google Cloud project behind that key (needs the Generative Language API enabled / billing linked on that project) — an account issue, not a code issue.

**The fourth brain — Vertex AI (`agents/triage_agent_vertex.py`)** — is the same loop again, but Vertex uses a fundamentally different auth model than the other three. OpenAI and Gemini both use a **static API key** that never changes, so `llm/client.py` and `llm/gemini_client.py` each build **one** client object at import time and reuse it forever:
```python
client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.llm_base_url)
```
Vertex AI instead authenticates with a **Google Cloud service account** (a JSON credentials file), which you exchange for a short-lived access token — it expires after about an hour. So `llm/vertex_client.py` can't build one static client; instead it exposes a function that hands back a client with a fresh token every time it's called:
```python
def get_client() -> AsyncOpenAI:
    base_url = (
        f"https://{settings.vertex_region}-aiplatform.googleapis.com/v1beta1/"
        f"projects/{settings.vertex_project_id}/locations/{settings.vertex_region}/endpoints/openapi"
    )
    return AsyncOpenAI(api_key=_get_access_token(), base_url=base_url)   # ← fresh token each call
```
`_get_access_token()` uses Google's `google-auth` library to refresh the token from the service account file whenever it's expired. Everything else — the loop, the tools, the retries — is identical to the other three brains.

**Security note:** the Vertex service account file is a real credential (like a password). It must live **outside** this project folder and never be committed to git — `.gitignore` here now blocks `*.json` files defensively for exactly this reason. `.env` only stores the *path* to that file (`VERTEX_SERVICE_ACCOUNT_PATH`), never the file's contents.

Reachable at `/triage-vertex`. **⚠️ Not live-tested** — no real service account file was available while building this; I verified the app boots cleanly and fails with a clear, specific error (`"VERTEX_PROJECT_ID is not set in .env"`) rather than crashing, when the credentials aren't configured yet. Once you add `VERTEX_SERVICE_ACCOUNT_PATH`, `VERTEX_PROJECT_ID`, and confirm `VERTEX_REGION` in `.env`, try it and share the result.

---

## If you only remember one thing

**An "agent" is nothing more than the `for` loop inside `run_agent`.** Everything else — the web server, the validation, the tools registry, the settings — exists purely to feed that loop correctly and hand back what it produces safely. Once that one loop makes sense, the rest of the files are just plumbing around it.
