import urllib.request
import base64

data = b"""test_gpu{node="node1",gpu="0"} 85.5
test_gpu{node="node1",gpu="1"} 72.3
test_gpu{node="node2",gpu="0"} 0
test_idle{cluster="digua"} 3
"""

req = urllib.request.Request(
    "http://localhost:8428/api/v1/import/prometheus",
    data=data,
    method="POST",
)
cred = base64.b64encode(b"writer:auwomo-gpu-monitor-2026").decode()
req.add_header("Authorization", f"Basic {cred}")
resp = urllib.request.urlopen(req)
print(f"Write status: {resp.status}")
