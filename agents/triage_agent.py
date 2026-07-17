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
    """The agent loop — this is the ONE implementation both Flask and FastAPI call into."""
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

        # run every tool the LLM asked for CONCURRENTLY — this is asyncio.gather in action
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
