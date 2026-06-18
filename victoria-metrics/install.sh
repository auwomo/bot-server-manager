#!/bin/bash
set -euo pipefail

VM_VERSION="${VM_VERSION:-1.143.0}"
VM_DATA_DIR="/var/lib/victoria-metrics"
VM_USER="victoriametrics"
VM_BINARY="/usr/local/bin/victoria-metrics-prod"

echo "==> Installing VictoriaMetrics v${VM_VERSION}..."

if [ -f "$VM_BINARY" ]; then
    echo "    Binary already exists at $VM_BINARY, skipping download."
else
    ARCHIVE="victoria-metrics-linux-amd64-v${VM_VERSION}.tar.gz"
    URL="https://github.com/VictoriaMetrics/VictoriaMetrics/releases/download/v${VM_VERSION}/${ARCHIVE}"

    echo "    Downloading from ${URL}..."
    wget -q --show-progress -O "/tmp/${ARCHIVE}" "$URL"

    echo "    Extracting..."
    tar xzf "/tmp/${ARCHIVE}" -C /tmp/
    mv /tmp/victoria-metrics-prod "$VM_BINARY"
    chmod +x "$VM_BINARY"
    rm -f "/tmp/${ARCHIVE}"
fi

echo "==> Creating system user '${VM_USER}'..."
if ! id "$VM_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$VM_USER"
fi

echo "==> Creating data directory ${VM_DATA_DIR}..."
mkdir -p "$VM_DATA_DIR"
chown "$VM_USER:$VM_USER" "$VM_DATA_DIR"

echo "==> Installing systemd service..."
cp "$(dirname "$0")/victoriametrics.service" /etc/systemd/system/victoriametrics.service

if [ ! -f /etc/default/victoriametrics ]; then
    echo "==> Creating /etc/default/victoriametrics (env file)..."
    cat > /etc/default/victoriametrics <<'EOF'
VM_AUTH_USER=writer
VM_AUTH_PASS=CHANGE_ME_TO_A_STRONG_PASSWORD
EOF
    echo "    !! IMPORTANT: Edit /etc/default/victoriametrics to set a real password!"
fi

echo "==> Enabling and starting service..."
systemctl daemon-reload
systemctl enable victoriametrics
systemctl start victoriametrics

echo "==> Done! VictoriaMetrics is running."
echo "    Verify: curl -u \$(grep VM_AUTH_USER /etc/default/victoriametrics | cut -d= -f2):\$(grep VM_AUTH_PASS /etc/default/victoriametrics | cut -d= -f2) http://localhost:8428/api/v1/query?query=up"
echo "    Web UI: http://localhost:8428/vmui"
