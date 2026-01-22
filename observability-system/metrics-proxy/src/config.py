from pathlib import Path
import yaml


# Hot-reload support: cache queries and mtime
_QUERIES_CACHE = None
_QUERIES_MTIME = None

def load_queries(path: str | None = None) -> dict:
    global _QUERIES_CACHE, _QUERIES_MTIME
    if path is None:
        path = Path(__file__).parent / "queries.yaml"
    else:
        path = Path(path)
    if not path.exists():
        _QUERIES_CACHE = {}
        _QUERIES_MTIME = None
        return {}
    mtime = path.stat().st_mtime
    if _QUERIES_CACHE is not None and _QUERIES_MTIME == mtime:
        return _QUERIES_CACHE
    with open(path, "r") as fh:
        _QUERIES_CACHE = yaml.safe_load(fh) or {}
    _QUERIES_MTIME = mtime
    return _QUERIES_CACHE
