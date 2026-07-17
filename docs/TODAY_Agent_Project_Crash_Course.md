# Agent Project — Complete Crash Course
> **Project:** New 4-week internal project (alongside interview prep)
> **TL asked you to learn:** Python async (asyncio) · FastAPI basics · Pydantic models · REST APIs · LangChain/LlamaIndex overview · Calling LLM APIs (OpenAI/Azure/OpenAI-compatible) · JSON parsing and structured outputs
> **Your responsibilities:** Agent implementation · Tool development · API integration
> **Nothing here is skipped.** Every topic your TL listed is covered in full, with code, checklists, videos, and articles.

> **✅ Status: this plan has been executed.** The project this doc prepares you for now exists at `Agent\agentic_app\` (small, self-contained: Flask + FastAPI, one agent, tested) and `Agent\agentic_platform\` (the full team directory structure). 7 of the 8 topics above are demonstrated in real, tested code — the exception is **LlamaIndex**, which hasn't been touched (no RAG/document work in either project yet). See `EASY_Agent_Project_Explained.md` in this same folder for the plain-English status of every topic, or `How_This_Project_Works.md` for the actual code walkthrough.

> **🆕 New to this stack? Start with `Start_Here_Beginner_Guide.md` first**, not this file. It covers the same 7 topics with tiny, heavily-commented, standalone examples instead of the production-grade code below — come back here once those feel comfortable.

---

## Table of Contents
| # | Topic | Time | Priority |
|---|---|---|---|
| 0 | [Setup](#0--setup) | 10 min | — |
| 1 | [Python async (asyncio)](#1--python-async-asyncio) | 60 min | 🔴 Highest |
| 2 | [Pydantic models](#2--pydantic-models) | 45 min | 🔴 High |
| 3 | [REST APIs](#3--rest-apis) | 30 min | 🟢 Review |
| 4 | [FastAPI basics](#4--fastapi-basics) | 45 min | 🔴 High |
| 5 | [Calling LLM APIs (OpenAI / Azure / compatible)](#5--calling-llm-apis-openai--azure--openai-compatible) | 40 min | 🔴 High |
| 6 | [JSON parsing & structured outputs](#6--json-parsing--structured-outputs) | 45 min | 🔴 Highest |
| 7 | [LangChain / LlamaIndex / LangGraph](#7--langchain--llamaindex--langgraph-overview) | 45 min | 🟠 Overview |
| R1 | [Agent implementation](#r1--agent-implementation) | 45 min | ⭐ Your job |
| R2 | [Tool development](#r2--tool-development) | 30 min | ⭐ Your job |
| R3 | [API integration](#r3--api-integration) | 30 min | ⭐ Your job |
| 🏗️ | [The Build — one app that uses everything](#️-the-build--one-app-that-proves-all-of-it) | 60 min | ⭐⭐ |

> **Day 1 (today, 4–5 hrs):** Topics 1, 2, 6 + skim 4, 5 + The Build.
> **Rest of week 1:** Topics 3, 7 in full + R1, R2, R3 in depth.

---

## 0 · Setup

```bash
python -m venv venv
venv\Scripts\activate                 # Windows (PowerShell: venv\Scripts\Activate.ps1)

pip install fastapi uvicorn pydantic pydantic-settings openai httpx python-dotenv
pip install langchain langchain-openai langgraph llama-index    # for topic 7
pip install pytest pytest-asyncio                                # you're a TDD person
```

`.env`:
```
OPENAI_API_KEY=sk-...

# If your project uses Azure (ASK YOUR TL):
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# If an internal OpenAI-compatible gateway:
LLM_BASE_URL=https://internal-gateway.cisco.com/v1
```

---
---

# 1 · Python async (asyncio)

**Why your TL listed it:** An agent is mostly **I/O wait** — LLM calls and tool HTTP calls. Async lets one process handle many concurrent waits instead of blocking a thread on each. Every agent framework (LangGraph, LlamaIndex, OpenAI SDK, FastAPI) is async-first. Django is sync, so this is genuinely new for you.

## 1.1 Core concepts

```python
import asyncio, time

async def call_tool(name: str, delay: float):     # coroutine function
    await asyncio.sleep(delay)                     # await = "yield control while waiting"
    return f"{name} done"

async def main():
    result = await call_tool("a", 1)               # await = run it, wait for result
    print(result)

asyncio.run(main())                                # entry point — starts the event loop
```

- **Coroutine** — `async def` function. Calling it returns a coroutine object; it does **nothing** until awaited.
- **Event loop** — single-threaded scheduler. While one coroutine is `await`ing I/O, it runs others.
- **`await`** — only legal inside `async def`. Suspends this coroutine, frees the loop.
- **Async is concurrency, not parallelism.** One thread, interleaved. Great for I/O, useless for CPU work.

## 1.2 `asyncio.gather()` — the single most important thing

```python
async def main():
    start = time.time()

    # ❌ SEQUENTIAL — 3 seconds. The classic Django-dev mistake.
    a = await call_tool("a", 1)
    b = await call_tool("b", 1)
    c = await call_tool("c", 1)

    # ✅ CONCURRENT — 1 second. THIS is why agents use async.
    a, b, c = await asyncio.gather(
        call_tool("a", 1),
        call_tool("b", 1),
        call_tool("c", 1),
    )
    print(f"{time.time() - start:.2f}s")
```

**Handling failures without killing the batch:**
```python
results = await asyncio.gather(*coros, return_exceptions=True)
for r in results:
    if isinstance(r, Exception):
        log.warning("tool failed: %s", r)     # one bad tool doesn't kill the agent
    else:
        use(r)
```

## 1.3 Tasks — fire now, await later
```python
task = asyncio.create_task(call_tool("bg", 2))   # starts running immediately
other = await call_tool("fast", 0.1)             # do other work meanwhile
result = await task                              # collect when needed

task.cancel()                                    # cancellation
```

## 1.4 Timeouts — agents MUST have these
```python
try:
    result = await asyncio.wait_for(call_tool("slow", 10), timeout=3.0)
except asyncio.TimeoutError:
    result = "tool timed out"        # degrade gracefully, don't hang the agent

# Python 3.11+ preferred:
async with asyncio.timeout(3.0):
    result = await call_tool("slow", 10)
```

## 1.5 Running blocking/sync code (you WILL need this)
Your existing code — Django ORM, `requests`, Splunk SDK, boto3 — is **blocking**. Calling it inside `async def` **freezes the entire event loop**.

```python
import asyncio, requests

# ❌ NEVER — blocks the whole loop, all concurrency dies
async def bad():
    return requests.get("https://api.com").json()

# ✅ Offload to a thread pool
async def good():
    return await asyncio.to_thread(requests.get, "https://api.com")

# ✅ Better — use a natively async client
import httpx
async def best():
    async with httpx.AsyncClient() as c:
        r = await c.get("https://api.com")
        return r.json()
```
**Rule:** inside `async def` — never `time.sleep()` (use `asyncio.sleep`), never `requests` (use `httpx`), never heavy CPU loops (use `asyncio.to_thread` or a process pool).

## 1.6 Async HTTP with httpx (every tool you build uses this)
```python
import httpx

# Reuse ONE client across the app — connection pooling. Don't create per-request.
client = httpx.AsyncClient(timeout=httpx.Timeout(10.0), limits=httpx.Limits(max_connections=100))

async def fetch(ip: str) -> dict:
    r = await client.get(f"https://ti.internal/api/ip/{ip}")
    r.raise_for_status()
    return r.json()

async def shutdown():
    await client.aclose()
```

## 1.7 Async iteration & context managers
```python
async with httpx.AsyncClient() as c:          # async context manager
    async with c.stream("GET", url) as resp:  # streaming
        async for chunk in resp.aiter_bytes(): # async iteration
            process(chunk)

# Your own:
class Session:
    async def __aenter__(self): ...
    async def __aexit__(self, *exc): ...

async def gen():
    for i in range(3):
        await asyncio.sleep(0.1)
        yield i          # async generator — used for token streaming
```

## 1.8 Concurrency control (don't DoS your internal APIs)
```python
sem = asyncio.Semaphore(5)          # max 5 concurrent calls

