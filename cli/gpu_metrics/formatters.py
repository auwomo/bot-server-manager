import json
from typing import Any


def _val(v: Any) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else f"{v:.1f}"
    return str(v)


def _extract_scalar(data: dict) -> float | None:
    result = data.get("data", {}).get("result", [])
    if result and result[0].get("value"):
        try:
            return float(result[0]["value"][1])
        except (IndexError, ValueError, TypeError):
            return None
    return None


def _extract_vector(data: dict) -> list[dict]:
    return data.get("data", {}).get("result", [])


def format_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def format_summary(results: dict) -> str:
    total = results.get("gpu_total")
    allocated = results.get("gpu_allocated")
    idle = (int(total) - int(allocated)) if total and allocated else None
    alloc_pct = (allocated / total * 100) if total and allocated else None
    util_avg = results.get("gpu_util_avg")
    util_active = results.get("gpu_util_active")
    active_count = results.get("gpu_active_count")
    power = results.get("power_total_watts")
    temp_avg = results.get("temp_avg")
    temp_max = results.get("temp_max")

    lines = [
        "=== GPU 集群总览 ===",
        f"  GPU 总数:       {_val(total)} 张 (NVIDIA H20)",
        f"  已分配:         {_val(allocated)} 张",
        f"  空闲:           {_val(idle)} 张",
        f"  分配率:         {_val(alloc_pct)}%",
        f"  平均利用率:     {_val(util_avg)}%",
        f"  活跃卡数:       {_val(active_count)} 张 (利用率>{0}%)",
        f"  活跃卡平均利用率: {_val(util_active)}%",
        f"  总功耗:         {_val(power)} W ({_val(power / 1000 if power else None)} kW)",
        f"  平均温度:       {_val(temp_avg)}°C (最高: {_val(temp_max)}°C)",
    ]
    return "\n".join(lines)


def format_jobs(pods: list[dict], by_ns: list[dict]) -> str:
    lines = [f"=== 运行中的 GPU 任务 ({len(pods)} 个) ==="]

    if by_ns:
        lines.append("\n  按命名空间:")
        for item in sorted(by_ns, key=lambda x: float(x["value"][1]), reverse=True):
            ns = item["metric"].get("namespace", "?")
            gpus = int(float(item["value"][1]))
            lines.append(f"    {ns}: {gpus} GPUs")

    if pods:
        lines.append("\n  任务列表:")
        for item in sorted(pods, key=lambda x: float(x["value"][1]), reverse=True):
            pod = item["metric"].get("pod", "?")
            ns = item["metric"].get("namespace", "")
            gpus = int(float(item["value"][1]))
            lines.append(f"    {pod} ({ns}) — {gpus} GPU{'s' if gpus > 1 else ''}")

    if not pods:
        lines.append("  (无运行中的 GPU 任务)")
    return "\n".join(lines)


def format_nodes(util_data: list[dict], temp_data: list[dict], power_data: list[dict]) -> str:
    nodes = {}
    for item in util_data:
        host = item["metric"].get("Hostname", "?")
        nodes.setdefault(host, {})["util"] = float(item["value"][1])
    for item in temp_data:
        host = item["metric"].get("Hostname", "?")
        nodes.setdefault(host, {})["temp"] = float(item["value"][1])
    for item in power_data:
        host = item["metric"].get("Hostname", "?")
        nodes.setdefault(host, {})["power"] = float(item["value"][1])

    lines = [f"=== 节点 GPU 状态 ({len(nodes)} 节点) ==="]
    lines.append(f"  {'节点':<16} {'利用率':>8} {'温度':>8} {'功耗':>10}")
    lines.append(f"  {'─' * 16} {'─' * 8} {'─' * 8} {'─' * 10}")
    for host in sorted(nodes.keys()):
        info = nodes[host]
        u = f"{info.get('util', 0):.1f}%"
        t = f"{info.get('temp', 0):.0f}°C"
        p = f"{info.get('power', 0):.0f}W"
        lines.append(f"  {host:<16} {u:>8} {t:>8} {p:>10}")
    return "\n".join(lines)


