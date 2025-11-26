#!/bin/bash

# Usage: ./start.sh <DATAGRAM_KEY> [CONTAINER_NAME_PREFIX]

if [ $# -lt 1 ]; then
  echo "Usage: $0 <DATAGRAM_KEY> [CONTAINER_NAME_PREFIX]"
  exit 1
fi

DATAGRAM_KEY="$1"
CONTAINER_PREFIX="${2:-node}"  # Default to "node" if not provided

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

docker run \
  --platform linux/amd64 \
  --env DATAGRAM_KEY="$DATAGRAM_KEY" \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  --memory="100m" \
  --memory-swap="200m" \
  -d \
  datagram
