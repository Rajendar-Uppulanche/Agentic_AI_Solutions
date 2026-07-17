"""
Bonus / stretch goal: the SAME job as triage_agent.py, rebuilt with LangGraph's
prebuilt agent instead of a hand-written loop. Also shared by both Flask and FastAPI.
"""
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from config import settings


@tool
async def get_ip_reputation_tool(ip: str) -> str:
    """Look up threat-intelligence reputation for an IPv4 address."""
    return f"IP {ip}: score=87/100, verdict=malicious, last_seen=2h ago (mock)"


_llm = ChatOpenAI(model=settings.model, api_key=settings.openai_api_key, base_url=settings.llm_base_url)
_graph_agent = create_agent(_llm, tools=[get_ip_reputation_tool])


async def run_langgraph_agent(alert: str) -> str:
    result = await _graph_agent.ainvoke({"messages": [("user", f"Triage this alert: {alert}")]})
    return result["messages"][-1].content
