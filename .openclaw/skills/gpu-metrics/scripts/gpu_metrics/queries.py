"""PromQL queries for GPU cluster metrics.

All GPU hardware queries use job="aicp-dcgm-exporter" to deduplicate
(the cluster runs two DCGM exporters on ports 9400 and 19400).
"""

JOB_FILTER = 'job="aicp-dcgm-exporter"'

# --- Summary / Allocation ---
SUMMARY = {
    "gpu_total": f'count(DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}})',
    "gpu_allocated": (
        'sum(kube_pod_container_resource_requests{resource="nvidia_com_gpu"}'
        ' * on(pod,namespace) group_left'
        ' kube_pod_status_phase{phase="Running"})'
    ),
    "gpu_util_avg": f'avg(DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}})',
    "gpu_util_active": f'avg(DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}} > 0)',
    "gpu_active_count": f'count(DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}} > 0)',
    "power_total_watts": f'sum(DCGM_FI_DEV_POWER_USAGE{{{JOB_FILTER}}})',
    "temp_avg": f'avg(DCGM_FI_DEV_GPU_TEMP{{{JOB_FILTER}}})',
    "temp_max": f'max(DCGM_FI_DEV_GPU_TEMP{{{JOB_FILTER}}})',
}

# --- Training Jobs ---
JOBS = {
    "running_pods_with_gpu": (
        'sum by (pod, namespace) ('
        'kube_pod_container_resource_requests{resource="nvidia_com_gpu"}'
        ' * on(pod,namespace) group_left'
        ' kube_pod_status_phase{phase="Running"})'
    ),
    "gpu_by_namespace": (
        'sum by (namespace) ('
        'kube_pod_container_resource_requests{resource="nvidia_com_gpu"}'
        ' * on(pod,namespace) group_left'
        ' kube_pod_status_phase{phase="Running"})'
    ),
    "volcano_jobs_running": 'volcano_queue_pod_group_running_count',
    "volcano_jobs_pending": 'volcano_queue_pod_group_pending_count',
    "volcano_jobs_inqueue": 'volcano_queue_pod_group_inqueue_count',
}

# --- Per-Node ---
NODES = {
    "capacity_per_node": 'kube_node_status_capacity{resource="nvidia_com_gpu"}',
    "util_per_node": f'avg by (Hostname) (DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}})',
    "temp_per_node": f'avg by (Hostname) (DCGM_FI_DEV_GPU_TEMP{{{JOB_FILTER}}})',
    "power_per_node": f'sum by (Hostname) (DCGM_FI_DEV_POWER_USAGE{{{JOB_FILTER}}})',
    "node_ready": 'kube_node_status_condition{condition="Ready",status="true"}',
}

# --- Utilization Detail ---
UTILIZATION = {
    "gpu_util_all": f'DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}}',
    "tensor_active": f'avg(DCGM_FI_PROF_PIPE_TENSOR_ACTIVE{{{JOB_FILTER}}})',
    "sm_active": f'avg(DCGM_FI_PROF_SM_ACTIVE{{{JOB_FILTER}}})',
    "sm_occupancy": f'avg(DCGM_FI_PROF_SM_OCCUPANCY{{{JOB_FILTER}}})',
    "mem_copy_util": f'avg(DCGM_FI_DEV_MEM_COPY_UTIL{{{JOB_FILTER}}})',
    "dram_active": f'avg(DCGM_FI_PROF_DRAM_ACTIVE{{{JOB_FILTER}}})',
    # Buckets
    "util_zero": f'count(DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}} == 0)',
    "util_low": f'count(DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}} > 0 and DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}} <= 25)',
    "util_mid": f'count(DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}} > 25 and DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}} <= 50)',
    "util_high": f'count(DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}} > 50 and DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}} <= 75)',
    "util_full": f'count(DCGM_FI_DEV_GPU_UTIL{{{JOB_FILTER}}} > 75)',
}

