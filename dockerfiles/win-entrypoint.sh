#!/bin/sh
set -e

echo "[*] Starting Win node..."

# Validate required environment variables
if [ -z "$NODE_EMAIL" ]; then
    echo "[!] Error: NODE_EMAIL environment variable is not set." >&2
    exit 1
fi

if [ -z "$NODE_PASSWORD" ]; then
    echo "[!] Error: NODE_PASSWORD environment variable is not set." >&2
    exit 1
fi

# Use environment variables or defaults
brand="${BRAND:-win}"
env="release"

# Prep brand name for download
brand_name="$brand-node"

# Set download vars
domain="static.connectblockchain.net"
date=$(date +%s)
download_url="https://$domain/go-node/$env/${brand_name}_linux-amd64?$date"
node="/home/nodeuser/$brand_name"

echo "[*] brand=$brand"
echo "[*] download_url=$download_url"

# Download and config node if not exists
if [ ! -f "$node" ]; then
    echo "[*] Binary not found. Downloading and configuring..."
    wget "$download_url" -O "$node" --quiet || {
        echo "[!] Failed to download binary, retrying in 10 seconds..."
        sleep 10
        exec "$0"
    }
    chmod +x "$node"
    
    # Auto-fill Win Email and Win Password using expect
    expect <<EOF
        spawn $node config
        expect "Win Email:"
        send "${NODE_EMAIL}\r"
        expect "Win Password:"
        send "${NODE_PASSWORD}\r"
        expect eof
EOF
else
    echo "[*] Binary already exists. Skipping download and configuration."
fi

# Run the node in a loop to keep it running
while true; do
    echo "[*] Starting node..."
    NODE_LOG_LEVEL=info $node
    echo "[!] Node crashed with exit code $?; restarting..."
    sleep 5
done
