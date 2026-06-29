"""Scrape DCGM metrics from compute nodes via SSH + curl."""

import logging
import re

from .ssh import SSHManager

logger = logging.getLogger(__name__)

# Regex to match a Prometheus metric line: name{labels} value [timestamp]
_METRIC_LINE_RE = re.compile(
    r'^([a-zA-Z_:][a-zA-Z0-9_:]*)'  # metric name
    r'(\{[^}]*\})?'                   # optional labels
    r'\s+'
    r'([^\s]+)'                        # value
    r'(?:\s+(\d+))?$'                  # optional timestamp
)


def scrape_dcgm(
    ssh: SSHManager,
    nodes: list[str],
    extra_labels: dict[str, str],
    max_parallel: int = 10,
    curl_timeout: int = 3,
) -> list[str]:
    """Scrape DCGM exporter on multiple nodes, return Prometheus text lines with injected labels."""
    if not nodes:
        return []

    cmds = [
        f'curl -s --connect-timeout {curl_timeout} http://{node}:9400/metrics'
        for node in nodes
    ]

    raw_outputs = ssh.run_parallel(cmds, max_concurrent=max_parallel, timeout=curl_timeout + 5)

    all_lines: list[str] = []
    label_suffix = _build_label_suffix(extra_labels)

    for node, output in zip(nodes, raw_outputs):
        if not output:
            logger.debug("No DCGM data from %s", node)
            continue
        node_lines = _parse_and_inject(output, label_suffix)
        all_lines.extend(node_lines)

    logger.info("Scraped %d metric lines from %d/%d nodes", len(all_lines), sum(1 for o in raw_outputs if o), len(nodes))
    return all_lines


def _build_label_suffix(labels: dict[str, str]) -> str:
    """Build a label string like: ,cluster="school",job="school-dcgm-exporter" """
    if not labels:
        return ""
    parts = [f'{k}="{v}"' for k, v in labels.items()]
    return "," + ",".join(parts)


def _parse_and_inject(raw: str, label_suffix: str) -> list[str]:
    """Parse Prometheus text, inject extra labels into each metric line."""
    lines: list[str] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        m = _METRIC_LINE_RE.match(line)
        if not m:
            continue

        name = m.group(1)
        labels_block = m.group(2) or ""
        value = m.group(3)

        if labels_block:
            # Insert extra labels before the closing brace
            new_labels = labels_block[:-1] + label_suffix + "}"
        else:
            # No existing labels, create label block
            new_labels = "{" + label_suffix.lstrip(",") + "}"

        lines.append(f"{name}{new_labels} {value}")
    return lines