async def limited_fetch(ip):
    async with sem:
        return await fetch(ip)

results = await asyncio.gather(*[limited_fetch(ip) for ip in ips])
```

## ✅ asyncio checklist
- [ ] `async def`, `await`, coroutine vs coroutine object
- [ ] `asyncio.run()` — entry point
- [ ] **`asyncio.gather()`** — parallel calls ← most important
- [ ] `gather(..., return_exceptions=True)` — partial failure
- [ ] `asyncio.create_task()` — fire and collect later
- [ ] `asyncio.wait_for()` / `asyncio.timeout()` — timeouts
- [ ] `asyncio.to_thread()` — wrap blocking code
- [ ] `asyncio.Semaphore` — rate/concurrency limiting
- [ ] `httpx.AsyncClient` — async HTTP, reused client
- [ ] `async with` / `async for` / async generators
- [ ] Never block the event loop
- [ ] `pytest-asyncio` for testing async code

## 📺 Videos
- **mCoding — "Python Asyncio: The Complete Guide"** *(search: `mCoding asyncio`)* — best event-loop explanation, ~25 min
- **ArjanCodes — "Async Python Tutorial"** — practical, production style
- **Tech With Tim — "Asyncio in 15 Minutes"** — fastest on-ramp
- **freeCodeCamp — "Asyncio Full Course"** — depth if you want it

## 📄 Articles
- **Real Python — "Async IO in Python: A Complete Walkthrough"** → `realpython.com/async-io-python/` ⭐ **read this**
- **FastAPI — "Concurrency and async/await"** → `fastapi.tiangolo.com/async/` ⭐ (explains async in web-dev framing — perfect for you)
- **Python docs — asyncio** → `docs.python.org/3/library/asyncio.html`
- **httpx — Async support** → `python-httpx.org/async/`

---
---

# 2 · Pydantic models

**Why your TL listed it:** Pydantic is the backbone of everything — it validates API requests (FastAPI), it defines **tool schemas** for the LLM, and it enforces **structured output**. It's the most-used library in agent code.

## 2.1 Basics (Pydantic v2)
```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional
from datetime import datetime
from enum import Enum

class Severity(str, Enum):
    LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

