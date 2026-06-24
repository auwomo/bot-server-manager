import json
import sys

import click

from .client import VMClient
from .config import Config
from .formatters import (
    _extract_scalar,
    _extract_vector,
    format_errors,
    format_jobs,
    format_json,
    format_network,
    format_nodes,
    format_power,
    format_queue,
    format_report,
    format_storage,
    format_summary,
    format_temperature,
    format_utilization,
)
from .queries import (
    ERRORS,
    JOBS,
    NETWORK,
    NODES,
    POWER,
    QUEUE,
    STORAGE,
    SUMMARY,
    TEMPERATURE,
    UTILIZATION,
)


def get_client() -> VMClient:
    return VMClient(Config.load())


def _query_group(client: VMClient, queries: dict) -> dict:
    results = {}
    for key, promql in queries.items():
        data = client.query(promql)
        vector = _extract_vector(data)
        if not vector:
            results[key] = None
        elif len(vector) == 1:
            labels = {k: v for k, v in vector[0].get("metric", {}).items() if k != "__name__"}
            if not labels:
                results[key] = _extract_scalar(data)
            else:
                results[key] = vector
        else:
            results[key] = vector
    return results


@click.group()
def cli():
    """GPU cluster metrics CLI — query VictoriaMetrics for GPU usage data."""
    pass


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def health(fmt):
    """Check VictoriaMetrics connection status."""
    client = get_client()
    result = client.health()
    if fmt == "json":
        click.echo(format_json(result))
    elif result["status"] == "ok":
        click.echo(f"VictoriaMetrics: OK (version: {result['version']})")
    else:
        click.echo(f"VictoriaMetrics: ERROR — {result['error']}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def summary(fmt):
    """Show overall GPU cluster summary."""
    client = get_client()
    results = _query_group(client, SUMMARY)
    if fmt == "json":
        total = results.get("gpu_total")
        allocated = results.get("gpu_allocated")
        results["gpu_idle"] = (total - allocated) if total and allocated else None
        results["allocation_percent"] = round(allocated / total * 100, 1) if total and allocated else None
        click.echo(format_json(results))
    else:
        click.echo(format_summary(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def jobs(fmt):
    """Show currently running GPU training jobs."""
    client = get_client()
    results = _query_group(client, JOBS)
    pods = results.get("running_pods_with_gpu", [])
    by_ns = results.get("gpu_by_namespace", [])
    if fmt == "json":
        click.echo(format_json({
            "total_gpu_pods": len(pods),
            "pods": pods,
            "by_namespace": by_ns,
            "volcano_running": results.get("volcano_jobs_running"),
            "volcano_pending": results.get("volcano_jobs_pending"),
        }))
    else:
        click.echo(format_jobs(pods, by_ns))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def nodes(fmt):
    """Show per-node GPU status."""
    client = get_client()
    results = _query_group(client, NODES)
    util = results.get("util_per_node", [])
    temp = results.get("temp_per_node", [])
    power = results.get("power_per_node", [])
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_nodes(util, temp, power))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def utilization(fmt):
    """Show GPU utilization details and distribution."""
    client = get_client()
    results = _query_group(client, UTILIZATION)
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_utilization(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def power(fmt):
    """Show GPU power consumption."""
    client = get_client()
    results = _query_group(client, POWER)
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_power(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def temperature(fmt):
    """Show GPU temperature status."""
    client = get_client()
    results = _query_group(client, TEMPERATURE)
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_temperature(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def errors(fmt):
    """Detect GPU errors and node issues."""
    client = get_client()
    results = _query_group(client, ERRORS)
    if fmt == "json":
        click.echo(format_json({k: v if isinstance(v, list) else [] for k, v in results.items()}))
    else:
        click.echo(format_errors(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def network(fmt):
    """Show InfiniBand and NVLink network status."""
    client = get_client()
    results = _query_group(client, NETWORK)
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_network(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def queue(fmt):
    """Show Volcano scheduler queue status."""
    client = get_client()
    results = _query_group(client, QUEUE)
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_queue(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def storage(fmt):
    """Show GPFS storage status."""
    client = get_client()
    results = _query_group(client, STORAGE)
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_storage(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def report(fmt):
    """Generate full cluster status report (for Feishu group)."""
    client = get_client()
    summary_r = _query_group(client, SUMMARY)
    jobs_r = _query_group(client, JOBS)
    queue_r = _query_group(client, QUEUE)
    errors_r = _query_group(client, ERRORS)
    temp_r = _query_group(client, TEMPERATURE)
    power_r = _query_group(client, POWER)

    if fmt == "json":
        click.echo(format_json({
            "summary": summary_r,
            "jobs": jobs_r,
            "queue": queue_r,
            "errors": {k: v if isinstance(v, list) else [] for k, v in errors_r.items()},
            "temperature": temp_r,
            "power": power_r,
        }))
    else:
        pods = jobs_r.get("running_pods_with_gpu", [])
        if not isinstance(pods, list):
            pods = []
        ns_data = jobs_r.get("gpu_by_namespace", [])
        if not isinstance(ns_data, list):
            ns_data = []
        click.echo(format_report(
            summary=summary_r,
            jobs_pods=pods,
            jobs_ns=ns_data,
            queue=queue_r,
            errors={k: v for k, v in errors_r.items() if isinstance(v, list) and v},
            temp=temp_r,
            power=power_r,
        ))


@cli.command("query")
@click.argument("promql")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def query_cmd(promql, fmt):
    """Run a custom PromQL query."""
    client = get_client()
    data = client.query(promql)
    if fmt == "json":
        click.echo(format_json(data))
    else:
        vector = _extract_vector(data)
        if not vector:
            click.echo("(no data)")
        else:
            for item in vector:
                m = item["metric"]
                v = item["value"][1]
                name = m.pop("__name__", "")
                labels = ", ".join(f'{k}={v}' for k, v in sorted(m.items()))
                click.echo(f"  {name}{{{labels}}}: {v}")


@cli.command()
def explore():
    """Discover available metrics and labels."""
    client = get_client()
    labels = client.labels()
    click.echo(f"=== Available Labels ({len(labels)}) ===")
    for label in sorted(labels):
        click.echo(f"  {label}")

    click.echo("\n=== GPU-related Series ===")
    for pattern in [
        '{__name__=~"DCGM.*"}',
        '{__name__=~"kube.*gpu.*"}',
        '{__name__=~"node_gpu.*"}',
        '{__name__=~"volcano.*"}',
        '{__name__=~"iblinkinfo.*"}',
        '{__name__=~"gpfs.*"}',
    ]:
        series = client.series(pattern)
        if series:
            names = set(s.get("__name__", "") for s in series)
            click.echo(f"\n  {pattern}: {len(series)} series, {len(names)} metrics")
            for n in sorted(names)[:10]:
                click.echo(f"    {n}")


if __name__ == "__main__":
    cli()
