import asyncio


async def query_splunk(query: str) -> str:
    await asyncio.sleep(0.3)  # simulate network latency
    return f"Splunk[{query}] -> 42 events in last 24h, 3 distinct dest hosts (mock)"
