import json
import sys

import click

from .client import VMClient
from .config import Config
from .formatters import format_instant_result, format_summary
from .queries import QUERIES


def get_client() -> VMClient:
    return VMClient(Config.load())


def extract_scalar(data: dict) -> float | None:
    result = data.get("data", {}).get("result", [])
    if result and result[0].get("value"):
        try:
            return float(result[0]["value"][1])
        except (IndexError, ValueError, TypeError):
            return None
    return None


@click.group()
def cli():
    """GPU cluster metrics CLI - query VictoriaMetrics for GPU usage data."""
    pass


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def health(fmt):
    """Check VictoriaMetrics connection status."""
    client = get_client()
    result = client.health()
    if fmt == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        if result["status"] == "ok":
            click.echo(f"VictoriaMetrics: OK (version: {result['version']})")
        else:
            click.echo(f"VictoriaMetrics: ERROR - {result['error']}", err=True)
            sys.exit(1)


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def summary(fmt):
    """Show overall GPU cluster summary."""
    client = get_client()

    gpu_total = extract_scalar(client.query(QUERIES["gpu_capacity_total"]))
    gpu_allocated = extract_scalar(client.query(QUERIES["gpu_requested_total"]))
    gpu_idle = extract_scalar(client.query(QUERIES["gpu_idle_total"]))
    avg_util = extract_scalar(client.query(QUERIES["gpu_util_avg"]))

    if fmt == "json":
        click.echo(json.dumps({
            "gpu_total": gpu_total,
            "gpu_allocated": gpu_allocated,
            "gpu_idle": gpu_idle,
            "avg_utilization_percent": avg_util,
            "allocation_ratio_percent": (
                round(gpu_allocated / gpu_total * 100, 1)
                if gpu_total and gpu_allocated else None
            ),
        }, indent=2))
    else:
        click.echo(format_summary(
            gpu_total=int(gpu_total) if gpu_total else None,
            gpu_allocated=int(gpu_allocated) if gpu_allocated else None,
            gpu_idle=int(gpu_idle) if gpu_idle else None,
            avg_util=avg_util,
        ))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def nodes(fmt):
    """Show GPU allocation per node."""
    client = get_client()
    data = client.query(QUERIES["gpu_capacity_per_node"])
    requested_data = client.query(QUERIES["gpu_requested_per_node"])

    if fmt == "json":
        click.echo(json.dumps({
            "capacity": data.get("data", {}).get("result", []),
            "requested": requested_data.get("data", {}).get("result", []),
        }, indent=2, ensure_ascii=False))
    else:
        click.echo("=== GPU Per Node ===")
        click.echo("Capacity:")
        click.echo(format_instant_result(data))
        click.echo("\nRequested:")
        click.echo(format_instant_result(requested_data))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def jobs(fmt):
    """Show currently running GPU training jobs."""
    client = get_client()
    count_data = client.query(QUERIES["running_pods_gpu"])
    pods_data = client.query(QUERIES["pod_gpu_requests"])

    count = extract_scalar(count_data)

    if fmt == "json":
        click.echo(json.dumps({
            "running_gpu_pods": int(count) if count else 0,
            "pods": pods_data.get("data", {}).get("result", []),
        }, indent=2, ensure_ascii=False))
    else:
        click.echo(f"=== Running GPU Jobs: {int(count) if count else 0} ===")
        click.echo(format_instant_result(pods_data))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def idle(fmt):
    """Show idle GPU details."""
    client = get_client()
    data = client.query(QUERIES["gpu_idle_total"])
    per_node_capacity = client.query(QUERIES["gpu_capacity_per_node"])
    per_node_requested = client.query(QUERIES["gpu_requested_per_node"])

    total_idle = extract_scalar(data)

    if fmt == "json":
        click.echo(json.dumps({
            "total_idle_gpus": int(total_idle) if total_idle else 0,
            "capacity_per_node": per_node_capacity.get("data", {}).get("result", []),
            "requested_per_node": per_node_requested.get("data", {}).get("result", []),
        }, indent=2, ensure_ascii=False))
    else:
        click.echo(f"=== Idle GPUs: {int(total_idle) if total_idle else 'N/A'} ===")
        click.echo("\nCapacity per node:")
        click.echo(format_instant_result(per_node_capacity))
        click.echo("\nRequested per node:")
        click.echo(format_instant_result(per_node_requested))


@cli.command()
@click.argument("promql")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def query(promql, fmt):
    """Run a custom PromQL query."""
    client = get_client()
    data = client.query(promql)
    if fmt == "json":
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        click.echo(format_instant_result(data))


@cli.command()
def explore():
    """Discover available metrics and labels (useful after data starts flowing)."""
    client = get_client()
    labels = client.labels()
    click.echo(f"=== Available Labels ({len(labels)}) ===")
    for label in sorted(labels):
        click.echo(f"  {label}")

    click.echo("\n=== GPU-related Series ===")
    for pattern in ["{__name__=~'DCGM.*'}", "{__name__=~'kube.*gpu.*'}", "{__name__=~'nvidia.*'}"]:
        series = client.series(pattern)
        if series:
            click.echo(f"\n  Pattern: {pattern} ({len(series)} series)")
            for s in series[:5]:
                click.echo(f"    {s}")
            if len(series) > 5:
                click.echo(f"    ... and {len(series) - 5} more")


if __name__ == "__main__":
    cli()