class SecurityAlert(BaseModel):
    severity: Severity                                        # constrains the LLM!
    src_ip: str = Field(description="Source IPv4 address")    # ← LLM READS this
    action: Literal["block", "monitor", "ignore", "escalate"]
    confidence: float = Field(ge=0, le=1, description="0 to 1")
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    seen_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("src_ip")
    @classmethod
    def valid_ipv4(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            raise ValueError("must be a valid IPv4 address")
        return v

    @model_validator(mode="after")
    def critical_must_block(self):
        if self.severity == Severity.CRITICAL and self.action == "ignore":
            raise ValueError("critical alerts cannot be ignored")
        return self
```

## 2.2 The methods you'll use constantly
```python
a = SecurityAlert(severity="high", src_ip="10.0.0.1", action="block", confidence=0.9)

a.model_dump()                       # → dict
a.model_dump_json(indent=2)          # → JSON string
a.model_dump(exclude={"notes"})      # partial
SecurityAlert.model_validate(d)      # dict  → model (validates)
SecurityAlert.model_validate_json(s) # JSON  → model (validates)

SecurityAlert.model_json_schema()    # ⭐⭐ → JSON Schema — THIS becomes your LLM tool schema
```

## 2.3 Error handling — and the retry loop
```python
from pydantic import ValidationError

try:
    alert = SecurityAlert.model_validate_json(llm_output)
except ValidationError as e:
    print(e.errors())     # structured, machine-readable errors
    # ⭐ Agent pattern: feed e back to the LLM and ask it to fix its own output
```

## 2.4 Settings management (config from env)
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    llm_base_url: str | None = None
    model: str = "gpt-4o"
    max_agent_steps: int = 5

    class Config:
        env_file = ".env"

settings = Settings()      # reads + validates env vars at startup
```

## 2.5 🧠 Mental map from DRF (you already know this)
| DRF | Pydantic |
|---|---|
| `serializers.Serializer` | `BaseModel` |
| `serializer.is_valid()` | automatic on construction |
| `serializer.validated_data` | the model instance itself |
| `validate_<field>()` | `@field_validator("field")` |
| `validate()` (object-level) | `@model_validator(mode="after")` |
| `serializer.data` | `.model_dump()` |
| `ValidationError` | `ValidationError` (same idea) |
| — *(DRF has no equivalent)* | **`.model_json_schema()`** ← the LLM superpower |

## ✅ Pydantic checklist
- [ ] `BaseModel`, type hints drive validation
- [ ] `Field(description=...)` — **the LLM reads descriptions; write them like prompts**
- [ ] `Literal` / `Enum` — constrain LLM to valid values (huge reliability win)
- [ ] `Field(ge=, le=, min_length=, max_length=, pattern=)` — constraints
- [ ] `Optional[X]` / `X | None`, `default_factory`
- [ ] `@field_validator`, `@model_validator`
- [ ] `.model_dump()`, `.model_dump_json()`, `.model_validate()`, `.model_validate_json()`
- [ ] **`.model_json_schema()`** — generates tool schemas
- [ ] `ValidationError` → retry the LLM with the error
- [ ] Nested models, `list[Model]`
- [ ] `BaseSettings` for config

## 📺 Videos
- **ArjanCodes — "Pydantic Tutorial"** ⭐ best practical intro
- **Tech With Tim — "Pydantic in 20 Minutes"**
- **Patrick Loeber — "Pydantic Crash Course"**

## 📄 Articles
- **Pydantic docs — Models** → `docs.pydantic.dev/latest/concepts/models/` ⭐
- **Pydantic docs — Validators** → `docs.pydantic.dev/latest/concepts/validators/`
- **Pydantic docs — JSON Schema** → `docs.pydantic.dev/latest/concepts/json_schema/` ⭐ *(the tool-schema magic)*
- **Pydantic docs — Settings** → `docs.pydantic.dev/latest/concepts/pydantic_settings/`
- Real Python — "Pydantic: Simplifying Data Validation in Python"

---
---

# 3 · REST APIs

**Why your TL listed it:** Your agent will be **exposed as** a REST API, and its tools will **consume** REST APIs (internal Cisco services). You have 4.5 yrs of DRF so this is a **review**, but here is the complete checklist — plus the parts specific to agent/LLM services that are genuinely new.

## 3.1 Fundamentals (you know these — confirm)
| Method | Meaning | Idempotent? | Body? |
|---|---|---|---|
| `GET` | Read | ✅ | ❌ |
| `POST` | Create / action | ❌ | ✅ |
| `PUT` | Replace whole resource | ✅ | ✅ |
| `PATCH` | Partial update | ❌ | ✅ |
| `DELETE` | Remove | ✅ | ❌ |

**Status codes to know cold:**
`200` OK · `201` Created · `202` **Accepted** (async job started — you'll use this for long agent runs) · `204` No Content · `400` Bad Request · `401` Unauthorized · `403` Forbidden · `404` Not Found · `409` Conflict · `422` Unprocessable Entity (validation — FastAPI's default) · `429` **Too Many Requests** (rate limit — LLM APIs return this constantly) · `500` Server Error · `502/503/504` upstream failures.

## 3.2 Design principles
- **Resource-oriented URLs:** `/agents/{id}/runs` — nouns, plural, no verbs (`/getAgent` ❌)
- **Versioning:** `/v1/triage` or an `Accept` header
- **Pagination:** limit/offset or cursor
- **Filtering/sorting:** `?severity=high&sort=-created_at`
- **Consistent error envelope:**
  ```json
  {"error": {"code": "invalid_ip", "message": "src_ip must be IPv4", "request_id": "abc-123"}}
  ```
- **Idempotency keys** — for POSTs that must not double-execute (critical when an agent retries a tool that *takes an action*, e.g. "block this IP")
- **HATEOAS** — know the term; rarely used in practice
- **OpenAPI/Swagger** — the spec. FastAPI generates it for free at `/docs`.

## 3.3 Auth (you'll hit all of these on internal APIs)
- **API key** — `X-API-Key: ...` header
- **Bearer token / JWT** — `Authorization: Bearer <token>`
- **OAuth2 / client-credentials** — machine-to-machine; you fetch a token, cache it, refresh before expiry ← **most likely for internal Cisco APIs**
- **mTLS** — possible in Cisco-internal contexts

## 3.4 What's NEW for agent/LLM APIs (this part matters)
- **Long-running requests.** Agent runs take 10–60s. Options:
  - **Streaming** (SSE) — stream tokens/steps as they happen ← preferred
  - **`202 Accepted` + polling** — return a `run_id`, client polls `GET /runs/{id}`
  - **Webhooks** — call the client back when done
- **Streaming with SSE** — the standard for LLM responses (`text/event-stream`)
- **Timeouts** — must be generous (LLM latency) but bounded
- **Retries + backoff on `429`/`5xx`** — LLM providers rate-limit aggressively
- **Cost/token headers** — expose usage so callers can budget
- **Idempotency** — an agent retry must not re-execute a destructive tool twice

## ✅ REST checklist
- [ ] HTTP methods + idempotency semantics
- [ ] Status codes (esp. `202`, `422`, `429`)
- [ ] Resource naming, versioning, pagination, filtering
- [ ] Consistent error envelope + request IDs
- [ ] Auth: API key, Bearer/JWT, OAuth2 client-credentials, mTLS
- [ ] Idempotency keys for action-taking endpoints
- [ ] OpenAPI/Swagger
- [ ] **Long-running patterns:** streaming (SSE) vs `202`+polling vs webhooks
- [ ] Retry/backoff on `429`/`5xx`
- [ ] Rate limiting, timeouts, circuit breakers

## 📺 Videos
- **freeCodeCamp — "REST API Tutorial"** (refresher)
- **ByteByteGo — "REST API Design Best Practices"** *(YouTube, short + excellent)* ⭐
- **Search: `SSE server sent events python fastapi`** for the streaming pattern

## 📄 Articles
- **Microsoft — REST API Design Best Practices** → `learn.microsoft.com/azure/architecture/best-practices/api-design` ⭐ (thorough, free)
- **Google — API Design Guide** → `cloud.google.com/apis/design`
- **MDN — HTTP status codes** → `developer.mozilla.org/en-US/docs/Web/HTTP/Status`
- **MDN — Server-Sent Events** → `developer.mozilla.org/en-US/docs/Web/API/Server-sent_events`
- **Stripe API docs** — the gold standard for error/idempotency design; read how they do idempotency keys

---
---

# 4 · FastAPI basics

**Why your TL listed it:** Your agent will be served over FastAPI. It's the standard for AI backends because it's **async-native** and **Pydantic-native**.

## 4.1 🧠 Mental map from Django/DRF
| Django / DRF | FastAPI |
|---|---|
| `serializers.py` | Pydantic models |
| `views.py` / ViewSet | plain `async def` functions |
| `urls.py` | decorator on the function |
| DRF Browsable API | **auto Swagger at `/docs`** (free) |
| WSGI + Gunicorn | **ASGI + Uvicorn** (async native) |
| `permission_classes` | `Depends()` |
| `settings.py` | `BaseSettings` |
| Middleware | Middleware (same concept) |
| Celery | `BackgroundTasks` (light) / Celery (heavy) |

## 4.2 Core app
```python
from fastapi import FastAPI, Depends, HTTPException, Query, Path, Header, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Triage Agent Service", version="1.0.0")

class TriageRequest(BaseModel):
    alert: str
    priority: int = 1

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/v1/triage", response_model=SecurityAlert, status_code=200)
async def triage(
    req: TriageRequest,                                  # body — auto-validated → 422
    verbose: bool = Query(False),                        # query param
    x_request_id: str | None = Header(None),             # header
):
    try:
        return await run_agent(req.alert)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/v1/runs/{run_id}")
async def get_run(run_id: str = Path(..., description="Agent run ID")):
    ...
```
Run: `uvicorn main:app --reload` → **http://127.0.0.1:8000/docs**

## 4.3 Dependency injection (`Depends`) — auth, shared clients
```python
from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer()

async def verify_token(cred: HTTPAuthorizationCredentials = Security(bearer)) -> str:
    if not is_valid(cred.credentials):
        raise HTTPException(401, "invalid token")
    return cred.credentials

async def get_llm_client() -> AsyncOpenAI:
    return app.state.llm          # shared, pooled

@app.post("/v1/triage")
async def triage(req: TriageRequest,
                 user: str = Depends(verify_token),
                 llm: AsyncOpenAI = Depends(get_llm_client)):
    ...
```

## 4.4 Streaming (essential for agents)
```python
from fastapi.responses import StreamingResponse

async def token_stream(alert: str):
    stream = await client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": alert}], stream=True
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield f"data: {delta}\n\n"        # SSE format
    yield "data: [DONE]\n\n"

@app.post("/v1/triage/stream")
async def triage_stream(req: TriageRequest):
    return StreamingResponse(token_stream(req.alert), media_type="text/event-stream")
```

## 4.5 Lifespan (create clients once, not per request)
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.llm = AsyncOpenAI()
    app.state.http = httpx.AsyncClient(timeout=10)
    yield
    await app.state.http.aclose()

app = FastAPI(lifespan=lifespan)
```

## 4.6 Errors, middleware, background tasks
```python
from fastapi.responses import JSONResponse

@app.exception_handler(ValidationError)
async def validation_handler(request, exc):
    return JSONResponse(status_code=422, content={"error": {"message": str(exc)}})

@app.middleware("http")
async def add_request_id(request, call_next):
    rid = request.headers.get("x-request-id", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["x-request-id"] = rid
    return response

@app.post("/v1/triage")
async def triage(req: TriageRequest, bg: BackgroundTasks):
    result = await run_agent(req.alert)
    bg.add_task(audit_log, result)          # runs after response is sent
    return result
```

## 4.7 Testing (your TDD strength)
```python
from fastapi.testclient import TestClient
client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

# async tests
import pytest
@pytest.mark.asyncio
async def test_agent():
    result = await run_agent("test alert")
    assert result.severity in {"low", "medium", "high", "critical"}
```

## ✅ FastAPI checklist
- [ ] `@app.get/post/put/patch/delete`
- [ ] Body (Pydantic) · `Query` · `Path` · `Header` · `Form` · `File`
- [ ] `response_model=`, `status_code=`
- [ ] `HTTPException`, custom exception handlers
- [ ] `Depends()` — DI for auth / clients / DB
- [ ] `async def` vs `def` endpoints (FastAPI auto-threads `def`)
- [ ] **`StreamingResponse`** + SSE ← agents need this
- [ ] `lifespan` — startup/shutdown, shared clients
- [ ] `BackgroundTasks`
- [ ] Middleware, CORS
- [ ] Auto docs at `/docs` and `/redoc`
- [ ] `TestClient` + `pytest-asyncio`
- [ ] Run with `uvicorn` (prod: `uvicorn` workers behind a proxy)

## 📺 Videos
- **freeCodeCamp — "FastAPI Course for Beginners"** *(~4h; first 90 min at 1.5x is enough)*
- **ArjanCodes — "FastAPI Best Practices"** ⭐ *(how production code is structured)*
- **Tech With Tim — "FastAPI Tutorial"**
- **Patrick Loeber — "FastAPI Crash Course"**

## 📄 Articles
- **FastAPI Tutorial — User Guide** → `fastapi.tiangolo.com/tutorial/` ⭐⭐ *(best docs in Python — just work through it)*
- **FastAPI — Async** → `fastapi.tiangolo.com/async/` ⭐
- **FastAPI — Dependencies** → `fastapi.tiangolo.com/tutorial/dependencies/`
- **FastAPI — Bigger Applications** → `fastapi.tiangolo.com/tutorial/bigger-applications/` *(project structure)*
- **FastAPI — Custom/Streaming Responses** → `fastapi.tiangolo.com/advanced/custom-response/`

---
---

# 5 · Calling LLM APIs (OpenAI / Azure / OpenAI-compatible)

**Why your TL listed it — and read this carefully:** the fact that they said *"OpenAI/Azure/OpenAI-compatible"* strongly suggests your project routes through **Azure OpenAI or an internal gateway**, not public OpenAI. **Confirm this on day 1.**

## 5.1 The three client flavours — same SDK
```python
import os
from openai import AsyncOpenAI, AsyncAzureOpenAI

# (a) OpenAI direct
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# model="gpt-4o"

# (b) Azure OpenAI  ⚠️ different constructor + `model` = DEPLOYMENT NAME
client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),   # https://<res>.openai.azure.com/
    api_version="2024-10-21",                            # REQUIRED, pin it
)
# model="my-gpt4o-deployment"   ← NOT "gpt-4o"

