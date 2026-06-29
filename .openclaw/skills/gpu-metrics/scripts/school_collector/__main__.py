"""School HPC cluster metrics collector daemon.

Connects to the school login node via SSH, scrapes DCGM metrics from
compute nodes, collects SLURM state, and pushes everything to VictoriaMetrics.
"""

import logging
import signal
import sys
import time

from .config import Config
from .pusher import Pusher
from .scraper import scrape_dcgm
from .slurm import get_active_nodes, get_all_metrics
from .ssh import SSHManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = Config.load()
    logger.info(
        "Starting school collector — SSH %s:%d, push to %s",
        config.ssh.host, config.ssh.port, config.vm.url,
    )

    ssh = SSHManager(config.ssh)
    pusher = Pusher(config.vm)

    running = True

    def _stop(signum, frame):
        nonlocal running
        logger.info("Received signal %d, shutting down...", signum)
        running = False

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    last_slurm_time = 0.0
    cycle = 0

    while running:
        cycle += 1
        cycle_start = time.time()
        logger.info("=== Cycle %d ===", cycle)

        try:
            # Discover active nodes (needed for DCGM scraping)
            nodes = get_active_nodes(ssh)

            # DCGM scrape (every cycle = every dcgm_interval seconds)
            if nodes:
                dcgm_lines = scrape_dcgm(
                    ssh, nodes,
                    extra_labels=config.labels,
                    max_parallel=config.scrape.max_parallel,
                    curl_timeout=config.scrape.curl_timeout,
                )
                if dcgm_lines:
                    ok = pusher.push(dcgm_lines)
                    logger.info("DCGM push: %d lines, success=%s", len(dcgm_lines), ok)

            # SLURM metrics (every slurm_interval)
            now = time.time()
            if now - last_slurm_time >= config.scrape.slurm_interval:
                slurm_lines = get_all_metrics(ssh, cluster_label=config.labels.get("cluster", "school"))
                if slurm_lines:
                    ok = pusher.push(slurm_lines)
                    logger.info("SLURM push: %d lines, success=%s", len(slurm_lines), ok)
                last_slurm_time = now

        except ConnectionError as e:
            logger.error("SSH connection lost: %s. Will retry next cycle.", e)
        except Exception as e:
            logger.exception("Unexpected error in cycle %d: %s", cycle, e)

        # Sleep until next DCGM interval
        elapsed = time.time() - cycle_start
        sleep_time = max(1, config.scrape.dcgm_interval - elapsed)
        logger.debug("Cycle took %.1fs, sleeping %.1fs", elapsed, sleep_time)

        # Interruptible sleep
        end = time.time() + sleep_time
        while running and time.time() < end:
            time.sleep(min(1.0, end - time.time()))

    ssh.close()
    logger.info("Collector stopped.")


if __name__ == "__main__":
    main()
