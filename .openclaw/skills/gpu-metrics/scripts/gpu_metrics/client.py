import requests
from .config import Config


class VMClient:
    def __init__(self, config: Config):
        self.base_url = config.vm_url.rstrip("/")
        self.auth = None
        if config.vm_auth_user:
            self.auth = (config.vm_auth_user, config.vm_auth_pass)

    def query(self, promql: str) -> dict:
        resp = requests.get(
            f"{self.base_url}/api/v1/query",
            params={"query": promql},
            auth=self.auth,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def query_range(self, promql: str, start: str, end: str, step: str = "60s") -> dict:
        resp = requests.get(
            f"{self.base_url}/api/v1/query_range",
            params={"query": promql, "start": start, "end": end, "step": step},
            auth=self.auth,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def labels(self) -> list[str]:
        resp = requests.get(
            f"{self.base_url}/api/v1/labels",
            auth=self.auth,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def label_values(self, label: str) -> list[str]:
        resp = requests.get(
            f"{self.base_url}/api/v1/label/{label}/values",
            auth=self.auth,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def series(self, match: str) -> list[dict]:
        resp = requests.get(
            f"{self.base_url}/api/v1/series",
            params={"match[]": match},
            auth=self.auth,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def health(self) -> dict:
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/query",
                params={"query": "vm_app_version"},
                auth=self.auth,
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            result = data.get("data", {}).get("result", [])
            version = result[0]["metric"].get("version", "unknown") if result else "unknown"
            return {"status": "ok", "version": version}
        except Exception as e:
            return {"status": "error", "error": str(e)}
