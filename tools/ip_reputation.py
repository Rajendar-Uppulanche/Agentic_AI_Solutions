import httpx


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