def format_utilization(results: dict) -> str:
    lines = ["=== GPU 利用率详情 ==="]
    lines.append(f"  Tensor Core 活跃率: {_val(results.get('tensor_active'))}%")
    lines.append(f"  SM 活跃率:          {_val(results.get('sm_active'))}%")
    lines.append(f"  SM 占用率:          {_val(results.get('sm_occupancy'))}%")
    lines.append(f"  显存带宽利用率:     {_val(results.get('mem_copy_util'))}%")
    lines.append(f"  DRAM 活跃率:        {_val(results.get('dram_active'))}%")
    lines.append("\n  利用率分布:")
    lines.append(f"    0%:      {_val(results.get('util_zero'))} 张")
    lines.append(f"    1-25%:   {_val(results.get('util_low'))} 张")
    lines.append(f"    25-50%:  {_val(results.get('util_mid'))} 张")
    lines.append(f"    50-75%:  {_val(results.get('util_high'))} 张")
    lines.append(f"    75-100%: {_val(results.get('util_full'))} 张")
    return "\n".join(lines)


def format_power(results: dict) -> str:
    total = results.get("total_watts")
    lines = [
        "=== GPU 功耗 ===",
        f"  集群总功耗: {_val(total)} W ({_val(total / 1000 if total else None)} kW)",
        f"  单卡平均:   {_val(results.get('avg_per_gpu'))} W",
        f"  单卡最高:   {_val(results.get('max_single_gpu'))} W",
        f"  功耗上限:   {_val(results.get('power_limit'))} W/卡",
    ]
    return "\n".join(lines)


def format_temperature(results: dict) -> str:
    lines = [
        "=== GPU 温度 ===",
        f"  GPU 核心:  平均 {_val(results.get('gpu_temp_avg'))}°C / 最高 {_val(results.get('gpu_temp_max'))}°C",
        f"  显存:      平均 {_val(results.get('mem_temp_avg'))}°C / 最高 {_val(results.get('mem_temp_max'))}°C",
        f"  超 70°C:   {int(results['over_70']) if results.get('over_70') else 0} 张",
        f"  超 80°C:   {int(results['over_80']) if results.get('over_80') else 0} 张",
    ]
    top5 = results.get("top5_hottest", [])
    if top5:
        lines.append("\n  最高温 Top5:")
        for item in top5:
            m = item["metric"]
            t = float(item["value"][1])
            lines.append(f"    {m.get('Hostname','?')} gpu{m.get('gpu','?')}: {t:.0f}°C")
    return "\n".join(lines)


def format_errors(results: dict) -> str:
    lines = ["=== 故障检测 ==="]
    categories = [
        ("xid_errors", "XID 错误"),
        ("uncorrectable_remapped", "不可纠正行重映射"),
        ("row_remap_failure", "行重映射失败"),
        ("pcie_replay", "PCIe 重放 (>100)"),
        ("correctable_remapped", "可纠正行重映射"),
        ("node_not_ready", "节点 Not Ready"),
    ]
    has_issues = False
    for key, label in categories:
        items = results.get(key, [])
        if items:
            has_issues = True
            lines.append(f"\n  ⚠️  {label}: {len(items)} 个")
            for item in items[:5]:
                m = item["metric"]
                v = item["value"][1]
                host = m.get("Hostname", m.get("node", "?"))
                gpu = m.get("gpu", "")
                detail = f"gpu{gpu}" if gpu else ""
                lines.append(f"      {host} {detail} = {v}")
            if len(items) > 5:
                lines.append(f"      ... 还有 {len(items) - 5} 个")
    if not has_issues:
        lines.append("  ✅ 无异常")
    return "\n".join(lines)


def format_network(results: dict) -> str:
    lines = ["=== 网络状态 ==="]
    ib_total = results.get("ib_links_total")
    ib_active = results.get("ib_links_active")
    lines.append(f"  InfiniBand 链路: {_val(ib_active)}/{_val(ib_total)} 活跃")

    ib_down = results.get("ib_link_down", [])
    if ib_down:
        lines.append(f"  ⚠️  链路故障: {len(ib_down)} 个")
        for item in ib_down[:3]:
            lines.append(f"      {item['metric']}")

    ib_ber = results.get("ib_ber", [])
    if ib_ber:
        lines.append(f"  ⚠️  BER 异常: {len(ib_ber)} 个")

    nvlink = results.get("nvlink_bw_total")
    lines.append(f"  NVLink 总带宽: {_val(nvlink)} bytes/s")

    if not ib_down and not ib_ber:
        lines.append("  ✅ 网络正常")
    return "\n".join(lines)


