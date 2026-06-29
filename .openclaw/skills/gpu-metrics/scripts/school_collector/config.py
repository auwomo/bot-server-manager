"""Configuration for the school HPC collector daemon."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SSHConfig:
    host: str = "172.16.78.35"
    port: int = 10024
    username: str = "mazijian"
    password_env: str = "SCHOOL_SSH_PASSWORD"

    @property
    def password(self) -> str:
        return os.environ.get(self.password_env, "")


@dataclass
class VMConfig:
    url: str = "http://localhost:8428"
    auth_user_env: str = "VM_AUTH_USER"
    auth_pass_env: str = "VM_AUTH_PASS"

    @property
    def auth_user(self) -> str:
        return os.environ.get(self.auth_user_env, "")

    @property
    def auth_pass(self) -> str:
        return os.environ.get(self.auth_pass_env, "")

    @property
    def auth(self) -> tuple[str, str] | None:
        user = self.auth_user
        if user:
            return (user, self.auth_pass)
        return None


@dataclass
class ScrapeConfig:
    dcgm_interval: int = 30
    slurm_interval: int = 60
    max_parallel: int = 10
    curl_timeout: int = 3


@dataclass
class Config:
    ssh: SSHConfig = field(default_factory=SSHConfig)
    vm: VMConfig = field(default_factory=VMConfig)
    scrape: ScrapeConfig = field(default_factory=ScrapeConfig)
    labels: dict[str, str] = field(default_factory=lambda: {
        "cluster": "school",
        "job": "school-dcgm-exporter",
    })

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        if path is None:
            path = os.environ.get(
                "SCHOOL_COLLECTOR_CONFIG",
                str(Path.home() / ".school-collector.yaml"),
            )
        config = cls()
        if Path(path).exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            if "ssh" in data:
                for k, v in data["ssh"].items():
                    if hasattr(config.ssh, k):
                        setattr(config.ssh, k, v)
            if "vm" in data:
                for k, v in data["vm"].items():
                    if hasattr(config.vm, k):
                        setattr(config.vm, k, v)
            if "scrape" in data:
                for k, v in data["scrape"].items():
                    if hasattr(config.scrape, k):
                        setattr(config.scrape, k, v)
            if "labels" in data:
                config.labels.update(data["labels"])
        return config
