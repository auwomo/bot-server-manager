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
from . import queries as digua_q
from . import queries_school as school_q


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


def _get_queries(cluster: str, category: str) -> dict:
    """Get the query dict for a cluster and category."""
    cat_upper = category.upper()
    if cluster == "school":
        return getattr(school_q, cat_upper, {})
    return getattr(digua_q, cat_upper, {})


@click.group()
@click.option("--cluster", type=click.Choice(["digua", "school", "all"]), default="digua",
              help="Target cluster: digua (default), school, or all.")
@click.pass_context
def cli(ctx, cluster):
    """GPU cluster metrics CLI — query VictoriaMetrics for GPU usage data."""
    ctx.ensure_object(dict)
    ctx.obj["cluster"] = cluster


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
@click.pass_context
def summary(ctx, fmt):
    """Show overall GPU cluster summary."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    if cluster == "all":
        for c in ("digua", "school"):
            results = _query_group(client, _get_queries(c, "summary"))
            click.echo(f"\n[{c.upper()}]")
            if fmt == "json":
                click.echo(format_json(results))
            else:
                click.echo(format_summary(results))
        return

    results = _query_group(client, _get_queries(cluster, "summary"))
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
@click.pass_context
def jobs(ctx, fmt):
    """Show currently running GPU training jobs."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    if cluster == "all":
        for c in ("digua", "school"):
            click.echo(f"\n[{c.upper()}]")
            results = _query_group(client, _get_queries(c, "jobs"))
            if fmt == "json":
                click.echo(format_json(results))
            else:
                _print_jobs(results, c)
        return

    results = _query_group(client, _get_queries(cluster, "jobs"))
    if fmt == "json":
        click.echo(format_json(results))
    else:
        _print_jobs(results, cluster)


