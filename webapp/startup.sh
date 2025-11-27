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

build_images() {
    echo "[*] Building Docker images for all node types..."
    
    for node_type in "${!NODE_IMAGES[@]}"; do
        image_name="${NODE_IMAGES[$node_type]}"
        dockerfile="$DOCKERFILES_DIR/${node_type}.Dockerfile"
        
        if [ -f "$dockerfile" ]; then
            echo "[*] Building image: $image_name from $dockerfile"
            
            # Check if image already exists
            if docker image inspect "$image_name" > /dev/null 2>&1; then
                echo "[*] Image $image_name already exists, skipping..."
            else
                docker build -t "$image_name" -f "$dockerfile" "$DOCKERFILES_DIR" || {
                    echo "[!] Warning: Failed to build $image_name, continuing..."
                }
            fi
        else
            echo "[!] Warning: Dockerfile not found: $dockerfile"
        fi
    done
    
    # Mark images as built
    touch "$IMAGES_BUILT_FLAG"
    echo "[*] All images built successfully!"
}

# Check if this is the first run
if [ ! -f "$IMAGES_BUILT_FLAG" ]; then
    echo "[*] First startup detected, building node images..."
    build_images
else
    echo "[*] Images already built on previous startup"
    
    # Optionally rebuild missing images
    echo "[*] Checking for missing images..."
    for node_type in "${!NODE_IMAGES[@]}"; do
        image_name="${NODE_IMAGES[$node_type]}"
        if ! docker image inspect "$image_name" > /dev/null 2>&1; then
            dockerfile="$DOCKERFILES_DIR/${node_type}.Dockerfile"
            if [ -f "$dockerfile" ]; then
                echo "[*] Rebuilding missing image: $image_name"
                docker build -t "$image_name" -f "$dockerfile" "$DOCKERFILES_DIR" || {
                    echo "[!] Warning: Failed to build $image_name"
                }
            fi
        fi
    done
fi

echo "[*] Starting Datagram Control Panel..."
exec python app.py
