"""
Same loop as triage_agent.py, calling Vertex AI instead of OpenAI.

⚠️ Not live-tested — see llm/vertex_client.py for why, and the auth caveat.
Also unverified: whether Vertex's OpenAI-compat layer supports .parse() +
response_format the same way OpenAI does (same open question as the Gemini
version). If it errors, fall back to response_format={"type": "json_object"}
+ json.loads + SecurityVerdict.model_validate.
"""
import asyncio
import logging

from openai import APITimeoutError, RateLimitError

from config import settings
from llm.vertex_client import get_client
from schemas.models import SecurityVerdict
from tools.registry import TOOL_SCHEMAS, execute_tool

log = logging.getLogger("agent.vertex")

SYSTEM_PROMPT = (
    "You are a SOC triage agent. Use the available tools to enrich the alert with "
    "threat intelligence and historical context, then give a final structured verdict. "
    "Call tools in parallel when possible. Be concise."
)


async def call_llm(**kwargs):
    """Retry on rate limits / timeouts; anything else bubbles up immediately.

    Gets a fresh client (and therefore a fresh token) on every call — Vertex
    tokens expire after ~1 hour, unlike OpenAI/Gemini's static API keys.
    """
    for attempt in range(3):
        try:
            client = get_client()
            return await client.chat.completions.create(**kwargs)
        except (RateLimitError, APITimeoutError):
            await asyncio.sleep(min(2 ** attempt, 3))
    raise RuntimeError("Vertex AI unavailable after retries")


async def run_agent_vertex(alert: str) -> SecurityVerdict:
    """Same loop as triage_agent.run_agent — see docs/How_This_Project_Works.md for the walkthrough."""
    messages: list = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Triage this alert:\n{alert}"},
    ]

    for step in range(settings.max_agent_steps):
        resp = await call_llm(model=settings.vertex_model, messages=messages, tools=TOOL_SCHEMAS, temperature=0)
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

    client = get_client()
    final = await client.chat.completions.parse(
        model=settings.vertex_model,
        messages=messages + [{"role": "user", "content": "Give your final verdict."}],
        response_format=SecurityVerdict,
    )
    verdict = final.choices[0].message.parsed
    if verdict is None:
        raise RuntimeError("Vertex AI refused or returned invalid output")
    return verdict
