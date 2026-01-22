# Metrics Proxy

A lightweight, production-ready FastAPI service that exposes a single `/observations` endpoint for running curated PromQL queries and returning averaged numeric values per metric. Designed to provide a stable, minimal interface in front of Prometheus without exposing PromQL directly. The API is generic: if your query returns multiple series (e.g., via `by (...)`), you get a value per label; if it returns a single series, you get a single value.

## Features
- **Stable HTTP API**: Exposes curated PromQL queries via a single endpoint.
- **Generic Aggregation**: Returns a single value for single-series queries, or a dictionary of values per label for multi-series queries (e.g., `by (source)`).
- **Customizable Queries**: Supports user-defined queries via `queries.yaml`.
- **Flexible Deployment**: Runs seamlessly in Docker, Kubernetes, or standalone environments.
- **Minimal Dependencies**: Fast startup and low resource usage.

## Quick Start

### Local Development
1. Set up a virtual environment and install dependencies:
  ```bash
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```
2. Run the application:
  ```bash
  PROM_URL=http://127.0.0.1:9090 uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
  ```

### Docker
Build and run the Docker image:
  ```bash
  docker build -t metrics-proxy:latest -f Dockerfile .
  docker run -e PROM_URL="http://127.0.0.1:9090" -p 8000:8000 --rm metrics-proxy:latest
  ```
Mount a custom `queries.yaml` from the host:
  ```bash
  docker run -v /path/to/queries.yaml:/app/src/queries.yaml \
    -e PROM_URL="http://127.0.0.1:9090" -p 8000:8000 --rm metrics-proxy:latest
  ```

### Kubernetes
Mount a custom `queries.yaml` using a ConfigMap:
  ```bash
  kubectl create configmap metrics-proxy-queries \
    --from-file=queries.yaml=/path/to/queries.yaml -n <namespace>
  ```

Deployment snippet (mounting the ConfigMap):
  ```yaml
  volumeMounts:
    - name: queries
      mountPath: /app/src/queries.yaml
      subPath: queries.yaml
  volumes:
    - name: queries
      configMap:
        name: metrics-proxy-queries
  ```

## API Usage

### Endpoint
`POST /observations`

### Request Body
```json
{
  "queries": ["cpu_usage", "freshness"],
  "window_minutes": 5
}
```

### Response Shape
For a query that returns a single series (e.g., `cpu_usage`):
```json
{
  "results": {
    "cpu_usage": 0.42
  }
}
```
For a query that returns multiple series (e.g., `freshness: avg by (source) (freshness_good_batches_total)`):
```json
{
  "results": {
    "freshness": {
      "source=foo": 1.0,
      "source=bar": 2.0,
      "source=baz": 3.0
    }
  }
}
```

## Behavior & Semantics
- For each requested metric, the service calls Prometheus’ `/api/v1/query_range`.
- Computes an arithmetic mean for each returned series (e.g., per label group if using `by (...)`).
- If only one series is returned, a single value is returned. If multiple, a dictionary of label(s) to value is returned.
- Ignores non-numeric and `NaN` samples.
- Returns `0.0` if no numeric samples are found for a series.
- Prometheus target is configured via `PROM_URL` environment variable.
- Custom queries can be provided by mounting a `queries.yaml` file at `/app/src/queries.yaml`.
- The resolved `PROM_URL` is logged at startup.

## Example
Request:
```bash
curl -X POST http://127.0.0.1:8000/observations \
  -H "Content-Type: application/json" \
  -d '{"queries":["cpu_usage","freshness"],"window_minutes":5}'
```
Response:
```json
{
  "results": {
    "cpu_usage": 0.42,
    "freshness": {
      "source=foo": 1.0,
      "source=bar": 2.0
    }
  }
}
```


## Configuration Files
- `src/queries.yaml`: mapping of metric names to PromQL expressions.
- `metrics-proxy/Dockerfile`: container build definition.
- `metrics-proxy/Makefile`: build and publish automation.


### Directory Overview
```text
metrics-proxy/
├─ src/
│  ├─ main.py          # FastAPI application and /observations handler
│  ├─ prom_client.py   # Prometheus query_range HTTP client (httpx)
│  ├─ config.py        # YAML queries loader
│  ├─ aggregation.py   # Aggregation helpers (average_scalar_result)
│  └─ queries.yaml     # Default queries (key → PromQL)
├─ Dockerfile
├─ Makefile            # Build/push targets for images
├─ requirements.txt
└─ README.md
```

## Makefile Usage
Convenience targets for building and publishing Docker images:
```bash
# Build a local image with default registry/TAG
make docker-build
# Push a single-arch image (runs docker-build first)
make docker-push
# Build and push a multi-arch image (requires buildx)
make docker-pushx
```
Override defaults as needed:
```bash
make metrics-proxy REGISTRY=<your-registry> TAG=v1 docker-build
```