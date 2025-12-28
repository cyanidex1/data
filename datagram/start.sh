#!/bin/bash

# Usage: ./start.sh <LICENSE_KEY> [CONTAINER_NAME_PREFIX]

if [ $# -lt 1 ]; then
  echo "Usage: $0 <LICENSE_KEY> [CONTAINER_NAME_PREFIX]"
  exit 1
fi

LICENSE_KEY="$1"
CONTAINER_PREFIX="${2:-node}"  # Default to "node" if not provided

# Container ulimit for file descriptors (default: 8192)
# Can be overridden via CONTAINER_ULIMIT environment variable
# 8192 is sufficient for VPN/WireGuard while allowing 500+ containers
CONTAINER_ULIMIT="${CONTAINER_ULIMIT:-8192}"

# Build image if not already built
if ! docker image inspect datagram > /dev/null 2>&1; then
  echo "[*] Building Docker image 'datagram'..."
  docker build --platform linux/amd64 -t datagram .
fi

# Auto-increment container name
INDEX=1
while docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_PREFIX}${INDEX}$"; do
  INDEX=$((INDEX + 1))
done
CONTAINER_NAME="${CONTAINER_PREFIX}${INDEX}"

echo "[*] Launching container '$CONTAINER_NAME' in background..."
echo "[*] Using ulimit: $CONTAINER_ULIMIT file descriptors"

# Use specific capabilities instead of --privileged
# NET_ADMIN: Create and manage network interfaces (TUN/TAP for VPN)
# NET_RAW: Use raw and packet sockets
# SYS_MODULE: Load kernel modules (for WireGuard if needed)
# Using host network mode to allow WireGuard wg0 interface creation
# Note: This means containers share the host's network namespace
docker run \
  --platform linux/amd64 \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  --cap-add=SYS_MODULE \
  --device=/dev/net/tun:/dev/net/tun \
  --network=host \
  --env LICENSE_KEY="$LICENSE_KEY" \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  --ulimit nofile=${CONTAINER_ULIMIT}:${CONTAINER_ULIMIT} \
  -d \
  datagram
