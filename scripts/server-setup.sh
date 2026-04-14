#!/usr/bin/env bash
# =============================================================================
# LIPI — Remote server bootstrap
# Target: Ubuntu 22.04 LTS, bare-metal with 2× NVIDIA L40S
#
# Run once as root (or with sudo) on a fresh server:
#   curl -fsSL https://raw.githubusercontent.com/.../server-setup.sh | bash
#   — or —
#   scp scripts/server-setup.sh root@<server>:~ && ssh root@<server> bash server-setup.sh
#
# What this does:
#   1. System update + essential packages
#   2. NVIDIA driver 535 + CUDA 12.1
#   3. Docker CE + nvidia-container-toolkit
#   4. UFW firewall (22/80/443 only)
#   5. Sysctl tuning (network + file limits)
#   6. Create deploy user + clone repo to /opt/lipi
# =============================================================================

set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/YOUR_ORG/lipi.git}"
DEPLOY_USER="lipi"
DEPLOY_DIR="/opt/lipi"
LOG="/var/log/lipi-setup.log"

exec > >(tee -a "$LOG") 2>&1
echo "=== LIPI server setup started at $(date) ==="

# ─── 1. System update ────────────────────────────────────────────────────────
echo "[1/6] System update..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y --no-install-recommends \
    curl wget git make jq unzip \
    ca-certificates gnupg lsb-release \
    ufw htop tmux \
    build-essential

# ─── 2. NVIDIA driver 535 + CUDA 12.1 ────────────────────────────────────────
echo "[2/6] Installing NVIDIA driver 535..."
if ! nvidia-smi &>/dev/null; then
    # Add NVIDIA package repo
    wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
    dpkg -i cuda-keyring_1.1-1_all.deb
    rm cuda-keyring_1.1-1_all.deb
    apt-get update -qq
    apt-get install -y --no-install-recommends \
        cuda-drivers-535 \
        cuda-toolkit-12-1
    echo "NVIDIA driver installed. A reboot is required before GPUs are usable."
else
    echo "NVIDIA driver already present: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)"
fi

# ─── 3. Docker CE ─────────────────────────────────────────────────────────────
echo "[3/6] Installing Docker CE..."
if ! docker info &>/dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
else
    echo "Docker already installed: $(docker --version)"
fi

# nvidia-container-toolkit
echo "Installing nvidia-container-toolkit..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    > /etc/apt/sources.list.d/nvidia-container-toolkit.list
apt-get update -qq
apt-get install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

# Test GPU passthrough
echo "GPU passthrough test..."
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 \
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader \
    || echo "WARNING: GPU passthrough test failed — reboot may be required"

# ─── 4. Firewall ─────────────────────────────────────────────────────────────
echo "[4/6] Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    comment "SSH"
ufw allow 80/tcp    comment "HTTP (Caddy redirect)"
ufw allow 443/tcp   comment "HTTPS"
ufw allow 443/udp   comment "HTTP/3 QUIC"
# Internal service ports (only from localhost — not exposed externally)
ufw deny 5432/tcp   comment "Postgres — internal only"
ufw deny 6379/tcp   comment "Valkey — internal only"
ufw deny 8000/tcp   comment "Backend — internal only"
ufw deny 8080/tcp   comment "vLLM — internal only"
ufw deny 5001/tcp   comment "ML service — internal only"
ufw deny 9000/tcp   comment "MinIO API — internal only"
ufw deny 9001/tcp   comment "MinIO console — use SSH tunnel"
ufw --force enable
echo "UFW status:"
ufw status verbose

# ─── 5. Sysctl tuning ────────────────────────────────────────────────────────
echo "[5/6] Sysctl tuning..."
cat > /etc/sysctl.d/99-lipi.conf << 'EOF'
# Network tuning for high-throughput WebSocket workloads
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 1024 65535
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# File descriptor limits for many concurrent WebSocket connections
fs.file-max = 2097152
fs.nr_open = 2097152
EOF
sysctl --system

cat > /etc/security/limits.d/99-lipi.conf << 'EOF'
*    soft nofile 1048576
*    hard nofile 1048576
root soft nofile 1048576
root hard nofile 1048576
EOF

# ─── 6. Deploy user + repo ────────────────────────────────────────────────────
echo "[6/6] Creating deploy user and cloning repo..."
if ! id "$DEPLOY_USER" &>/dev/null; then
    useradd -r -m -s /bin/bash "$DEPLOY_USER"
    usermod -aG docker "$DEPLOY_USER"
    echo "Deploy user '$DEPLOY_USER' created."
fi

mkdir -p "$DEPLOY_DIR"
chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"

if [ ! -d "$DEPLOY_DIR/.git" ]; then
    sudo -u "$DEPLOY_USER" git clone "$REPO_URL" "$DEPLOY_DIR"
    echo "Repo cloned to $DEPLOY_DIR"
else
    echo "Repo already present at $DEPLOY_DIR"
fi

# Create .env from .env.example if missing
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"
    echo ""
    echo "================================================================="
    echo "  ACTION REQUIRED: Edit $DEPLOY_DIR/.env before deploying!"
    echo "  Fill in: POSTGRES_PASSWORD, JWT_SECRET, GOOGLE_CLIENT_*,"
    echo "           CADDY_DOMAIN, CADDY_EMAIL, GROQ_API_KEY (optional)"
    echo "================================================================="
fi

echo ""
echo "=== Setup complete at $(date) ==="
echo ""
echo "Next steps:"
echo "  1. Reboot if NVIDIA driver was just installed: sudo reboot"
echo "  2. Edit /opt/lipi/.env with production values"
echo "  3. Run: sudo -u lipi bash /opt/lipi/scripts/deploy.sh"
echo ""
echo "Verify GPU after reboot:"
echo "  nvidia-smi"
echo "  docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi"
