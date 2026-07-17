import asyncio
import json
import logging

from tools.ip_reputation import get_ip_reputation
from tools.splunk import query_splunk

log = logging.getLogger("tools")

TOOL_REGISTRY = {
    "get_ip_reputation": get_ip_reputation,
    "query_splunk": query_splunk,
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_ip_reputation",
        "description": "Look up threat-intelligence reputation for an IPv4 address. "
                       "Use when the alert contains an external or suspicious IP.",
        "parameters": {
            "type": "object",
            "properties": {"ip": {"type": "string", "description": "IPv4 address, e.g. 10.20.30.40"}},
            "required": ["ip"],
        },
    }},
    {"type": "function", "function": {
        "name": "query_splunk",
        "description": "Run an SPL query against the security index for historical context. "
                       "Use to check whether this activity has happened before.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "SPL query, e.g. 'index=security src_ip=10.0.0.1'"}},
            "required": ["query"],
        },
    }},
]


async def execute_tool(tool_call) -> str:
    """JSON parsing + timeout + error safety — the LLM sees errors, never a crash."""
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