# (c) Any OpenAI-compatible endpoint (internal gateway, vLLM, Ollama, LiteLLM, Together...)
client = AsyncOpenAI(
    api_key=os.getenv("INTERNAL_KEY"),
    base_url="https://internal-gateway.cisco.com/v1",    # ← just override base_url
)
```
> **Key gotchas:**
> - Azure needs `api_version` and uses **deployment name** where OpenAI uses model name.
> - Azure auth can also be **Entra ID / AAD token** instead of an API key (`azure_ad_token_provider=`).
> - Some internal gateways don't support every param (e.g. `response_format`, `tools`) — **test early**.

## 5.2 Chat completions — the core call
```python
resp = await client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a SOC triage agent."},
        {"role": "user",   "content": "Classify this alert: ..."},
    ],
    temperature=0.0,        # 0 for deterministic/classification work
    max_tokens=1000,
    timeout=30,
)
text  = resp.choices[0].message.content
usage = resp.usage          # prompt_tokens, completion_tokens, total_tokens → COST
```

**Message roles:** `system` (instructions) · `user` · `assistant` (model's past replies) · `tool` (tool results). The conversation is a **list you append to** — that's the agent loop.

## 5.3 Streaming
```python
stream = await client.chat.completions.create(
    model="gpt-4o", messages=msgs, stream=True
)
async for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

## 5.4 Production concerns (this is where your backend experience shines)
```python
from openai import RateLimitError, APITimeoutError, APIStatusError
import asyncio, random

async def call_llm_with_retry(**kwargs):
    for attempt in range(5):
        try:
            return await client.chat.completions.create(**kwargs)
        except (RateLimitError, APITimeoutError) as e:
            wait = (2 ** attempt) + random.random()      # exponential backoff + jitter
            await asyncio.sleep(wait)
        except APIStatusError as e:
            if e.status_code >= 500:
                await asyncio.sleep(2 ** attempt)
            else:
                raise                                    # 4xx = your bug, don't retry
    raise RuntimeError("LLM unavailable after retries")
```
- **Rate limits (`429`)** — retry with exponential backoff + jitter
- **Token counting / cost** — `tiktoken` to pre-count; `resp.usage` to post-count
- **Timeouts** — always set them
- **Idempotency** — LLM calls are cheap to retry; **tool calls may not be**
- **Prompt caching** — big cost saver on long system prompts
- **Logging** — log prompt, response, tokens, latency, model, request_id

## 5.5 Other providers (be aware)
- **Anthropic Claude** — `client.messages.create(...)`, `system=` is a top-level param (not a message), tool use is very similar in spirit
- **LiteLLM** — one wrapper over 100+ providers; useful if the project must be provider-agnostic

## ✅ LLM API checklist
- [ ] `AsyncOpenAI` vs `AsyncAzureOpenAI` vs `base_url=` override
- [ ] Azure: `api_version` + **deployment name** as `model`
- [ ] `chat.completions.create()` — messages, roles, temperature, max_tokens
- [ ] Streaming (`stream=True`)
- [ ] `resp.usage` → token accounting & cost
- [ ] Retries/backoff on `429`/`5xx`; don't retry `4xx`
- [ ] Timeouts everywhere
- [ ] `tiktoken` for pre-flight token counting
- [ ] Prompt caching
- [ ] Tool calling (`tools=`) ← see §6 and R1/R2
- [ ] Structured output (`response_format=`) ← see §6

## 📺 Videos
- **OpenAI DevDay talks** — structured outputs & function calling (official YouTube)
- **Search: `Azure OpenAI python tutorial`** — Microsoft Learn has official walkthroughs
- **DeepLearning.AI — "Building Systems with the ChatGPT API"** *(free short course)*

## 📄 Articles
- **OpenAI — API reference & guides** → `platform.openai.com/docs/` ⭐
- **OpenAI — Function calling** → `platform.openai.com/docs/guides/function-calling` ⭐⭐ **most important page for your project**
- **OpenAI — Structured Outputs** → `platform.openai.com/docs/guides/structured-outputs` ⭐⭐
- **Azure OpenAI — Quickstart** → `learn.microsoft.com/azure/ai-services/openai/quickstart` ⭐
- **Azure OpenAI — Switching from OpenAI** → search `learn.microsoft.com azure openai switching endpoints`
- **Anthropic — Tool use** → `docs.anthropic.com` → Tool use

---
---

# 6 · JSON parsing & structured outputs

**Why your TL listed it:** This is **the** core skill for tool development. The LLM must return machine-readable data, not prose — and your tools receive their arguments as JSON. You already parse JSON/CSV daily (S3 log framework); the new part is **making an LLM produce reliable JSON**.

## 6.1 Plain JSON in Python (you know this — the agent-specific bits)
```python
import json

d    = json.loads(s)                   # str  → dict
s    = json.dumps(d, indent=2, default=str)   # dict → str  (default=str handles datetime)
obj  = json.load(f)  /  json.dump(obj, f)     # file I/O
```
**Agent reality:** tool arguments arrive as a **JSON string**, always:
```python
args = json.loads(tool_call.function.arguments)   # ← this line is in every agent
```

## 6.2 Structured output — 4 escalating techniques

