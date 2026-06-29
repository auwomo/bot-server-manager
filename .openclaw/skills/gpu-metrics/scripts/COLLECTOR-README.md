# School HPC Collector — Setup Guide

Collects GPU metrics from the school SLURM cluster via SSH and pushes to VictoriaMetrics.

## Prerequisites

- macOS with Python 3.10+
- VPN connection to school network (access to 172.16.x.x)
- SSH credentials for the login node

## Install

```bash
git clone <this-repo>
cd .openclaw/skills/gpu-metrics/scripts
pip install -e .
```

This installs the `school-collector` command.

## Configure

1. Copy the example config:

```bash
cp school-collector.example.yaml ~/.school-collector.yaml
```

2. Edit `~/.school-collector.yaml`:

```yaml
ssh:
  host: 172.16.78.35
  port: 10024
  username: your-username
  password_env: SCHOOL_SSH_PASSWORD   # reads password from this env var

vm:
  url: http://YOUR-VM-HOST:8428       # VictoriaMetrics endpoint
  auth_user_env: VM_AUTH_USER         # optional basic auth
  auth_pass_env: VM_AUTH_PASS

scrape:
  dcgm_interval: 30    # seconds between DCGM scrapes
  slurm_interval: 60   # seconds between SLURM state collections
  max_parallel: 10     # concurrent SSH channels for node scraping
  curl_timeout: 3      # per-node curl timeout

labels:
  cluster: school
  job: school-dcgm-exporter
```

3. Set environment variables:

```bash
export SCHOOL_SSH_PASSWORD="your-password"
export VM_AUTH_USER="admin"        # if VM requires auth
export VM_AUTH_PASS="secret"       # if VM requires auth
```

## Run (foreground)

```bash
school-collector
```

You should see output like:
```
2026-06-30 10:00:00 INFO [school_collector.__main__] Starting school collector — SSH 172.16.78.35:10024, push to http://...
2026-06-30 10:00:01 INFO [school_collector.slurm] Discovered 37 active nodes from sinfo
2026-06-30 10:00:12 INFO [school_collector.scraper] Scraped 7688 metric lines from 37/59 nodes
2026-06-30 10:00:12 INFO [school_collector.__main__] DCGM push: 7688 lines, success=True
```

## Run as macOS Service (launchd)

1. Create the plist file:

```bash
cat > ~/Library/LaunchAgents/com.gpu-metrics.school-collector.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gpu-metrics.school-collector</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/school-collector</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>SCHOOL_SSH_PASSWORD</key>
        <string>YOUR_PASSWORD_HERE</string>
    </dict>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/school-collector.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/school-collector.log</string>
</dict>
</plist>
EOF
```

2. Adjust the path to `school-collector` (find it with `which school-collector`).

3. Load and start:

```bash
launchctl load ~/Library/LaunchAgents/com.gpu-metrics.school-collector.plist
```

4. Check status:

```bash
launchctl list | grep school-collector
tail -f /tmp/school-collector.log
```

5. Stop:

```bash
launchctl unload ~/Library/LaunchAgents/com.gpu-metrics.school-collector.plist
```

## Verify Data Arrival

Query VictoriaMetrics to confirm data is being pushed:

```bash
curl 'http://YOUR-VM-HOST:8428/api/v1/query?query=count(DCGM_FI_DEV_GPU_UTIL{cluster="school"})'
```

Should return a non-zero count.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `SSH connection lost` in logs | VPN disconnected | Reconnect VPN; collector auto-retries |
| `ChannelException(2, 'Connect failed')` for some nodes | Those nodes are down or DCGM not running | Normal — collector skips unavailable nodes |
| `push failed: 401` | VM auth credentials wrong | Check `VM_AUTH_USER` / `VM_AUTH_PASS` env vars |
| `push failed: connection refused` | VM not reachable | Check VM URL and network connectivity |
| All nodes show 0 metrics | Login node can't reach compute nodes | SSH in manually and test: `curl gnho001:9400/metrics` |

## Architecture

```
Mac (VPN) ──SSH──► Login Node (172.16.78.35:10024)
                        │
                        ├── curl compute-node:9400/metrics  (DCGM)
                        └── squeue/sinfo                    (SLURM state)
                        │
                        ▼ parse + inject cluster="school"
                        │
Mac ────HTTP POST───────► VictoriaMetrics (:8428/api/v1/import/prometheus)
```
