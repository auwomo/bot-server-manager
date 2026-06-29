import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Config:
    vm_url: str = "http://localhost:8428"
    vm_auth_user: str = ""
    vm_auth_pass: str = ""

    @classmethod
    def load(cls) -> "Config":
        config = cls()

        config_path = Path.home() / ".gpu-metrics.yaml"
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            config.vm_url = data.get("vm_url", config.vm_url)
            config.vm_auth_user = data.get("vm_auth_user", config.vm_auth_user)
            config.vm_auth_pass = data.get("vm_auth_pass", config.vm_auth_pass)

        config.vm_url = os.environ.get("VM_URL", config.vm_url)
        config.vm_auth_user = os.environ.get("VM_AUTH_USER", config.vm_auth_user)
        config.vm_auth_pass = os.environ.get("VM_AUTH_PASS", config.vm_auth_pass)

        return config