def format_queue(results: dict) -> str:
    lines = ["=== Volcano 调度队列 ==="]
    cap = results.get("capacity_gpu", [])
    alloc = {r["metric"].get("queue_name", r["metric"].get("queue", "?")): float(r["value"][1])
             for r in results.get("allocated_gpu", [])}
    req = {r["metric"].get("queue_name", r["metric"].get("queue", "?")): float(r["value"][1])
           for r in results.get("requested_gpu", [])}
    running = {r["metric"].get("queue_name", r["metric"].get("queue", "?")): int(float(r["value"][1]))
               for r in results.get("pg_running", [])}
    pending = {r["metric"].get("queue_name", r["metric"].get("queue", "?")): int(float(r["value"][1]))
               for r in results.get("pg_pending", [])}

    for item in cap:
        name = item["metric"].get("queue_name", item["metric"].get("queue", "?"))
        if name == "root":
            continue
        c = float(item["value"][1])
        a = alloc.get(name, 0)
        r = req.get(name, 0)
        run = running.get(name, 0)
        pend = pending.get(name, 0)
        lines.append(f"  {name}:")
        lines.append(f"    容量: {_val(c)} GPU | 已分配: {_val(a)} | 请求: {_val(r)}")
        lines.append(f"    运行: {run} 个任务 | 排队: {pend} 个")

    return "\n".join(lines)


def format_storage(results: dict) -> str:
    lines = ["=== GPFS 存储 ==="]
    mounts = results.get("mount_status", [])
    ok = sum(1 for m in mounts if float(m["value"][1]) == 1)
    lines.append(f"  挂载状态: {ok}/{len(mounts)} 正常")

    read_bps = results.get("read_bps", [])
    write_bps = results.get("write_bps", [])
    total_read = sum(float(r["value"][1]) for r in read_bps)
    total_write = sum(float(r["value"][1]) for r in write_bps)
    lines.append(f"  读吞吐:   {total_read / 1024 / 1024:.1f} MB/s")
    lines.append(f"  写吞吐:   {total_write / 1024 / 1024:.1f} MB/s")
    return "\n".join(lines)


def format_report(summary: dict, jobs_pods: list, jobs_ns: list, queue: dict, errors: dict, temp: dict, power: dict) -> str:
    total = summary.get("gpu_total")
    allocated = summary.get("gpu_allocated")
    idle = (int(total) - int(allocated)) if total and allocated else None
    alloc_pct = (allocated / total * 100) if total and allocated else None
    util_avg = summary.get("gpu_util_avg")
    power_total = power.get("total_watts")

    lines = [
        "📊 GPU 集群状态报告",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"总计: {_val(total)} 张 H20 | 已分配: {_val(allocated)} 张 | 空闲: {_val(idle)} 张",
        f"分配率: {_val(alloc_pct)}% | 平均利用率: {_val(util_avg)}%",
        "",
    ]

    # Jobs
    lines.append(f"📋 运行中的任务 ({len(jobs_pods)} 个)")
    if jobs_pods:
        for item in sorted(jobs_pods, key=lambda x: float(x["value"][1]), reverse=True)[:10]:
            pod = item["metric"].get("pod", "?")
            ns = item["metric"].get("namespace", "")
            gpus = int(float(item["value"][1]))
            lines.append(f"  • {pod} ({ns}) — {gpus} GPUs")
        if len(jobs_pods) > 10:
            lines.append(f"  ... 还有 {len(jobs_pods) - 10} 个")
    else:
        lines.append("  (无)")
    lines.append("")

    # Queue
    lines.append("📊 Volcano 队列")
    cap_data = queue.get("capacity_gpu", [])
    alloc_data = {r["metric"].get("queue_name", r["metric"].get("queue", "?")): float(r["value"][1])
                  for r in queue.get("allocated_gpu", [])}
    running_data = {r["metric"].get("queue_name", r["metric"].get("queue", "?")): int(float(r["value"][1]))
                    for r in queue.get("pg_running", [])}
    for item in cap_data:
        name = item["metric"].get("queue_name", item["metric"].get("queue", "?"))
        if name == "root":
            continue
        c = float(item["value"][1])
        a = alloc_data.get(name, 0)
        run = running_data.get(name, 0)
        lines.append(f"  • {name}: {_val(a)}/{_val(c)} GPU 已分配 | {run} 个任务运行中")
    lines.append("")

    # Errors
    has_errors = any(errors.get(k) for k in errors)
    lines.append("⚠️ 告警")
    if has_errors:
        for key, items in errors.items():
            if items:
                lines.append(f"  • {key}: {len(items)} 个异常")
    else:
        lines.append("  • ✅ 无 XID 错误 / 无行重映射故障 / 所有节点正常")
    lines.append("")

    # Environment
    lines.append("🌡️ 环境")
    lines.append(f"  • 平均温度: {_val(temp.get('gpu_temp_avg'))}°C | 最高: {_val(temp.get('gpu_temp_max'))}°C")
    lines.append(f"  • 总功耗: {_val(power_total)} W ({_val(power_total / 1000 if power_total else None)} kW)")

    return "\n".join(lines)
