import paramiko
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('172.16.78.35', port=10024, username='mazijian', password='123456Mzj!', timeout=15)
    commands = [
        # === All DCGM metric names from a live compute node ===
        'curl -s --connect-timeout 5 http://gnho006:9400/metrics 2>/dev/null | grep "^# HELP DCGM"',
        # === GPU utilization specifically ===
        'curl -s --connect-timeout 5 http://gnho006:9400/metrics 2>/dev/null | grep -E "DCGM_FI_DEV_GPU_UTIL|DCGM_FI_DEV_MEM_COPY_UTIL|DCGM_FI_DEV_FB_USED|DCGM_FI_DEV_FB_FREE|DCGM_FI_PROF" | head -40',
        # === h800-metrics-counters.csv (what metrics are configured) ===
        'cat /soft/mongpu/dcgm-exporter/h800-metrics-counters.csv 2>/dev/null',
        # === gpu2025.csv historical data (tail for most recent entries) ===
        'tail -40 /soft/gpu2025.csv 2>/dev/null',
        'wc -l /soft/gpu2025.csv 2>/dev/null',
        # === Check for 2026 version ===
        'ls /soft/gpu2026* /soft/gpu*.csv 2>/dev/null',
        # === All nodes with DCGM reachable (quick scan a few) ===
        'for n in gnho001 gnho010 gnho020 gnho030 gnho040 gnho050 gnho060 nv-h100-001 nv-h100-010; do curl -s --connect-timeout 2 http://$n:9400/metrics 2>/dev/null | head -1 | grep -q DCGM && echo "$n: DCGM OK" || echo "$n: no DCGM"; done',
        # === Full DCGM data for one node (GPU util, mem, power, temp) ===
        'curl -s --connect-timeout 5 http://gnho006:9400/metrics 2>/dev/null | grep -v "^#" | grep -E "GPU_UTIL|MEM_COPY_UTIL|FB_USED|FB_FREE|POWER_USAGE|GPU_TEMP|MEM_TEMP|NVLINK|PCIE" | head -60',
    ]
    for cmd in commands:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        print(f"$ {cmd}")
        if out:
            print(out)
        if err and 'DeprecationWarning' not in err:
            print(f"  [stderr: {err}]")
        print()
    client.close()
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
