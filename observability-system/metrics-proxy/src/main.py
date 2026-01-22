from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from . import prom_client, config
import logging

logger = logging.getLogger("metrics-proxy")
from . import aggregation
from contextlib import asynccontextmanager
import time


@asynccontextmanager
async def lifespan(app: FastAPI):
    global QUERIES
    # Always load queries from config at startup.
    QUERIES = config.load_queries()
    # Log resolved Prometheus URL for visibility (can be overridden with PROM_URL env)
    try:
        resolved = prom_client.PROM_URL
    except Exception:
        resolved = None
    logger.info(f"Resolved PROM_URL={resolved}")
    yield


app = FastAPI(title="Prometheus Observations API", lifespan=lifespan)


class ObservationsRequest(BaseModel):
    # list of named queries (keys defined in app/queries.yaml)
    queries: List[str]
    # required lookback window in minutes (applies to all queries)
    window_minutes: int = Field(..., gt=0)
    # optional end timestamp (unix seconds). If omitted, server uses now.
    end_ts: Optional[float] = None
    # optional step in seconds for range queries. If not provided, server will choose a default.
    step_seconds: Optional[int] = None
    # aggregation is always performed (average across series)



@app.post("/observations")
async def observations(req: ObservationsRequest):
    # Always reload queries.yaml if changed
    queries = config.load_queries()
    # compute shared time window and step (clients provide minutes)
    end_ts = req.end_ts or time.time()
    window_seconds = float(req.window_minutes * 60)
    start_ts = end_ts - window_seconds
    if req.step_seconds and req.step_seconds > 0:
        step = int(req.step_seconds)
    else:
        step = max(1, int(window_seconds // 100))

    results = {}
    for name in req.queries:
        if name not in queries:
            raise HTTPException(status_code=400, detail=f"Unknown query: {name}")
        q = queries[name]
        try:
            data = await prom_client.query_range_prometheus(q, start=start_ts, end=end_ts, step=step)
            # generic aggregation: single value or dict per label
            agg = aggregation.average_scalar_result(data)
            results[name] = agg
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))
    return results
