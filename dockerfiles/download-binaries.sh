#!/bin/bash
set -e

echo "[*] Downloading Datagram CLI binaries..."

# Create temporary directory for binaries
BINARIES_DIR="$(dirname "$0")/binaries"
mkdir -p "$BINARIES_DIR"

# Build a temporary image if needed
echo "[*] Building temporary image for binary extraction..."
docker build --platform linux/amd64 -t datagram-temp:latest -f- "$(dirname "$0")" <<'DOCKERFILE'
FROM alpine:3.19

# Install curl for downloading the binary, procps for health check
RUN apk add --no-cache curl procps

# Download binary from GitHub releases
RUN curl -fsSL \
  "https://github.com/Datagram-Group/datagram-cli-release/releases/latest/download/datagram-cli-x86_64-linux" \
  -o /usr/local/bin/datagram && \
  chmod +x /usr/local/bin/datagram

WORKDIR /root
DOCKERFILE

# Start a privileged container to download all CLI tools
echo "[*] Starting temporary privileged container to download CLI tools..."
CONTAINER_ID=$(docker run -d --rm --privileged \
  -e LICENSE_KEY="92bcf2ae4e326968f40f8670a3596b80" \
  --platform linux/amd64 \
  datagram-temp:latest \
  /usr/local/bin/datagram run -- -key 92bcf2ae4e326968f40f8670a3596b80)

echo "[*] Container ID: $CONTAINER_ID"
echo "[*] Waiting for CLI tools to download (90 seconds)..."
sleep 90

# Extract the binaries
echo "[*] Extracting binaries from container..."
docker cp "$CONTAINER_ID:/root/.datagram" "$BINARIES_DIR/" || {
  echo "[!] Failed to extract binaries"
  docker stop "$CONTAINER_ID" 2>/dev/null || true
  exit 1
}

# Stop the container
echo "[*] Stopping temporary container..."
docker stop "$CONTAINER_ID" || true

# Verify binaries were downloaded
echo "[*] Verifying downloaded binaries..."
if [ -d "$BINARIES_DIR/.datagram/conference" ]; then
  echo "  ✓ Conference CLI found"
else
  echo "  ✗ Conference CLI not found"
fi

if [ -d "$BINARIES_DIR/.datagram/vpn" ]; then
  echo "  ✓ VPN CLI found"
else
  echo "  ✗ VPN CLI not found"
fi

# Cleanup temp image - force remove since container might still be referenced
echo "[*] Cleaning up temporary image..."
docker rmi -f datagram-temp:latest 2>/dev/null || true

echo "[*] Binary download complete!"
echo "[*] Binaries saved to: $BINARIES_DIR"
