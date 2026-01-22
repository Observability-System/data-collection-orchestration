from typing import Any
import math


def average_scalar_result(data: Any) -> Any:
    """
    Generic aggregation:
    - If Prometheus returns a single series, return a single average value.
    - If multiple series (e.g., from `by (...)`), return a dict mapping label(s) to average per series.
    - If no numeric samples, return 0.0 or empty dict.
    """
    if not isinstance(data, dict) or data.get("resultType") != "matrix":
        return None

    series = data.get("result", [])
    if not series:
        return 0.0

    # If only one series, aggregate all its values
    if len(series) == 1:
        vals = series[0].get("values", [])
        nums = [float(v) for _, v in vals if _is_number(v)]
        if not nums:
            return 0.0
        return sum(nums) / len(nums)

    # Multiple series: aggregate per label (e.g., per source)
    result = {}
    for s in series:
        # Use all label keys except '__name__' as the group key
        labels = s.get("metric", {})
        key = _label_key(labels)
        vals = s.get("values", [])
        nums = [float(v) for _, v in vals if _is_number(v)]
        if nums:
            result[key] = sum(nums) / len(nums)
        else:
            result[key] = 0.0
    return result

def _is_number(v):
    try:
        f = float(v)
        return not math.isnan(f)
    except Exception:
        return False

def _label_key(labels: dict) -> str:
    # Remove __name__ and join remaining labels for key
    return ",".join(f"{k}={v}" for k, v in sorted(labels.items()) if k != "__name__") or "_"
