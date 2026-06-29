# Data Schema — Metric Naming and Labels

## Metric Naming Conventions

### DCGM Metrics (both clusters)

All DCGM metrics share the `DCGM_FI_*` prefix. Common ones:

| Metric | Unit | Description |
|--------|------|-------------|
| `DCGM_FI_DEV_GPU_UTIL` | % | SM utilization (active time ratio) |
| `DCGM_FI_DEV_GPU_TEMP` | °C | GPU core temperature |
| `DCGM_FI_DEV_MEMORY_TEMP` | °C | HBM temperature |
| `DCGM_FI_DEV_POWER_USAGE` | W | Current power draw |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | % | Memory bandwidth utilization |
| `DCGM_FI_DEV_FB_USED` | MiB | Framebuffer memory used |
| `DCGM_FI_DEV_FB_FREE` | MiB | Framebuffer memory free |
| `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE` | ratio | Tensor core activity |
| `DCGM_FI_PROF_SM_ACTIVE` | ratio | SM active ratio |
| `DCGM_FI_PROF_SM_OCCUPANCY` | ratio | SM occupancy |
| `DCGM_FI_PROF_DRAM_ACTIVE` | ratio | DRAM bandwidth active |
| `DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL` | B/s | NVLink total throughput |
| `DCGM_FI_DEV_XID_ERRORS` | count | XID error counter |
| `DCGM_FI_DEV_PCIE_REPLAY_COUNTER` | count | PCIe replay events |
| `DCGM_FI_DEV_UNCORRECTABLE_REMAPPED_ROWS` | count | Bad memory rows (uncorrectable) |
| `DCGM_FI_DEV_CORRECTABLE_REMAPPED_ROWS` | count | Bad memory rows (correctable) |

### SLURM Synthetic Metrics (school only)

Pushed by the school-collector daemon:

| Metric | Labels | Description |
|--------|--------|-------------|
| `slurm_job_gpus` | cluster, job_id, user, partition, state, job_name | GPU count per job |
| `slurm_partition_total_gpus` | cluster, partition | Total GPUs in partition |
| `slurm_partition_allocated_gpus` | cluster, partition | Allocated GPUs in partition |
| `slurm_partition_idle_gpus` | cluster, partition | Idle GPUs in partition |
| `slurm_partition_total_nodes` | cluster, partition | Total nodes in partition |
| `slurm_partition_alloc_nodes` | cluster, partition | Allocated nodes |
| `slurm_partition_idle_nodes` | cluster, partition | Idle nodes |
| `slurm_queue_running_jobs` | cluster, partition | Running job count |
| `slurm_queue_pending_jobs` | cluster, partition | Pending job count |
| `slurm_cluster_total_gpus` | cluster | Cluster-wide total |
| `slurm_cluster_allocated_gpus` | cluster | Cluster-wide allocated |
| `slurm_cluster_idle_gpus` | cluster | Cluster-wide idle |

### Kubernetes Metrics (DiGua only)

| Metric | Description |
|--------|-------------|
| `kube_pod_container_resource_requests{resource="nvidia_com_gpu"}` | GPU requests per pod |
| `kube_pod_status_phase{phase="Running"}` | Running pods |
| `kube_node_status_capacity{resource="nvidia_com_gpu"}` | GPU capacity per node |
| `volcano_queue_*` | Volcano scheduler queue state |

## Distinguishing Clusters in PromQL

```promql
# DiGua cluster (no cluster label, use job filter)
DCGM_FI_DEV_GPU_UTIL{job="aicp-dcgm-exporter"}

# School cluster (uses injected cluster label)
DCGM_FI_DEV_GPU_UTIL{cluster="school"}

# Both (union)
DCGM_FI_DEV_GPU_UTIL{job="aicp-dcgm-exporter"} or DCGM_FI_DEV_GPU_UTIL{cluster="school"}
```

## Label Taxonomy

| Label | Scope | Description |
|-------|-------|-------------|
| `cluster` | school only | Cluster identifier, injected by collector |
| `job` | both | Prometheus scrape job name |
| `Hostname` | both | Compute node hostname |
| `gpu` | both | GPU device index (0-7) |
| `hpc_job` | school DCGM | SLURM job ID (set by DCGM automatically) |
| `partition` | school slurm_* | SLURM partition name |
| `user` | school slurm_* | Job owner username |
| `job_id` | school slurm_* | SLURM job ID |
| `job_name` | school slurm_* | SLURM job name |
| `namespace` | digua kube_* | K8s namespace |
| `pod` | digua kube_* | K8s pod name |
| `queue_name` | digua volcano_* | Volcano queue name |