def _print_jobs(results: dict, cluster: str):
    """Format and print jobs based on cluster type."""
    if cluster == "school":
        running = results.get("running_jobs", [])
        if not isinstance(running, list):
            running = []
        pending_count = results.get("pending_job_count")
        by_user = results.get("gpu_by_user", [])

        lines = [f"=== SLURM 运行中的 GPU 任务 ({len(running)} 个) ==="]
        if by_user and isinstance(by_user, list):
            lines.append("\n  按用户:")
            for item in sorted(by_user, key=lambda x: float(x["value"][1]), reverse=True):
                user = item["metric"].get("user", "?")
                gpus = int(float(item["value"][1]))
                lines.append(f"    {user}: {gpus} GPUs")

        if running:
            lines.append("\n  任务列表:")
            for item in sorted(running, key=lambda x: float(x["value"][1]), reverse=True):
                m = item["metric"]
                job_id = m.get("job_id", "?")
                user = m.get("user", "?")
                partition = m.get("partition", "?")
                job_name = m.get("job_name", "")
                gpus = int(float(item["value"][1]))
                lines.append(f"    [{job_id}] {user}@{partition} — {job_name} ({gpus} GPU)")
        else:
            lines.append("  (无运行中的 GPU 任务)")

        if pending_count:
            lines.append(f"\n  排队中: {int(pending_count)} 个任务")
        click.echo("\n".join(lines))
    else:
        pods = results.get("running_pods_with_gpu", [])
        if not isinstance(pods, list):
            pods = []
        by_ns = results.get("gpu_by_namespace", [])
        if not isinstance(by_ns, list):
            by_ns = []
        click.echo(format_jobs(pods, by_ns))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def nodes(ctx, fmt):
    """Show per-node GPU status."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    if cluster == "all":
        for c in ("digua", "school"):
            click.echo(f"\n[{c.upper()}]")
            results = _query_group(client, _get_queries(c, "nodes"))
            if fmt == "json":
                click.echo(format_json(results))
            else:
                util = results.get("util_per_node", [])
                temp = results.get("temp_per_node", [])
                power = results.get("power_per_node", [])
                click.echo(format_nodes(util or [], temp or [], power or []))
        return

    results = _query_group(client, _get_queries(cluster, "nodes"))
    if fmt == "json":
        click.echo(format_json(results))
    else:
        util = results.get("util_per_node", [])
        temp = results.get("temp_per_node", [])
        power = results.get("power_per_node", [])
        click.echo(format_nodes(util or [], temp or [], power or []))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def utilization(ctx, fmt):
    """Show GPU utilization details and distribution."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    if cluster == "all":
        for c in ("digua", "school"):
            click.echo(f"\n[{c.upper()}]")
            results = _query_group(client, _get_queries(c, "utilization"))
            if fmt == "json":
                click.echo(format_json(results))
            else:
                click.echo(format_utilization(results))
        return

    results = _query_group(client, _get_queries(cluster, "utilization"))
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_utilization(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def power(ctx, fmt):
    """Show GPU power consumption."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    if cluster == "all":
        for c in ("digua", "school"):
            click.echo(f"\n[{c.upper()}]")
            results = _query_group(client, _get_queries(c, "power"))
            if fmt == "json":
                click.echo(format_json(results))
            else:
                click.echo(format_power(results))
        return

    results = _query_group(client, _get_queries(cluster, "power"))
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_power(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def temperature(ctx, fmt):
    """Show GPU temperature status."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    if cluster == "all":
        for c in ("digua", "school"):
            click.echo(f"\n[{c.upper()}]")
            results = _query_group(client, _get_queries(c, "temperature"))
            if fmt == "json":
                click.echo(format_json(results))
            else:
                click.echo(format_temperature(results))
        return

    results = _query_group(client, _get_queries(cluster, "temperature"))
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_temperature(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def errors(ctx, fmt):
    """Detect GPU errors and node issues."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    if cluster == "all":
        for c in ("digua", "school"):
            click.echo(f"\n[{c.upper()}]")
            results = _query_group(client, _get_queries(c, "errors"))
            if fmt == "json":
                click.echo(format_json({k: v if isinstance(v, list) else [] for k, v in results.items()}))
            else:
                click.echo(format_errors(results))
        return

    results = _query_group(client, _get_queries(cluster, "errors"))
    if fmt == "json":
        click.echo(format_json({k: v if isinstance(v, list) else [] for k, v in results.items()}))
    else:
        click.echo(format_errors(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def network(ctx, fmt):
    """Show network status (InfiniBand/NVLink)."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    if cluster == "all":
        for c in ("digua", "school"):
            queries = _get_queries(c, "network")
            if not queries:
                continue
            click.echo(f"\n[{c.upper()}]")
            results = _query_group(client, queries)
            if fmt == "json":
                click.echo(format_json(results))
            else:
                click.echo(format_network(results))
        return

    queries = _get_queries(cluster, "network")
    if not queries:
        click.echo("(此集群无网络监控数据)")
        return
    results = _query_group(client, queries)
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_network(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def queue(ctx, fmt):
    """Show scheduler queue status (Volcano/SLURM)."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    if cluster == "all":
        for c in ("digua", "school"):
            click.echo(f"\n[{c.upper()}]")
            results = _query_group(client, _get_queries(c, "queue"))
            if fmt == "json":
                click.echo(format_json(results))
            else:
                _print_queue(results, c)
        return

    results = _query_group(client, _get_queries(cluster, "queue"))
    if fmt == "json":
        click.echo(format_json(results))
    else:
        _print_queue(results, cluster)


def _print_queue(results: dict, cluster: str):
    """Format and print queue based on cluster type."""
    if cluster == "school":
        lines = ["=== SLURM 分区状态 ==="]
        partitions = results.get("partition_total_gpus", [])
        alloc_data = results.get("partition_allocated_gpus", [])
        idle_data = results.get("partition_idle_gpus", [])
        running_data = results.get("queue_running_jobs", [])
        pending_data = results.get("queue_pending_jobs", [])

        if not isinstance(partitions, list):
            partitions = [partitions] if partitions else []

        alloc_map = {}
        if isinstance(alloc_data, list):
            alloc_map = {r["metric"].get("partition", "?"): float(r["value"][1]) for r in alloc_data}
        idle_map = {}
        if isinstance(idle_data, list):
            idle_map = {r["metric"].get("partition", "?"): float(r["value"][1]) for r in idle_data}
        run_map = {}
        if isinstance(running_data, list):
            run_map = {r["metric"].get("partition", "?"): int(float(r["value"][1])) for r in running_data}
        pend_map = {}
        if isinstance(pending_data, list):
            pend_map = {r["metric"].get("partition", "?"): int(float(r["value"][1])) for r in pending_data}

        for item in partitions:
            if not isinstance(item, dict):
                continue
            name = item["metric"].get("partition", "?")
            total = int(float(item["value"][1]))
            alloc = int(alloc_map.get(name, 0))
            idle = int(idle_map.get(name, 0))
            running = run_map.get(name, 0)
            pending = pend_map.get(name, 0)
            lines.append(f"  {name}:")
            lines.append(f"    GPU: {total} 总 | {alloc} 已分配 | {idle} 空闲")
            lines.append(f"    任务: {running} 运行 | {pending} 排队")

        click.echo("\n".join(lines))
    else:
        click.echo(format_queue(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def storage(ctx, fmt):
    """Show storage status (GPFS)."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    queries = _get_queries(cluster, "storage")
    if not queries:
        click.echo("(此集群无存储监控数据)")
        return
    results = _query_group(client, queries)
    if fmt == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_storage(results))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def report(ctx, fmt):
    """Generate full cluster status report (for Feishu group)."""
    client = get_client()
    cluster = ctx.obj["cluster"]

    if cluster == "all":
        for c in ("digua", "school"):
            click.echo(f"\n{'='*40}")
            click.echo(f"  {c.upper()} CLUSTER REPORT")
            click.echo(f"{'='*40}")
            _generate_report(client, c, fmt)
        return

    _generate_report(client, cluster, fmt)


def _generate_report(client: VMClient, cluster: str, fmt: str):
    """Generate report for a single cluster."""
    summary_r = _query_group(client, _get_queries(cluster, "summary"))
    jobs_r = _query_group(client, _get_queries(cluster, "jobs"))
    queue_r = _query_group(client, _get_queries(cluster, "queue"))
    errors_r = _query_group(client, _get_queries(cluster, "errors"))
    temp_r = _query_group(client, _get_queries(cluster, "temperature"))
    power_r = _query_group(client, _get_queries(cluster, "power"))

    if fmt == "json":
        click.echo(format_json({
            "cluster": cluster,
            "summary": summary_r,
            "jobs": jobs_r,
            "queue": queue_r,
            "errors": {k: v if isinstance(v, list) else [] for k, v in errors_r.items()},
            "temperature": temp_r,
            "power": power_r,
        }))
        return

    if cluster == "school":
        _print_report_school(summary_r, jobs_r, queue_r, errors_r, temp_r, power_r)
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


def _print_report_school(summary_r, jobs_r, queue_r, errors_r, temp_r, power_r):
    """Print report formatted for school cluster."""
    total = summary_r.get("gpu_total")
    allocated = summary_r.get("gpu_allocated")
    idle = summary_r.get("gpu_idle")
    util_avg = summary_r.get("gpu_util_avg")
    power_total = power_r.get("total_watts")

    def _v(x):
        if x is None:
            return "N/A"
        if isinstance(x, float):
            return str(int(x)) if x == int(x) else f"{x:.1f}"
        return str(x)

    lines = [
        "📊 学校 HPC 集群状态报告",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"总计: {_v(total)} 张 GPU | 已分配: {_v(allocated)} 张 | 空闲: {_v(idle)} 张",
        f"平均利用率: {_v(util_avg)}%",
        "",
    ]

    running = jobs_r.get("running_jobs", [])
    if not isinstance(running, list):
        running = []
    lines.append(f"📋 运行中的任务 ({len(running)} 个)")
    if running:
        for item in sorted(running, key=lambda x: float(x["value"][1]), reverse=True)[:10]:
            m = item["metric"]
            job_id = m.get("job_id", "?")
            user = m.get("user", "?")
            partition = m.get("partition", "?")
            job_name = m.get("job_name", "")
            gpus = int(float(item["value"][1]))
            lines.append(f"  • [{job_id}] {user}@{partition} — {job_name} ({gpus} GPU)")
        if len(running) > 10:
            lines.append(f"  ... 还有 {len(running) - 10} 个")
    else:
        lines.append("  (无)")
    lines.append("")

    lines.append("📊 SLURM 分区")
    _print_queue(queue_r, "school")
    lines.append("")

    has_errors = any(isinstance(v, list) and v for v in errors_r.values())
    lines.append("⚠️ 告警")
    if has_errors:
        for key, items in errors_r.items():
            if isinstance(items, list) and items:
                lines.append(f"  • {key}: {len(items)} 个异常")
    else:
        lines.append("  • ✅ 无异常")
    lines.append("")

    lines.append("🌡️ 环境")
    lines.append(f"  • 平均温度: {_v(temp_r.get('gpu_temp_avg'))}°C | 最高: {_v(temp_r.get('gpu_temp_max'))}°C")
    lines.append(f"  • 总功耗: {_v(power_total)} W ({_v(power_total / 1000 if power_total else None)} kW)")

    click.echo("\n".join(lines))


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
        '{__name__=~"slurm.*"}',
    ]:
        series = client.series(pattern)
        if series:
            names = set(s.get("__name__", "") for s in series)
            click.echo(f"\n  {pattern}: {len(series)} series, {len(names)} metrics")
            for n in sorted(names)[:10]:
                click.echo(f"    {n}")


if __name__ == "__main__":
    cli()
