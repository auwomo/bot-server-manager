import json
from typing import Any


def format_value(value: Any) -> str:
    if isinstance(value, (int, float)):
        if value == int(value):
            return str(int(value))
        return f"{value:.2f}"
    return str(value)


def format_instant_result(data: dict, output_format: str = "text") -> str:
    if output_format == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)

    result = data.get("data", {}).get("result", [])
    if not result:
        return "(no data)"

    result_type = data.get("data", {}).get("resultType", "")

    if result_type == "scalar":
        return format_value(result[1])

    lines = []
    for item in result:
        metric = item.get("metric", {})
        value = item.get("value", [None, None])
        val = format_value(float(value[1])) if value[1] is not None else "N/A"

        label_parts = []
        for k, v in metric.items():
            if k == "__name__":
                continue
            label_parts.append(f"{k}={v}")

        name = metric.get("__name__", "")
        labels = "{" + ", ".join(label_parts) + "}" if label_parts else ""
        lines.append(f"  {name}{labels}: {val}")

    return "\n".join(lines)


def format_summary(
    gpu_total: int | None,
    gpu_allocated: int | None,
    gpu_idle: int | None,
    avg_util: float | None,
) -> str:
    lines = ["=== GPU Cluster Summary ==="]
    if gpu_total is not None:
        lines.append(f"  Total GPUs:     {gpu_total}")
    if gpu_allocated is not None:
        lines.append(f"  Allocated:      {gpu_allocated}")
    if gpu_idle is not None:
        lines.append(f"  Idle:           {gpu_idle}")
    if avg_util is not None:
        lines.append(f"  Avg Util:       {avg_util:.1f}%")
    if gpu_total and gpu_allocated:
        ratio = gpu_allocated / gpu_total * 100
        lines.append(f"  Alloc Ratio:    {ratio:.1f}%")
    return "\n".join(lines)