# --- Power ---
POWER = {
    "total_watts": f'sum(DCGM_FI_DEV_POWER_USAGE{{{JOB_FILTER}}})',
    "per_node_watts": f'sum by (Hostname) (DCGM_FI_DEV_POWER_USAGE{{{JOB_FILTER}}})',
    "max_single_gpu": f'max(DCGM_FI_DEV_POWER_USAGE{{{JOB_FILTER}}})',
    "avg_per_gpu": f'avg(DCGM_FI_DEV_POWER_USAGE{{{JOB_FILTER}}})',
    "power_limit": 'max(node_gpu_powerManagementLimit)',
}

# --- Temperature ---
TEMPERATURE = {
    "gpu_temp_avg": f'avg(DCGM_FI_DEV_GPU_TEMP{{{JOB_FILTER}}})',
    "gpu_temp_max": f'max(DCGM_FI_DEV_GPU_TEMP{{{JOB_FILTER}}})',
    "mem_temp_avg": f'avg(DCGM_FI_DEV_MEMORY_TEMP{{{JOB_FILTER}}})',
    "mem_temp_max": f'max(DCGM_FI_DEV_MEMORY_TEMP{{{JOB_FILTER}}})',
    "top5_hottest": f'topk(5, DCGM_FI_DEV_GPU_TEMP{{{JOB_FILTER}}})',
    "over_80": f'count(DCGM_FI_DEV_GPU_TEMP{{{JOB_FILTER}}} > 80)',
    "over_70": f'count(DCGM_FI_DEV_GPU_TEMP{{{JOB_FILTER}}} > 70)',
}

# --- Errors / Health ---
ERRORS = {
    "xid_errors": f'DCGM_FI_DEV_XID_ERRORS{{{JOB_FILTER}}} > 0',
    "uncorrectable_remapped": f'DCGM_FI_DEV_UNCORRECTABLE_REMAPPED_ROWS{{{JOB_FILTER}}} > 0',
    "row_remap_failure": f'DCGM_FI_DEV_ROW_REMAP_FAILURE{{{JOB_FILTER}}} > 0',
    "pcie_replay": f'DCGM_FI_DEV_PCIE_REPLAY_COUNTER{{{JOB_FILTER}}} > 100',
    "node_not_ready": 'kube_node_status_condition{condition="Ready",status="true"} == 0',
    "correctable_remapped": f'DCGM_FI_DEV_CORRECTABLE_REMAPPED_ROWS{{{JOB_FILTER}}} > 0',
}

# --- Network (InfiniBand + NVLink) ---
NETWORK = {
    "ib_link_down": 'iblinkinfo_link_down_counter > 0',
    "ib_error_recovery": 'iblinkinfo_link_error_recovery_counter > 0',
    "ib_ber": 'iblinkinfo_physical_effective_ber > 0',
    "nvlink_bw_total": f'sum(DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL{{{JOB_FILTER}}})',
    "nvlink_bw_per_node": f'sum by (Hostname) (DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL{{{JOB_FILTER}}})',
    "ib_links_total": 'count(iblinkinfo_operational_state)',
    "ib_links_active": 'count(iblinkinfo_operational_state == 1)',
}

# --- Volcano Queue ---
QUEUE = {
    "capacity_gpu": 'volcano_queue_capacity_scalar_resources{resource="nvidia.com/gpu"} / 1000',
    "allocated_gpu": 'volcano_queue_allocated_scalar_resources{resource="nvidia.com/gpu"} / 1000',
    "requested_gpu": 'volcano_queue_request_scalar_resources{resource="nvidia.com/gpu"} / 1000',
    "pg_running": 'volcano_queue_pod_group_running_count',
    "pg_pending": 'volcano_queue_pod_group_pending_count',
    "pg_inqueue": 'volcano_queue_pod_group_inqueue_count',
    "pg_completed": 'volcano_queue_pod_group_completed_count',
}

# --- Storage (GPFS) ---
STORAGE = {
    "mount_status": 'gpfs_mount_status',
    "read_bps": 'rate(gpfs_perf_read_bytes_total[5m])',
    "write_bps": 'rate(gpfs_perf_write_bytes_total[5m])',
    "iops": 'rate(gpfs_perf_operations_total[5m])',
    "state": 'gpfs_state',
}
