"""PromQL queries for School HPC cluster metrics.

School cluster data is identified by cluster="school" label,
injected by the school-collector daemon. SLURM state comes from
synthetic slurm_* gauges also pushed by the collector.
"""

SCHOOL_FILTER = 'cluster="school"'

# --- Summary / Allocation ---
SUMMARY = {
    "gpu_total": f'count(DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}})',
    "gpu_allocated": f'slurm_cluster_allocated_gpus{{{SCHOOL_FILTER}}}',
    "gpu_idle": f'slurm_cluster_idle_gpus{{{SCHOOL_FILTER}}}',
    "gpu_util_avg": f'avg(DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}})',
    "gpu_util_active": f'avg(DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}} > 0)',
    "gpu_active_count": f'count(DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}} > 0)',
    "power_total_watts": f'sum(DCGM_FI_DEV_POWER_USAGE{{{SCHOOL_FILTER}}})',
    "temp_avg": f'avg(DCGM_FI_DEV_GPU_TEMP{{{SCHOOL_FILTER}}})',
    "temp_max": f'max(DCGM_FI_DEV_GPU_TEMP{{{SCHOOL_FILTER}}})',
}

# --- Training Jobs (SLURM) ---
JOBS = {
    "running_jobs": f'slurm_job_gpus{{{SCHOOL_FILTER},state="RUNNING"}}',
    "pending_jobs": f'slurm_job_gpus{{{SCHOOL_FILTER},state="PENDING"}}',
    "running_job_count": f'count(slurm_job_gpus{{{SCHOOL_FILTER},state="RUNNING"}})',
    "pending_job_count": f'count(slurm_job_gpus{{{SCHOOL_FILTER},state="PENDING"}})',
    "gpu_by_user": f'sum by (user) (slurm_job_gpus{{{SCHOOL_FILTER},state="RUNNING"}})',
    "gpu_by_partition": f'sum by (partition) (slurm_job_gpus{{{SCHOOL_FILTER},state="RUNNING"}})',
}

# --- Per-Node ---
NODES = {
    "util_per_node": f'avg by (Hostname) (DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}})',
    "temp_per_node": f'avg by (Hostname) (DCGM_FI_DEV_GPU_TEMP{{{SCHOOL_FILTER}}})',
    "power_per_node": f'sum by (Hostname) (DCGM_FI_DEV_POWER_USAGE{{{SCHOOL_FILTER}}})',
}

# --- Utilization Detail ---
UTILIZATION = {
    "gpu_util_all": f'DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}}',
    "tensor_active": f'avg(DCGM_FI_PROF_PIPE_TENSOR_ACTIVE{{{SCHOOL_FILTER}}})',
    "sm_active": f'avg(DCGM_FI_PROF_SM_ACTIVE{{{SCHOOL_FILTER}}})',
    "sm_occupancy": f'avg(DCGM_FI_PROF_SM_OCCUPANCY{{{SCHOOL_FILTER}}})',
    "mem_copy_util": f'avg(DCGM_FI_DEV_MEM_COPY_UTIL{{{SCHOOL_FILTER}}})',
    "dram_active": f'avg(DCGM_FI_PROF_DRAM_ACTIVE{{{SCHOOL_FILTER}}})',
    "util_zero": f'count(DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}} == 0)',
    "util_low": f'count(DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}} > 0 and DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}} <= 25)',
    "util_mid": f'count(DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}} > 25 and DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}} <= 50)',
    "util_high": f'count(DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}} > 50 and DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}} <= 75)',
    "util_full": f'count(DCGM_FI_DEV_GPU_UTIL{{{SCHOOL_FILTER}}} > 75)',
}

# --- Power ---
POWER = {
    "total_watts": f'sum(DCGM_FI_DEV_POWER_USAGE{{{SCHOOL_FILTER}}})',
    "per_node_watts": f'sum by (Hostname) (DCGM_FI_DEV_POWER_USAGE{{{SCHOOL_FILTER}}})',
    "max_single_gpu": f'max(DCGM_FI_DEV_POWER_USAGE{{{SCHOOL_FILTER}}})',
    "avg_per_gpu": f'avg(DCGM_FI_DEV_POWER_USAGE{{{SCHOOL_FILTER}}})',
}

# --- Temperature ---
TEMPERATURE = {
    "gpu_temp_avg": f'avg(DCGM_FI_DEV_GPU_TEMP{{{SCHOOL_FILTER}}})',
    "gpu_temp_max": f'max(DCGM_FI_DEV_GPU_TEMP{{{SCHOOL_FILTER}}})',
    "mem_temp_avg": f'avg(DCGM_FI_DEV_MEMORY_TEMP{{{SCHOOL_FILTER}}})',
    "mem_temp_max": f'max(DCGM_FI_DEV_MEMORY_TEMP{{{SCHOOL_FILTER}}})',
    "top5_hottest": f'topk(5, DCGM_FI_DEV_GPU_TEMP{{{SCHOOL_FILTER}}})',
    "over_80": f'count(DCGM_FI_DEV_GPU_TEMP{{{SCHOOL_FILTER}}} > 80)',
    "over_70": f'count(DCGM_FI_DEV_GPU_TEMP{{{SCHOOL_FILTER}}} > 70)',
}

# --- Errors / Health ---
ERRORS = {
    "xid_errors": f'DCGM_FI_DEV_XID_ERRORS{{{SCHOOL_FILTER}}} > 0',
    "uncorrectable_remapped": f'DCGM_FI_DEV_UNCORRECTABLE_REMAPPED_ROWS{{{SCHOOL_FILTER}}} > 0',
    "row_remap_failure": f'DCGM_FI_DEV_ROW_REMAP_FAILURE{{{SCHOOL_FILTER}}} > 0',
    "pcie_replay": f'DCGM_FI_DEV_PCIE_REPLAY_COUNTER{{{SCHOOL_FILTER}}} > 100',
    "correctable_remapped": f'DCGM_FI_DEV_CORRECTABLE_REMAPPED_ROWS{{{SCHOOL_FILTER}}} > 0',
}

# --- Network (NVLink only, no InfiniBand monitoring on school cluster) ---
NETWORK = {
    "nvlink_bw_total": f'sum(DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL{{{SCHOOL_FILTER}}})',
    "nvlink_bw_per_node": f'sum by (Hostname) (DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL{{{SCHOOL_FILTER}}})',
}

# --- SLURM Queue (replaces Volcano for school) ---
QUEUE = {
    "partition_total_gpus": f'slurm_partition_total_gpus{{{SCHOOL_FILTER}}}',
    "partition_allocated_gpus": f'slurm_partition_allocated_gpus{{{SCHOOL_FILTER}}}',
    "partition_idle_gpus": f'slurm_partition_idle_gpus{{{SCHOOL_FILTER}}}',
    "queue_running_jobs": f'slurm_queue_running_jobs{{{SCHOOL_FILTER}}}',
    "queue_pending_jobs": f'slurm_queue_pending_jobs{{{SCHOOL_FILTER}}}',
}

# --- Storage (not available for school cluster) ---
STORAGE = {}
