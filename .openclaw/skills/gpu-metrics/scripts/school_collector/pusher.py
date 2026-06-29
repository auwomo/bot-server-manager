"""Push metrics to VictoriaMetrics in Prometheus exposition format."""

import logging

import requests

from .config import VMConfig

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000
PUSH_ENDPOINT = "/api/v1/import/prometheus"


class Pusher:
    def __init__(self, config: VMConfig):
        self._url = config.url.rstrip("/") + PUSH_ENDPOINT
        self._auth = config.auth
        self._session = requests.Session()
        if self._auth:
            self._session.auth = self._auth

    def push(self, metric_lines: list[str]) -> bool:
        if not metric_lines:
            return True

        success = True
        for i in range(0, len(metric_lines), BATCH_SIZE):
            batch = metric_lines[i : i + BATCH_SIZE]
            body = "\n".join(batch) + "\n"
            if not self._post(body):
                success = False
        return success

    def _post(self, body: str, retry: bool = True) -> bool:
        try:
            resp = self._session.post(
                self._url,
                data=body.encode(),
                headers={"Content-Type": "text/plain"},
                timeout=10,
            )
            if resp.status_code == 204 or resp.status_code == 200:
                return True
            logger.error(
                "Push failed: HTTP %d — %s", resp.status_code, resp.text[:200]
            )
        except requests.RequestException as e:
            logger.error("Push request error: %s", e)

        if retry:
            logger.info("Retrying push...")
            return self._post(body, retry=False)
        return False

    @property
    def metrics_pushed(self) -> str:
        return self._url