**(1) Just ask (worst — don't rely on it)**
```python
"Return JSON with keys severity, src_ip."      # model may add prose, markdown fences...
```

**(2) JSON mode — guarantees *valid JSON*, not your *schema***
```python
resp = await client.chat.completions.create(
    model="gpt-4o", messages=msgs,
    response_format={"type": "json_object"},   # must also say "JSON" in the prompt
)
data = json.loads(resp.choices[0].message.content)
```

**(3) ⭐ Structured Outputs with a Pydantic model — guarantees YOUR schema (use this)**
```python
resp = await client.chat.completions.parse(
    model="gpt-4o",
    messages=msgs,
    response_format=SecurityAlert,             # ← Pydantic model directly
)
alert: SecurityAlert = resp.choices[0].message.parsed   # already validated ✅
if resp.choices[0].message.refusal:                     # model may refuse
    handle_refusal()
```

**(4) Tool/function calling — structured *actions* (the agent mechanism)**
```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_ip_reputation",
        "description": "Look up threat intelligence reputation for an IP address.",
        "parameters": SecurityAlert.model_json_schema(),   # ⭐ Pydantic → schema
        "strict": True,                                     # enforce the schema
    },
}]
```

## 6.3 Defensive parsing — because reality bites
```python
import json, re
from pydantic import BaseModel, ValidationError

def extract_json(text: str) -> str:
    """LLMs love wrapping JSON in ```json fences and prose."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    if fenced:
        return fenced.group(1)
    braces = re.search(r"\{.*\}", text, re.S)      # first {...} block
    return braces.group(0) if braces else text

def parse_or_raise(text: str, model: type[BaseModel]):
    try:
        return model.model_validate_json(extract_json(text))
    except (ValidationError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid LLM output: {e}") from e
```

## 6.4 ⭐ The self-healing retry loop (very important pattern)
```python
async def get_structured(messages, model_cls, max_retries=3):
    for attempt in range(max_retries):
        resp = await client.chat.completions.create(model="gpt-4o", messages=messages)
        text = resp.choices[0].message.content
        try:
            return model_cls.model_validate_json(extract_json(text))
        except ValidationError as e:
            # Feed the LLM its own error and let it fix itself
            messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": f"That was invalid. Fix these errors and return ONLY valid JSON:\n{e}"},
            ]
    raise RuntimeError("LLM could not produce valid output")
```

## 6.5 Reliability tips that actually work
- Use **`Literal`/`Enum`** — never let the LLM invent a value
- **`Field(description=...)`** — this is a prompt; write it well
- **`temperature=0`** for extraction/classification
- Prefer **`response_format=<PydanticModel>`** over prompt-begging
- **Validate, then retry with the error** — self-healing beats hoping
- Handle **`refusal`** and truncation (`finish_reason == "length"`)
- **Log every raw LLM output** — you'll need it to debug schema failures

## ✅ JSON & structured output checklist
- [ ] `json.loads` / `json.dumps` (+ `default=str`)
- [ ] Tool args always arrive as a JSON string → `json.loads(tc.function.arguments)`
- [ ] JSON mode (`{"type": "json_object"}`) vs **Structured Outputs** (`response_format=Model`)
- [ ] `client.chat.completions.parse()` → `.parsed` (validated Pydantic object)
- [ ] `strict: True` in tool schemas
- [ ] `.model_json_schema()` → tool `parameters`
- [ ] Markdown-fence stripping / JSON extraction
- [ ] `ValidationError` → **self-healing retry loop**
- [ ] `refusal` + `finish_reason` handling
- [ ] `temperature=0`, `Literal`/`Enum` constraints

## 📺 Videos
- **Search: `OpenAI structured outputs tutorial python`**
- **Search: `OpenAI function calling python tutorial`** ⭐
- **DeepLearning.AI — "Functions, Tools and Agents with LangChain"** *(free)* ⭐

## 📄 Articles
- **OpenAI — Structured Outputs** → `platform.openai.com/docs/guides/structured-outputs` ⭐⭐
- **OpenAI — Function calling** → `platform.openai.com/docs/guides/function-calling` ⭐⭐
- **Pydantic — JSON Schema** → `docs.pydantic.dev/latest/concepts/json_schema/`
- **Instructor library docs** → `python-useinstructor.com` *(library purpose-built for structured LLM output + retries — worth 15 min)*

---
---

# 7 · LangChain / LlamaIndex / LangGraph (overview)

**Why your TL listed it:** you need to know **which tool solves which problem** — and which one your project uses. **Don't learn all three.** Ask your TL.

## 7.1 The map
| Framework | Purpose | Use when |
|---|---|---|
| **LangChain** | General LLM app framework — models, prompts, tools, memory, 100s of integrations | Gluing LLM + tools + data together |
| **LangGraph** *(by LangChain)* | **Agents as state machines** — cycles, branching, human-in-the-loop, persistence, streaming | ⭐ **Agent implementation — most likely YOUR project** |
| **LlamaIndex** | **Data/RAG-first** — ingestion, chunking, indexing, retrieval, query engines | "Chat over our documents/knowledge base" |

> **Rule of thumb:** *Agents + tools* → **LangGraph**. *RAG over documents* → **LlamaIndex**. They interoperate; many projects use both.

## 7.2 LangChain — the pieces
```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

# A "tool" is just a function + a docstring
@tool
def get_ip_reputation(ip: str) -> str:
    """Look up threat reputation for an IP address."""   # ← docstring = LLM's description
    return f"{ip}: malicious, score 87"

llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools([get_ip_reputation])     # attach tools

# LCEL — pipe syntax
prompt = ChatPromptTemplate.from_template("Triage: {alert}")
chain = prompt | llm_with_tools
result = await chain.ainvoke({"alert": "..."})           # note: ainvoke = async
```
**Know:** `ChatModel`, `@tool`, `bind_tools`, LCEL (`|`), `invoke`/`ainvoke`/`stream`, output parsers, memory, `Document`, retrievers.

## 7.3 LangGraph — agents as graphs ⭐ (likely your project)
```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

# Fastest path — prebuilt ReAct agent
agent = create_react_agent(llm, tools=[get_ip_reputation])
result = await agent.ainvoke({"messages": [("user", "Triage 10.0.0.1")]})

# Custom graph — full control
class State(TypedDict):
    messages: list

builder = StateGraph(State)
builder.add_node("agent", call_model)
builder.add_node("tools", run_tools)
builder.set_entry_point("agent")
builder.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
builder.add_edge("tools", "agent")          # ← the cycle: agent → tools → agent
graph = builder.compile(checkpointer=memory)
```
**Know:** `StateGraph`, nodes, edges, **conditional edges**, cycles, `State` (TypedDict), `checkpointer` (persistence/memory), human-in-the-loop (`interrupt`), streaming, `create_react_agent`.

## 7.4 LlamaIndex — RAG
```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

docs  = SimpleDirectoryReader("./docs").load_data()   # Document
index = VectorStoreIndex.from_documents(docs)         # chunk → embed → index
qe    = index.as_query_engine()
resp  = await qe.aquery("What is our ZTNA policy?")
```
**Know:** `Document` → `Node` (chunk) → `Index` → `Retriever` → `QueryEngine`; node parsers/chunking; vector stores; also has agents/tools (`FunctionTool`).

## 7.5 Framework vs. raw SDK — the real decision
| | Raw OpenAI SDK | LangGraph/LangChain |
|---|---|---|
| Control | Total | Abstracted |
| Debuggability | Easy | Harder (magic) |
| Speed to build | Slower | Faster |
| Swap providers | Manual | Built in |
| Persistence/HITL/streaming | You build it | Built in |
> **Honest advice:** build your **first** agent with the raw SDK (§R1) so you understand the loop. Then adopt whatever your team uses. Frameworks hide the loop — if you never saw it, you can't debug it.

## ✅ Framework checklist
- [ ] LangChain vs LangGraph vs LlamaIndex — which solves what
- [ ] LangChain: `@tool`, `bind_tools`, LCEL, `ainvoke`
- [ ] LangGraph: `StateGraph`, nodes/edges, conditional edges, cycles, checkpointer, `create_react_agent`
- [ ] LlamaIndex: Document → Node → Index → QueryEngine
- [ ] When to use a framework vs raw SDK
- [ ] **Find out which one your project uses — then go deep on only that one**

## 📺 Videos
- **DeepLearning.AI — "AI Agents in LangGraph"** *(FREE short course)* ⭐⭐ **most relevant course to your project**
- **DeepLearning.AI — "Functions, Tools and Agents with LangChain"** *(free)* ⭐
- **LangChain official YouTube — LangGraph quickstarts** ⭐
- **James Briggs — LangChain/LangGraph series** — very practical
- **LlamaIndex official — "Getting Started"**

## 📄 Articles
- **Anthropic — "Building effective agents"** ⭐⭐⭐ *(search: `Anthropic building effective agents`)* — **the best article written on agent design. If you read one thing, read this.**
- **LangGraph — Quickstart / Build an agent** → `langchain-ai.github.io/langgraph/` ⭐⭐
- **LangGraph — Agentic concepts** → `langchain-ai.github.io/langgraph/concepts/agentic_concepts/`
- **LangChain — Tool calling** → `python.langchain.com/docs/concepts/tool_calling/` ⭐
- **LlamaIndex — Starter tutorial** → `docs.llamaindex.ai/en/stable/getting_started/starter_example/`

---
---

# R1 · Agent implementation

**This is your job #1.** An "agent" is not magic — it is a **loop**: call the LLM, if it asks for tools, run them, feed results back, repeat until it gives a final answer.

## R1.1 The agent loop (memorize this — it IS the agent)
```
┌─────────────────────────────────────────────┐
│ messages = [system, user]                   │
│                                             │
│ LOOP (max N steps):                         │
│   resp = LLM(messages, tools=TOOLS)         │
│   messages.append(resp.message)             │
│                                             │
│   if no resp.tool_calls:  ──► DONE, return  │
│                                             │
│   for each tool_call:                       │
│       args   = json.loads(tc.arguments)     │
│       result = await TOOL[tc.name](**args)  │
│       messages.append({role:"tool",         │
│                        tool_call_id: tc.id, │
│                        content: result})    │
│   ──► loop again                            │
└─────────────────────────────────────────────┘
```

## R1.2 Full implementation (raw SDK — understand this before any framework)
```python
import json, asyncio, logging
from openai import AsyncOpenAI

log = logging.getLogger(__name__)
client = AsyncOpenAI()

async def run_agent(user_input: str, max_steps: int = 6) -> SecurityAlert:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_input},
    ]

    for step in range(max_steps):
        resp = await client.chat.completions.create(
            model="gpt-4o", messages=messages, tools=TOOL_SCHEMAS, temperature=0,
        )
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:                      # ← LLM is done
            break

        # ⭐ Run all requested tools CONCURRENTLY (this is why you learned asyncio)
        results = await asyncio.gather(
            *[execute_tool(tc) for tc in msg.tool_calls],
            return_exceptions=True,
        )
        for tc, result in zip(msg.tool_calls, results):
            content = f"ERROR: {result}" if isinstance(result, Exception) else str(result)
            messages.append({
                "role": "tool", "tool_call_id": tc.id, "content": content,
            })
    else:
        log.warning("agent hit max_steps=%d", max_steps)

    # Final pass — force structured output
    final = await client.chat.completions.parse(
        model="gpt-4o",
        messages=messages + [{"role": "user", "content": "Give your final verdict."}],
        response_format=SecurityAlert,
    )
    return final.choices[0].message.parsed


