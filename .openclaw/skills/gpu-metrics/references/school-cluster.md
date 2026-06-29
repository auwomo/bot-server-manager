# School HPC Cluster (学校集群)

## Overview

- **Scheduler**: SLURM
- **Scale**: ~60 nodes, ~480 GPUs total
  - 38+ nodes with 8× NVIDIA H800 each
  - 22+ nodes with 8× NVIDIA H100 each
- **Login node**: 172.16.78.35:10024 (SSH)
- **Network**: Internal 172.16.x.x (requires VPN from outside)

## Partitions (9 total, by lab)

| Partition | GPU Type | Approx. GPUs |
|-----------|----------|-------------|
| yukaichenglab | H800 | 144 |
| tangleilab | H800 | 48 |
| zhangbolab | H800 | 48 |
| caopenglab | H100 | 48 |
| wuqionglab | H800 | 48 |
| wangxlab | H100 | 32 |
| zhangwenguanglab | H100 | 48 |
| zhangshenglab | H800 | 48 |
| linjinglab | H100 | 32 |

## Metrics Source

- **DCGM exporter**: Runs on compute nodes port 9400. Directly reachable from login node.
  - Includes `hpc_job` label = SLURM job ID (automatic job-to-GPU correlation)
  - Full coverage: utilization, tensor core, temperature, power, memory, NVLink, PCIe, XID errors
- **SLURM commands**: `squeue`, `sinfo`, `sacct` — synthesized into `slurm_*` gauges by collector
- **node_exporter**: Port 9100 on compute nodes (available but not currently collected)

## Data Path

```
Mac (lab, VPN) ──SSH──► Login Node
                            │
                            ├── curl gnho*:9400/metrics
                            └── squeue / sinfo
                            │
                            ▼ parse + inject cluster="school"
                            │
Mac ──HTTP POST─────────► VictoriaMetrics (Baidu cloud VM :8428)
```

Scrape cycle: DCGM every 30s, SLURM state every 60s.
Typical scrape: ~7700 metric lines from ~37 active nodes in ~12s.

## Key Labels

| Label | Example | Meaning |
|-------|---------|---------|
| `cluster` | `school` | Injected by collector |
| `job` | `school-dcgm-exporter` | Injected by collector |
| `Hostname` | `gnho001` | Compute node |
| `gpu` | `0`-`7` | GPU index on node |
| `hpc_job` | `65323` | SLURM job ID (from DCGM) |
| `partition` | `yukaichenglab` | SLURM partition (on slurm_* metrics) |
| `user` | `mazijian` | Job owner (on slurm_* metrics) |
| `job_id` | `65323` | SLURM job ID (on slurm_* metrics) |

## Constraints

- Must NOT disrupt running training jobs (read-only data collection)
- ~22 nodes may be unreachable (down or DCGM not running) — this is normal
- SSH password stored in environment variable, never in config files
