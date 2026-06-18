"""Pre-defined PromQL queries for GPU cluster metrics.

NOTE: The actual metric names depend on what the cluster pushes via remote_write.
Common sources:
- DCGM Exporter: DCGM_FI_DEV_* metrics
- kube-state-metrics: kube_pod_*, kube_node_* metrics
- node-exporter: node_* metrics

After data starts flowing, run `gpu-metrics explore` to discover available metrics
and update these queries accordingly.
"""

QUERIES = {
    # --- GPU Utilization (DCGM Exporter) ---
    "gpu_util_avg": 'avg(DCGM_FI_DEV_GPU_UTIL)',
    "gpu_util_per_gpu": 'DCGM_FI_DEV_GPU_UTIL',
    "gpu_mem_used": 'DCGM_FI_DEV_FB_USED',
    "gpu_mem_free": 'DCGM_FI_DEV_FB_FREE',
    "gpu_temperature": 'DCGM_FI_DEV_GPU_TEMP',
    "gpu_power_usage": 'DCGM_FI_DEV_POWER_USAGE',

    # --- K8s GPU Resource Allocation (kube-state-metrics) ---
    "gpu_capacity_total": 'sum(kube_node_status_capacity{resource="nvidia_com_gpu"})',
    "gpu_allocatable_total": 'sum(kube_node_status_allocatable{resource="nvidia_com_gpu"})',
    "gpu_requested_total": 'sum(kube_pod_resource_request{resource="nvidia_com_gpu"})',
    "gpu_idle_total": (
        'sum(kube_node_status_allocatable{resource="nvidia_com_gpu"}) '
        '- sum(kube_pod_resource_request{resource="nvidia_com_gpu"})'
    ),

    # Per-node breakdown
    "gpu_capacity_per_node": 'kube_node_status_capacity{resource="nvidia_com_gpu"}',
    "gpu_requested_per_node": (
        'sum by (node) (kube_pod_resource_request{resource="nvidia_com_gpu"})'
    ),

    # --- Training Jobs ---
    "running_pods_gpu": (
        'count(kube_pod_resource_request{resource="nvidia_com_gpu"} > 0)'
    ),
    "pod_gpu_requests": (
        'kube_pod_resource_request{resource="nvidia_com_gpu"} > 0'
    ),
}
