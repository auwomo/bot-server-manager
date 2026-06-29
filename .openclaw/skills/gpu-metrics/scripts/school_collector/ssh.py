"""SSH connection manager with auto-reconnect and parallel command execution."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import paramiko

from .config import SSHConfig

logger = logging.getLogger(__name__)


class SSHManager:
    def __init__(self, config: SSHConfig):
        self._config = config
        self._client: paramiko.SSHClient | None = None
        self._lock = Lock()

    def connect(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            self._config.host,
            port=self._config.port,
            username=self._config.username,
            password=self._config.password,
            timeout=15,
            banner_timeout=15,
        )
        self._client = client
        logger.info("SSH connected to %s:%d", self._config.host, self._config.port)

    def _ensure_connected(self) -> paramiko.SSHClient:
        with self._lock:
            if self._client is None or not self._is_alive():
                self._reconnect()
            return self._client

    def _is_alive(self) -> bool:
        if self._client is None:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()

    def _reconnect(self, max_retries: int = 3) -> None:
        self.close()
        for attempt in range(max_retries):
            try:
                self.connect()
                return
            except Exception as e:
                wait = 2 ** attempt
                logger.warning(
                    "SSH connect attempt %d/%d failed: %s. Retrying in %ds...",
                    attempt + 1, max_retries, e, wait,
                )
                time.sleep(wait)
        raise ConnectionError(
            f"Failed to connect to {self._config.host}:{self._config.port} "
            f"after {max_retries} attempts"
        )

    def run(self, cmd: str, timeout: int = 30) -> str:
        client = self._ensure_connected()
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if err and "DeprecationWarning" not in err:
            logger.debug("stderr for '%s': %s", cmd[:60], err[:200])
        return out

    def run_parallel(
        self, cmds: list[str], max_concurrent: int = 10, timeout: int = 30
    ) -> list[str]:
        results = [""] * len(cmds)

        def _exec(idx: int, cmd: str) -> tuple[int, str]:
            return idx, self.run(cmd, timeout=timeout)

        with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
            futures = {
                pool.submit(_exec, i, cmd): i for i, cmd in enumerate(cmds)
            }
            for future in as_completed(futures):
                try:
                    idx, output = future.result()
                    results[idx] = output
                except Exception as e:
                    idx = futures[future]
                    logger.warning("Command %d failed: %s", idx, e)
                    results[idx] = ""
        return results

    def close(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