async def execute_tool(tool_call) -> str:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)     # JSON parsing
    fn   = TOOL_REGISTRY.get(name)
    if fn is None:
        return f"ERROR: unknown tool {name}"
    try:
        return await asyncio.wait_for(fn(**args), timeout=15)   # ALWAYS timeout
    except asyncio.TimeoutError:
        return f"ERROR: tool {name} timed out"
    except Exception as e:
        log.exception("tool %s failed", name)
        return f"ERROR: {e}"                             # let the LLM see + recover
```

## R1.3 Agent design patterns (from Anthropic's "Building effective agents")
| Pattern | What | Use when |
|---|---|---|
| **Prompt chaining** | Fixed sequence of LLM calls | Task decomposes predictably |
| **Routing** | Classify input → send to a specialist | Distinct input categories |
| **Parallelization** | Run several LLM calls concurrently, aggregate | Independent subtasks (`gather`!) |
| **Orchestrator–workers** | A lead LLM delegates to workers | Dynamic subtasks |
| **Evaluator–optimizer** | One generates, another critiques, loop | Quality matters, iterate |
| **Autonomous agent** | LLM + tools in an open loop | Open-ended, unpredictable path |
> ⭐ **Start with the simplest thing that works.** Most "agent" problems are really a chain or a router. Full autonomy is expensive, slower, and harder to debug.

## R1.4 Production concerns (your backend experience matters here)
- **Step cap** (`max_steps`) — or the agent loops forever and burns money
- **Cost cap** — track tokens per run; abort past a budget
- **Timeouts** per tool and per run
- **Error → LLM**, don't crash: return `"ERROR: ..."` as tool output and let it recover
- **Idempotency** — a retried agent must not execute a destructive tool twice
- **Determinism** — `temperature=0` for triage/classification
- **Memory** — short-term = the `messages` list; long-term = a DB/vector store
- **Human-in-the-loop** — require approval before destructive actions
- **Observability** — log every step, tool call, token count, latency (LangSmith/Langfuse)
- **Guardrails** — validate tool args before executing; least-privilege tools

## ✅ Agent checklist
- [ ] I can write the agent loop from scratch, from memory
- [ ] Tool calls run **concurrently** with `asyncio.gather()`
- [ ] `max_steps`, per-tool timeouts, cost cap
- [ ] Tool errors returned to the LLM, not raised
- [ ] Final answer forced through a Pydantic schema
- [ ] I know the 6 agent patterns and pick the simplest
- [ ] Logging/tracing on every step

## 📄 Must-read
- **Anthropic — "Building effective agents"** ⭐⭐⭐
- **OpenAI — Function calling guide** ⭐⭐
- **LangGraph — Agentic concepts** ⭐

---
---

# R2 · Tool development

**This is your job #2.** A "tool" is just **a function + a schema the LLM can read**. The quality of your `description` fields determines whether the agent works.

## R2.1 Anatomy of a tool
```python
# 1) The Pydantic input schema — descriptions are PROMPTS for the LLM
class IPReputationArgs(BaseModel):
    ip: str = Field(description="IPv4 address to look up, e.g. 10.20.30.40")
    include_history: bool = Field(False, description="Include 30-day sighting history")

# 2) The implementation — async, timeout-bounded, error-safe
async def get_ip_reputation(ip: str, include_history: bool = False) -> str:
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(f"{TI_BASE}/ip/{ip}", params={"history": include_history},
                           headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        d = r.json()
        # 3) Return LLM-friendly output — concise, not a giant JSON blob
        return f"IP {ip}: score={d['score']}/100, verdict={d['verdict']}, last_seen={d['last_seen']}"

# 4) The schema the LLM sees
TOOL_SCHEMAS = [{
    "type": "function",
    "function": {
        "name": "get_ip_reputation",
        "description": "Look up threat-intelligence reputation for an IPv4 address. "
                       "Use when an alert contains a suspicious external IP.",   # ← WHEN to use it
        "parameters": IPReputationArgs.model_json_schema(),
        "strict": True,
    },
}]

# 5) The registry
TOOL_REGISTRY = {"get_ip_reputation": get_ip_reputation}
```

## R2.2 Rules for tools that actually work
1. **Describe *when* to use it, not just what it does.** `"Use when an alert contains an external IP"` beats `"Gets IP reputation"`.
2. **Descriptions on every field.** The LLM reads them. Include an example value.
3. **Constrain with `Literal`/`Enum`** — never accept free-text where a set of values exists.
4. **Return concise, natural-language-ish output.** Don't dump 4KB of JSON into the context — summarize.
5. **Never raise — return `"ERROR: ..."`.** The LLM can then retry or route around it.
6. **Always `async`, always timeout-bounded.**
7. **Few, well-named tools > many overlapping ones.** >10–15 tools and the LLM starts mis-picking.
8. **Least privilege.** A read tool and a *block-this-IP* tool are very different risks.
9. **Make destructive tools require confirmation** (human-in-the-loop) or an idempotency key.
10. **Test tools standalone** with pytest — before ever plugging in the LLM.

## R2.3 Tool categories you'll likely build
- **Retrieval/lookup** — query Splunk, a DB, a knowledge base, threat intel
- **Enrichment** — IP/domain/hash reputation, geo, asset owner lookup
- **Action** — block IP, create Jira ticket, quarantine host ← **destructive, guard these**
- **Computation** — parse logs, aggregate, calculate
- **Handoff** — escalate to a human / another agent

## R2.4 Testing tools (TDD — your strength)
```python
import pytest

@pytest.mark.asyncio
async def test_ip_reputation_success(respx_mock):
    respx_mock.get("https://ti/ip/1.2.3.4").respond(json={"score": 87, "verdict": "malicious", "last_seen": "2h"})
    out = await get_ip_reputation("1.2.3.4")
    assert "87" in out and "malicious" in out

@pytest.mark.asyncio
async def test_ip_reputation_timeout(respx_mock):
    respx_mock.get("https://ti/ip/1.2.3.4").mock(side_effect=httpx.TimeoutException("x"))
    with pytest.raises(httpx.TimeoutException):
        await get_ip_reputation("1.2.3.4")

def test_schema_is_valid():
    schema = IPReputationArgs.model_json_schema()
    assert "ip" in schema["properties"]
```

## ✅ Tool checklist
- [ ] Pydantic args model with rich `description`s
- [ ] `.model_json_schema()` → tool `parameters`, `strict: True`
- [ ] Async implementation, timeout, error → string not exception
- [ ] Concise LLM-friendly return value
- [ ] Registry mapping name → function
- [ ] Least privilege; destructive tools gated
- [ ] Unit tested standalone

## 📄 Articles
- **OpenAI — Function calling** ⭐⭐ (best practices section especially)
- **Anthropic — Tool use** → `docs.anthropic.com` (their tool-description guidance is excellent)
- **LangChain — Custom tools** → `python.langchain.com/docs/how_to/custom_tools/`

---
---

# R3 · API integration

**This is your job #3** — and it's the part you're **already strongest at** (4.5 yrs of REST + Cisco SSE API integration + SOAR connectors). Here's how it changes in an agent context.

## R3.1 A production HTTP client
```python
import httpx, asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class InternalAPIClient:
    def __init__(self, base_url: str, token_provider):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(connect=5, read=15, write=5, pool=5),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
        )
        self._token_provider = token_provider
        self._sem = asyncio.Semaphore(10)          # don't hammer internal services

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def get(self, path: str, **kwargs) -> dict:
        async with self._sem:
            token = await self._token_provider()          # cached OAuth2 token
            r = await self._client.get(
                path, headers={"Authorization": f"Bearer {token}"}, **kwargs
            )
            if r.status_code == 429:                       # rate limited
                await asyncio.sleep(int(r.headers.get("Retry-After", 5)))
                raise httpx.NetworkError("rate limited")   # → triggers retry
            r.raise_for_status()
            return r.json()

    async def aclose(self):
        await self._client.aclose()
