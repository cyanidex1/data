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

# Download binaries for datagram if not already present
download_datagram_binaries() {
    local binaries_dir="$DOCKERFILES_DIR/binaries"
    
    if [ -d "$binaries_dir/.datagram" ]; then
        echo "[*] Datagram binaries already exist, skipping download..."
        return 0
    fi
    
    echo "[*] Downloading datagram binaries (VPN and Conference CLI)..."
    
    if [ -x "$DOCKERFILES_DIR/download-binaries.sh" ]; then
        cd "$DOCKERFILES_DIR"
        ./download-binaries.sh || {
            echo "[!] Warning: Failed to download datagram binaries"
            return 1
        }
        cd - > /dev/null
    else
        echo "[!] Warning: download-binaries.sh not found or not executable"
        return 1
    fi
    
    return 0
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
    
    # For datagram, ensure binaries are downloaded first
    if [ "$node_type" = "datagram" ]; then
        download_datagram_binaries || {
            echo "[!] Warning: Failed to download datagram binaries, build may fail"
        }
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
