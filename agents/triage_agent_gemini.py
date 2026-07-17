"""
Same job as triage_agent.py, same loop, same tools — the only difference is
which LLM client it calls (Gemini instead of OpenAI). Kept as a separate file
(instead of editing triage_agent.py) so the working OpenAI path stays untouched.

⚠️ Not live-tested yet — no real Gemini key was available while building this.
Gemini's OpenAI-compatible endpoint supports chat.completions.create() reliably;
the structured-output call (.parse() + response_format=) below is the one part
that may need adjusting once tested against a real key — see the note near the
bottom of this file if it errors.
"""
import asyncio
import logging

from openai import APITimeoutError, RateLimitError

from config import settings
from llm.gemini_client import client
from schemas.models import SecurityVerdict
from tools.registry import TOOL_SCHEMAS, execute_tool

log = logging.getLogger("agent.gemini")

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
    raise RuntimeError("Gemini unavailable after retries")


async def run_agent_gemini(alert: str) -> SecurityVerdict:
    """Same loop as triage_agent.run_agent — see docs/How_This_Project_Works.md for the walkthrough."""
    messages: list = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Triage this alert:\n{alert}"},
    ]

    for step in range(settings.max_agent_steps):
        resp = await call_llm(model=settings.gemini_model, messages=messages, tools=TOOL_SCHEMAS, temperature=0)
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

    # ⚠️ Unverified: if Gemini's OpenAI-compat layer rejects .parse()/response_format,
    # switch to response_format={"type": "json_object"} + json.loads + SecurityVerdict.model_validate.
    final = await client.chat.completions.parse(
        model=settings.gemini_model,
        messages=messages + [{"role": "user", "content": "Give your final verdict."}],
        response_format=SecurityVerdict,
    )
    verdict = final.choices[0].message.parsed
    if verdict is None:
        raise RuntimeError("Gemini refused or returned invalid output")
    return verdict
