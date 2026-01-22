import os
from typing import Any
import httpx

PROM_URL = os.getenv("PROM_URL", "http://10.0.2.79:9090")

async def query_range_prometheus(query: str, start: float, end: float, step: float, timeout: float = 20.0) -> Any:
    """Run a range Prometheus query (/api/v1/query_range).

    `start`/`end` are unix timestamps (float seconds). `step` is in seconds.
    """
    url = f"{PROM_URL.rstrip('/')}/api/v1/query_range"
    params = {"query": query, "start": str(start), "end": str(end), "step": str(step)}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    if data.get("status") != "success":
        raise RuntimeError("Prometheus returned non-success status")
    return data.get("data")
