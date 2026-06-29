"""SLURM command execution and metric synthesis."""

import logging
import re

from .ssh import SSHManager

logger = logging.getLogger(__name__)

def _slurm_cmd(cmd: str) -> str:
    """Wrap a SLURM command for execution via non-login SSH shell.

    Uses single quotes for the outer bash -l -c wrapper. The inner command
    must not contain unescaped single quotes.
    """
    return f"bash -l -c '{cmd}'"


def get_active_nodes(ssh: SSHManager) -> list[str]:
    """Get list of active compute nodes (idle, mixed, or allocated) from sinfo."""
    cmd = _slurm_cmd('sinfo -N --format="%N|%T|%G" --noheader')
    output = ssh.run(cmd)
    if not output:
        logger.warning("sinfo returned no output")
        return []

    active_states = {"idle", "mixed", "alloc", "allocated", "completing"}
    nodes = []
    seen = set()
    for line in output.split("\n"):
        parts = line.strip().split("|")
        if len(parts) < 3:
            continue
        hostname = parts[0].strip()
        state = parts[1].strip().rstrip("*").lower()
        if hostname not in seen and state in active_states:
            nodes.append(hostname)
            seen.add(hostname)
    logger.info("Discovered %d active nodes from sinfo", len(nodes))
    return nodes


def get_all_metrics(ssh: SSHManager, cluster_label: str = "school") -> list[str]:
    """Run SLURM commands and synthesize Prometheus metric lines."""
    lines: list[str] = []
    lines.extend(_get_partition_metrics(ssh, cluster_label))
    lines.extend(_get_job_metrics(ssh, cluster_label))
    lines.extend(_get_cluster_summary(ssh, cluster_label))
    return lines


def _get_partition_metrics(ssh: SSHManager, cluster: str) -> list[str]:
    """Get per-partition GPU counts from sinfo."""
    cmd = _slurm_cmd('sinfo --format="%P|%a|%D|%F|%G" --noheader')
    output = ssh.run(cmd)
    if not output:
        return []

    lines: list[str] = []
    for row in output.split("\n"):
        parts = row.strip().split("|")
        if len(parts) < 5:
            continue
        partition = parts[0].strip().rstrip("*")
        avail = parts[1].strip()
        total_nodes = int(parts[2].strip()) if parts[2].strip().isdigit() else 0

        # %F = allocated/idle/other/total nodes
        node_states = parts[3].strip().split("/")
        alloc_nodes = int(node_states[0]) if len(node_states) > 0 and node_states[0].isdigit() else 0
        idle_nodes = int(node_states[1]) if len(node_states) > 1 and node_states[1].isdigit() else 0

        # Parse GPU GRES: "gpu:h800:8(S:0-1)" → 8 gpus per node
        gres = parts[4].strip()
        gpus_per_node = _parse_gres_gpu_count(gres)
        total_gpus = total_nodes * gpus_per_node
        alloc_gpus = alloc_nodes * gpus_per_node
        idle_gpus = idle_nodes * gpus_per_node

        lbl = f'cluster="{cluster}",partition="{partition}"'
        lines.append(f'slurm_partition_total_gpus{{{lbl}}} {total_gpus}')
        lines.append(f'slurm_partition_total_nodes{{{lbl}}} {total_nodes}')
        lines.append(f'slurm_partition_alloc_nodes{{{lbl}}} {alloc_nodes}')
        lines.append(f'slurm_partition_idle_nodes{{{lbl}}} {idle_nodes}')
        lines.append(f'slurm_partition_allocated_gpus{{{lbl}}} {alloc_gpus}')
        lines.append(f'slurm_partition_idle_gpus{{{lbl}}} {idle_gpus}')
    return lines


def _get_job_metrics(ssh: SSHManager, cluster: str) -> list[str]:
    """Get running and pending job info from squeue."""
    cmd = _slurm_cmd(
        'squeue --format="%i|%u|%P|%T|%b|%N|%j" --noheader'
    )
    output = ssh.run(cmd)
    if not output:
        return []

    lines: list[str] = []
    pending_by_partition: dict[str, int] = {}
    running_by_partition: dict[str, int] = {}

    for row in output.split("\n"):
        parts = row.strip().split("|")
        if len(parts) < 7:
            continue
        job_id = parts[0].strip()
        user = parts[1].strip()
        partition = parts[2].strip()
        state = parts[3].strip()
        gres_req = parts[4].strip()
        node_list = parts[5].strip()
        job_name = parts[6].strip()

        gpu_count = _parse_gres_gpu_count(gres_req)

        lbl = (
            f'cluster="{cluster}",'
            f'job_id="{job_id}",'
            f'user="{user}",'
            f'partition="{partition}",'
            f'state="{state}",'
            f'job_name="{_escape_label(job_name)}"'
        )
        lines.append(f'slurm_job_gpus{{{lbl}}} {gpu_count}')

        if state == "RUNNING":
            running_by_partition[partition] = running_by_partition.get(partition, 0) + 1
        elif state == "PENDING":
            pending_by_partition[partition] = pending_by_partition.get(partition, 0) + 1

    for part, count in running_by_partition.items():
        lines.append(f'slurm_queue_running_jobs{{cluster="{cluster}",partition="{part}"}} {count}')
    for part, count in pending_by_partition.items():
        lines.append(f'slurm_queue_pending_jobs{{cluster="{cluster}",partition="{part}"}} {count}')

    return lines


def _get_cluster_summary(ssh: SSHManager, cluster: str) -> list[str]:
    """Get cluster-wide GPU summary."""
    cmd = _slurm_cmd(
        'sinfo --format="%G|%D|%T" --noheader'
    )
    output = ssh.run(cmd)
    if not output:
        return []

    total_gpus = 0
    alloc_gpus = 0
    for row in output.split("\n"):
        parts = row.strip().split("|")
        if len(parts) < 3:
            continue
        gres = parts[0].strip()
        node_count = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
        state = parts[2].strip().rstrip("*").lower()
        gpus_per_node = _parse_gres_gpu_count(gres)
        total = node_count * gpus_per_node
        total_gpus += total
        if state in ("alloc", "allocated", "mixed"):
            alloc_gpus += total

    lbl = f'cluster="{cluster}"'
    return [
        f'slurm_cluster_total_gpus{{{lbl}}} {total_gpus}',
        f'slurm_cluster_allocated_gpus{{{lbl}}} {alloc_gpus}',
        f'slurm_cluster_idle_gpus{{{lbl}}} {total_gpus - alloc_gpus}',
    ]


def _parse_gres_gpu_count(gres: str) -> int:
    """Parse GPU count from GRES string.

    Handles formats like:
      gpu:H800:8(S:0-1)  → 8
      gpu:h800:8          → 8
      gpu:8               → 8
      gres/gpu:8          → 8
      gres:gpu:8          → 8
    """
    if not gres:
        return 0
    # Match gpu:MODEL:COUNT or gpu:COUNT patterns
    m = re.search(r'gpu(?::[^:]+)?:(\d+)', gres)
    if m:
        return int(m.group(1))
    return 0


def _escape_label(value: str) -> str:
    """Escape a Prometheus label value."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
