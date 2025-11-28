#!/bin/bash
set -e

DOCKERFILES_DIR="/app/dockerfiles"
IMAGES_BUILT_FLAG="/data/.images_built"

# Node types and their corresponding image names
declare -A NODE_IMAGES=(
    ["datagram"]="datagram"
    ["element"]="element-node"
    ["elevate"]="elevate-node"
    ["grow"]="grow-node"
    ["revo"]="revo-node"
    ["rlink"]="rlink-node"
    ["switch"]="switch-node"
    ["win"]="win-node"
)

# Start Tailscale daemon in the background
start_tailscaled() {
    echo "[*] Starting Tailscale daemon..."
    # Ensure state directory exists
    mkdir -p /var/lib/tailscale /var/run/tailscale
    
    # Start tailscaled in userspace networking mode (works without TUN device)
    tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock --tun=userspace-networking &
    
    # Wait for tailscaled to be ready (up to 10 seconds)
    local max_attempts=10
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if tailscale --socket=/var/run/tailscale/tailscaled.sock status &>/dev/null; then
            echo "[*] Tailscale daemon is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    echo "[!] Warning: Tailscale daemon may not be fully ready, continuing anyway..."
}

# Build a single Docker image
build_image() {
    local node_type="$1"
    local image_name="${NODE_IMAGES[$node_type]}"
    local dockerfile="$DOCKERFILES_DIR/${node_type}.Dockerfile"
    
    if [ ! -f "$dockerfile" ]; then
        echo "[!] Warning: Dockerfile not found: $dockerfile"
        return 1
    fi
    
    # Check if image already exists
    if docker image inspect "$image_name" > /dev/null 2>&1; then
        echo "[*] Image $image_name already exists, skipping..."
        return 0
    fi
    
    echo "[*] Building image: $image_name from $dockerfile"
    docker build -t "$image_name" -f "$dockerfile" "$DOCKERFILES_DIR" || {
        echo "[!] Warning: Failed to build $image_name"
        return 1
    }
    return 0
}

# Build all Docker images
build_all_images() {
    echo "[*] Building Docker images for all node types..."
    
    for node_type in "${!NODE_IMAGES[@]}"; do
        build_image "$node_type"
    done
    
    # Mark images as built
    touch "$IMAGES_BUILT_FLAG"
    echo "[*] All images processed!"
}

# Start Tailscale daemon
start_tailscaled

# Main startup logic
if [ ! -f "$IMAGES_BUILT_FLAG" ]; then
    echo "[*] First startup detected, building node images..."
    build_all_images
else
    echo "[*] Images already built on previous startup"
    echo "[*] Checking for missing images..."
    
    for node_type in "${!NODE_IMAGES[@]}"; do
        build_image "$node_type"
    done
fi

echo "[*] Starting Datagram Control Panel..."
exec python app.py
