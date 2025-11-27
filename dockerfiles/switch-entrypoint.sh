#!/bin/sh
set -e

echo "[*] Starting Switch node..."

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
brand="${BRAND:-switch}"
chain="${CHAIN:-switch}"
domain="${DOMAIN:-switchrewardcard.com}"
env="prod"
version="${VERSION:-v2.6.1-b}"
node_name="${NODE_NAME:-switch-node}"

# Determine architecture type
arch=$(uname -m)
type="amd64"
if [ "$arch" = "arm64" ]; then
    type="arm64"
fi

# Set node binary path
node="/usr/local/bin/$chain"

# Infinite loop to handle node crash, redownload and reconfigure
while true; do
    echo "[*] Downloading and configuring the binary..."

    # Prepare download URL
    base_url="download.$domain"
    date=$(date +%s)
    download_url="https://${base_url}/node-binaries/${version}/${chain}-${version}_linux-${type}?${date}"
    
    echo "[*] brand=$brand"
    echo "[*] chain=$chain"
    echo "[*] version=$version"
    echo "[*] domain=$domain"
    echo "[*] download_url=$download_url"

    # Download the binary
    wget "$download_url" -O "$node" --quiet || {
        echo "[!] Failed to download binary, retrying in 10 seconds..."
        sleep 10
        continue
    }
    chmod +x "$node"

    # Auto-fill configuration using expect
    expect <<EOF
        spawn $node config
        expect "Switch Username or Email:"
        send "${NODE_EMAIL}\r"
        expect "Switch Password:"
        send "${NODE_PASSWORD}\r"
        expect "Switch Node Name:"
        send "${node_name}\r"
        expect eof
EOF

    # Run the node with logging
    echo "[*] Starting node..."
    NODE_LOG_LEVEL=info $node
    exit_code=$?

    echo "[!] Node crashed with exit code $exit_code; restarting from scratch..."
    sleep 5
done
