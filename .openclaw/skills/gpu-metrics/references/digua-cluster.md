# DiGua Cloud Cluster (地瓜云)

## Overview

- **Platform**: auwomo (地瓜云)
- **Scale**: 36 nodes × 8 GPUs = 288 NVIDIA H20-3e
- **Orchestration**: Kubernetes + Volcano scheduler
- **Network**: InfiniBand interconnect
- **Storage**: GPFS parallel filesystem

## Scheduling

3 Volcano queues:
- `default`: 278 GPU capacity
- `que-1b0ccceacaca`: 256 GPU capacity
- `que-d55cc14f88f2`: 32 GPU capacity

## Metrics Source

- **DCGM exporter**: Runs on each node (port 9400 + 19400). CLI uses `job="aicp-dcgm-exporter"` to filter the primary exporter.
- **kube-state-metrics**: Pod resource requests, node capacity, scheduling state.
- **Volcano metrics**: Queue capacity, pod group status (running/pending/inqueue/completed).
- **InfiniBand**: `iblinkinfo_*` series for link state and BER.
- **GPFS**: `gpfs_*` series for mount status and throughput.

## Data Path

```
Nodes (Prometheus) ──remote_write──► VictoriaMetrics (Baidu cloud VM :8428)
```

Data arrives with ~15-30s latency.

## Key Labels

| Label | Example | Meaning |
|-------|---------|---------|
| `job` | `aicp-dcgm-exporter` | DCGM exporter instance |
| `Hostname` | `node-36-3` | Compute node |
| `gpu` | `0`-`7` | GPU index on node |
| `namespace` | `gpupool-user123` | K8s namespace (maps to user) |
| `pod` | `train-job-abc-worker-0` | K8s pod name |