```

## R3.2 OAuth2 client-credentials with token caching (likely for internal Cisco APIs)
```python
import time

class TokenProvider:
    def __init__(self, token_url, client_id, client_secret):
        self._url, self._id, self._secret = token_url, client_id, client_secret
        self._token, self._expires_at = None, 0
        self._lock = asyncio.Lock()

    async def __call__(self) -> str:
        async with self._lock:                        # avoid thundering-herd refresh
            if self._token and time.time() < self._expires_at - 60:   # 60s safety margin
                return self._token
            async with httpx.AsyncClient() as c:
                r = await c.post(self._url, data={
                    "grant_type": "client_credentials",
                    "client_id": self._id,
                    "client_secret": self._secret,
                })
                r.raise_for_status()
                d = r.json()
            self._token = d["access_token"]
            self._expires_at = time.time() + d.get("expires_in", 3600)
            return self._token
```

## R3.3 Resilience patterns (bring your backend discipline)
- **Retries + exponential backoff + jitter** — on timeouts, `429`, `5xx`. **Never** retry `4xx`.
- **Respect `Retry-After`** headers.
- **Circuit breaker** — stop calling a dead service; fail fast (`pybreaker` or roll your own).
- **Timeouts at every layer** — connect, read, total, and per-agent-run.
- **Connection pooling** — one `AsyncClient` for the app lifetime, not per call.
- **Concurrency limit** (`Semaphore`) — protect internal services from your agent's `gather()`.
- **Idempotency keys** on action endpoints — an agent retry must not block an IP twice.
- **Pagination** — handle it inside the tool; return a summary, not 10k rows.
- **Caching** — cache expensive lookups (Redis; you know this) — agents re-query the same IP constantly.
- **Secrets** — env/vault, never hardcoded. `pydantic-settings` validates at startup.
- **Structured logging** — request_id, latency, status, upstream service. Correlate agent step → API call.

## R3.4 Two directions of integration
1. **Inbound** — your agent *is* an API (FastAPI). Auth, validation, streaming/`202`, rate limits, docs.
2. **Outbound** — your tools *call* APIs (httpx). Auth, retries, timeouts, circuit breakers, caching.
> Both matter. §3/§4 cover inbound; this section covers outbound.

## ✅ API integration checklist
- [ ] Single pooled `httpx.AsyncClient` (lifespan-managed)
- [ ] OAuth2 client-credentials + token caching + refresh
- [ ] Retries with exponential backoff + jitter (`tenacity`)
- [ ] Respect `429` / `Retry-After`; never retry `4xx`
- [ ] Timeouts (connect/read/total) everywhere
- [ ] `Semaphore` concurrency limit
- [ ] Circuit breaker on flaky upstreams
- [ ] Idempotency keys for destructive calls
- [ ] Pagination handled inside the tool
- [ ] Caching (Redis) for repeat lookups
- [ ] Secrets via `pydantic-settings` / vault
- [ ] Structured logging + request IDs
- [ ] Mocked tests (`respx`)

## 📄 Articles
- **httpx — Advanced usage** → `python-httpx.org/advanced/`
- **tenacity docs** → `tenacity.readthedocs.io`
- **Microsoft — Retry & Circuit Breaker patterns** → `learn.microsoft.com/azure/architecture/patterns/retry` ⭐
- **Stripe — Idempotent requests** *(read how they design it)*

---
---

# 🏗️ THE BUILD — one app that proves all of it

**Don't do 7 disconnected tutorials.** Build one thing that exercises **every TL item and all 3 responsibilities**.

```
POST /v1/triage  {"alert": "..."}
  → FastAPI                     ✅ REST APIs, FastAPI
  → Pydantic request validation ✅ Pydantic
  → async agent loop            ✅ asyncio, AGENT IMPLEMENTATION
  → LLM requests a tool         ✅ Calling LLM APIs (OpenAI/Azure/compatible)
  → tools run concurrently      ✅ asyncio.gather, TOOL DEVELOPMENT
  → tool calls an external API  ✅ API INTEGRATION (httpx, retries, auth)
  → args parsed from JSON       ✅ JSON parsing
  → final answer typed via Pydantic ✅ Structured outputs
  → (stretch) rebuild in LangGraph  ✅ LangChain/LangGraph
```

## `main.py` — complete, runnable
```python
import asyncio, json, logging, os
from contextlib import asynccontextmanager
from typing import Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException, Depends
from openai import AsyncOpenAI, RateLimitError, APITimeoutError
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agent")


# ---------- Config (Pydantic Settings) ----------
class Settings(BaseSettings):
    openai_api_key: str
    llm_base_url: str | None = None      # set for Azure/internal gateway
    model: str = "gpt-4o"
    max_agent_steps: int = 6
    class Config:
        env_file = ".env"

settings = Settings()


# ---------- Schemas (Pydantic + structured output) ----------
class TriageRequest(BaseModel):
    alert: str = Field(description="Raw security alert text")

class SecurityVerdict(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    src_ip: Optional[str] = Field(None, description="Source IP if present")
    action: Literal["block", "monitor", "ignore", "escalate"]
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(description="Short justification")

class IPReputationArgs(BaseModel):
    ip: str = Field(description="IPv4 address, e.g. 10.20.30.40")

class SplunkQueryArgs(BaseModel):
    query: str = Field(description="SPL query, e.g. 'index=security src_ip=10.0.0.1'")


# ---------- Tools (TOOL DEVELOPMENT + API INTEGRATION) ----------
async def get_ip_reputation(ip: str) -> str:
    """Outbound API integration with timeout + error safety."""
    try:
        r = await app.state.http.get(f"https://ti.internal/api/ip/{ip}")
        r.raise_for_status()
        d = r.json()
        return f"IP {ip}: score={d['score']}/100, verdict={d['verdict']}"
    except httpx.HTTPError as e:
        # MOCK fallback so this runs today without the real API:
        return f"IP {ip}: score=87/100, verdict=malicious, last_seen=2h ago (mock)"

async def query_splunk(query: str) -> str:
    await asyncio.sleep(0.3)                       # simulate latency
    return f"Splunk[{query}] → 42 events in last 24h, 3 distinct dest hosts (mock)"


TOOL_REGISTRY = {"get_ip_reputation": get_ip_reputation, "query_splunk": query_splunk}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_ip_reputation",
        "description": "Look up threat-intelligence reputation for an IPv4 address. "
                       "Use when the alert contains an external or suspicious IP.",
        "parameters": IPReputationArgs.model_json_schema(),
    }},
    {"type": "function", "function": {
        "name": "query_splunk",
        "description": "Run an SPL query against the security index to get historical context. "
                       "Use to check whether this activity has happened before.",
        "parameters": SplunkQueryArgs.model_json_schema(),
    }},
]


# ---------- Tool execution (JSON parsing + timeouts + error handling) ----------
async def execute_tool(tc) -> str:
    name = tc.function.name
    try:
        args = json.loads(tc.function.arguments)        # ← JSON parsing
    except json.JSONDecodeError as e:
        return f"ERROR: bad tool arguments: {e}"

    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return f"ERROR: unknown tool '{name}'"
    try:
        log.info("tool → %s(%s)", name, args)
        return await asyncio.wait_for(fn(**args), timeout=15)   # ← always timeout
    except asyncio.TimeoutError:
        return f"ERROR: tool '{name}' timed out"
    except Exception as e:
        log.exception("tool %s failed", name)
        return f"ERROR: {e}"                                     # LLM can recover


# ---------- LLM call with retry (production concern) ----------
async def llm(**kwargs):
    for attempt in range(4):
        try:
            return await app.state.llm.chat.completions.create(**kwargs)
        except (RateLimitError, APITimeoutError):
            await asyncio.sleep(2 ** attempt)
    raise HTTPException(503, "LLM unavailable")


# ---------- AGENT IMPLEMENTATION (the loop) ----------
SYSTEM_PROMPT = (
    "You are a SOC triage agent. Use the available tools to enrich the alert with "
    "threat intelligence and historical context, then give a final structured verdict. "
    "Call tools in parallel when possible. Be concise."
)

async def run_agent(alert: str) -> SecurityVerdict:
    messages: list = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"Triage this alert:\n{alert}"},
    ]

    for step in range(settings.max_agent_steps):
        resp = await llm(model=settings.model, messages=messages,
                         tools=TOOL_SCHEMAS, temperature=0)
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            break

        # ⭐ concurrent tool execution — this is why asyncio matters
        results = await asyncio.gather(
            *[execute_tool(tc) for tc in msg.tool_calls], return_exceptions=True
        )
        for tc, result in zip(msg.tool_calls, results):
            content = f"ERROR: {result}" if isinstance(result, Exception) else str(result)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": content})
    else:
        log.warning("hit max steps")

    # ---------- STRUCTURED OUTPUT (final, typed, validated) ----------
    final = await app.state.llm.chat.completions.parse(
        model=settings.model,
        messages=messages + [{"role": "user", "content": "Now give your final verdict."}],
        response_format=SecurityVerdict,
    )
    verdict = final.choices[0].message.parsed
    if verdict is None:
        raise HTTPException(502, "LLM refused or returned invalid output")
    return verdict


# ---------- FastAPI app (REST + lifespan + DI) ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.llm = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.llm_base_url,       # None → OpenAI; set → Azure/internal
    )
    app.state.http = httpx.AsyncClient(timeout=10)
    yield
    await app.state.http.aclose()

app = FastAPI(title="SOC Triage Agent", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/v1/triage", response_model=SecurityVerdict)
async def triage(req: TriageRequest):
    try:
        return await run_agent(req.alert)
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(422, detail=str(e))
    except Exception as e:
        log.exception("triage failed")
        raise HTTPException(500, detail=str(e))
```

**Run it:**
```bash
uvicorn main:app --reload
# → http://127.0.0.1:8000/docs
```
**Test payload:**
```json
{"alert": "Blocked outbound connection from 10.20.30.40 to known C2 domain evil.example.com — 40 attempts in 5 minutes"}
```

## Stretch goals (in order)
- [ ] Add `StreamingResponse` so the client sees each agent step live
- [ ] Add the **self-healing retry loop** (§6.4) around structured output
- [ ] Add OAuth2 `TokenProvider` (§R3.2) for a real internal API
- [ ] Add a **destructive** tool (`block_ip`) behind human approval
- [ ] Add pytest tests for tools + agent (mock the LLM)
- [ ] **Rebuild the same agent in LangGraph** and compare (§7.3)
- [ ] Add Redis caching for repeat IP lookups
- [ ] Add token/cost tracking per run

---
---

# ❓ Ask your TL these on day 1 (halves your learning surface)

> **Status check** — most of these are still genuinely open, even though the project got built:

1. **Which LLM provider?** OpenAI direct / **Azure OpenAI** / internal OpenAI-compatible gateway? *(Changes client setup and `model=` semantics.)* — ⚠️ still open; code supports all three via `LLM_BASE_URL`, but only public OpenAI has been tried, and it's currently blocked by a billing/quota issue on the key.
2. **Which framework?** **LangGraph** / LlamaIndex / LangChain / raw SDK? *(Don't learn all four.)* — ✅ hedged: both a raw hand-written loop and a LangGraph version were built side by side, reachable at `/triage` and `/triage-langgraph`. LlamaIndex still untouched.
3. **What tools will the agent call?** Which internal APIs, what auth (OAuth2? API key? mTLS?), rate limits? — ⚠️ still open; two example tools exist (IP reputation, Splunk query) but both return **mock data**, no real internal API wired in yet.
4. **Is RAG in scope**, or purely agent + tools? *(Determines whether LlamaIndex matters at all.)* — ⚠️ still open.
5. **Any destructive/action tools?** (block, quarantine, ticket) — if yes, **human-in-the-loop is a requirement**, not a nice-to-have. — ⚠️ still open; both current tools are read-only, no approval gate built yet.
6. **Where does it deploy?** (Docker/K8s — you already know this.) — ⚠️ started, not proven: a `Dockerfile` + `docker-compose.yml` exist in `agentic_platform` but haven't been build-tested.
7. **Observability** — LangSmith/Langfuse/internal? What must be logged? — ⚠️ still open; only basic Python logging exists so far.

---

# ⭐ If you only do 5 things today
1. ~~**`asyncio.gather()`** — understand it cold (§1.2)~~ ✅ done — used for real, runs tools concurrently in `agents/triage_agent.py`
2. ~~**Pydantic + `.model_json_schema()`** (§2.2)~~ ✅ done — `schemas/models.py`
3. **OpenAI Function Calling guide** — read end to end *(`platform.openai.com/docs/guides/function-calling`)* — still worth reading if you haven't
4. **Anthropic "Building effective agents"** — read it *(best agent article that exists)* — still worth reading if you haven't
5. ~~**Get `main.py` running** — one endpoint, two tools, one structured verdict~~ ✅ done, tested (10+ automated tests across both projects), and verified live — though no real AI response has come back yet due to the API key's billing/quota issue

---

# ✅ Master end-of-week checklist

**Python async**
- [ ] `async`/`await`, event loop, `asyncio.run`
- [ ] `gather()`, `create_task()`, `wait_for()`, `to_thread()`, `Semaphore`
- [ ] `httpx.AsyncClient`; never block the loop

**Pydantic**
- [ ] `BaseModel`, `Field(description=)`, `Literal`/`Enum`, validators
- [ ] `model_dump()` / `model_validate()` / **`model_json_schema()`**
- [ ] `ValidationError` → retry; `BaseSettings`

**REST APIs**
- [ ] Methods, status codes (`202`/`422`/`429`), idempotency, auth (OAuth2)
- [ ] Long-running patterns: SSE streaming vs `202`+polling vs webhooks

**FastAPI**
- [ ] Routes, Pydantic bodies, `response_model`, `Depends`, `HTTPException`
- [ ] `StreamingResponse`, `lifespan`, `BackgroundTasks`, `/docs`, `TestClient`

**LLM APIs**
- [ ] `AsyncOpenAI` / `AsyncAzureOpenAI` / `base_url=` override
- [ ] Azure: `api_version` + deployment name; streaming; `usage`; retries on `429`

**JSON & structured outputs**
- [ ] `json.loads(tc.function.arguments)`
- [ ] `response_format=<PydanticModel>` → `.parsed`
- [ ] Fence-stripping + self-healing retry loop

**LangChain/LangGraph/LlamaIndex**
- [ ] Which is for what; `@tool`, `bind_tools`, `StateGraph`, `create_react_agent`

**Responsibilities**
- [ ] I can write the **agent loop** from memory
- [ ] I can build a **tool** (schema + async impl + error-safe + tested)
- [ ] I can integrate an **API** (auth, retries, timeouts, circuit breaker, caching)
- [ ] `main.py` runs end to end 🎉

---

## 📌 How this fits your other plans
- **This project replaces Phases 1 & 3** of [GenAI_Career_Roadmap_60Days.md](GenAI_Career_Roadmap_60Days.md) — don't build agents at work *and* study agents at night. Same skill; do it once, deeply, at work.
- **Shrink interview prep** for these 4 weeks: **DSA 1 hr/day + applications 20 min/day** (see [Interview_Prep_Roadmap.md](Interview_Prep_Roadmap.md)). Resume the full roadmap (RAG, fine-tuning, eval, LLM security) after the project ships.
- **Take notes daily** — what the agent does, tools you built, problems solved, metrics (latency, accuracy, cost). This becomes your **strongest STAR story**: *"Built production agentic tooling at Cisco."* Worth more in an AI interview than any side project.
