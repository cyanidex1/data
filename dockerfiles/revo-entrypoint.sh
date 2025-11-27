#!/bin/sh
set -e

echo "[*] Starting RevoRide node..."

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
brand="${BRAND:-revoride}"
chain="${CHAIN:-revoride}"
domain="${DOMAIN:-revoride.com}"
env="prod"
version="${VERSION:-v2.6.5}"
node_name="${NODE_NAME:-revoride-node}"

# Determine architecture type
arch=$(uname -m)
type="amd64"
if [ "$arch" = "arm64" ]; then
    type="arm64"
fi

# Set node binary path
node="/home/nodeuser/$chain"
config_file="/home/nodeuser/.${chain}/config.json"

# Authentication retry settings - exit after 3 failed attempts
max_auth_attempts=3
auth_attempt=0

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

    # Auto-fill configuration using expect with Firebase error detection
    config_output=$(mktemp)
    expect <<EOF > "$config_output" 2>&1 || true
        set timeout 30
        spawn $node config
        expect {
            "RevoRide Username or Email:" {
                send "${NODE_EMAIL}\r"
            }
            timeout {
                puts "Timeout waiting for email prompt"
                exit 1
            }
            eof {
                puts "Process exited before email prompt"
                exit 1
            }
        }
        expect {
            "RevoRide Password:" {
                send "${NODE_PASSWORD}\r"
            }
            timeout {
                puts "Timeout waiting for password prompt"
                exit 1
            }
            eof {
                puts "Process exited before password prompt"
                exit 1
            }
        }
        expect {
            "RevoRide Node Name:" {
                send "${node_name}\r"
            }
            timeout {
                puts "Timeout waiting for node name prompt"
                exit 1
            }
            eof {
                puts "Process exited before node name prompt"
                exit 1
            }
        }
        expect eof
EOF

    # Check for Firebase authentication errors
    if grep -qi "firebase\|invalid\|429\|unauthorized\|authentication" "$config_output"; then
        auth_attempt=$((auth_attempt + 1))
        echo "[!] Authentication error detected (attempt $auth_attempt/$max_auth_attempts)"
        cat "$config_output"
        rm -f "$config_output"
        
        if [ $auth_attempt -ge $max_auth_attempts ]; then
            echo "[!] ============================================"
            echo "[!] AUTHENTICATION ERROR: Max attempts reached ($max_auth_attempts)"
            echo "[!] Please verify your credentials and try again."
            echo "[!] Email: $NODE_EMAIL"
            echo "[!] ============================================"
            exit 1
        fi
        
        # Remove config and binary to force fresh re-authentication
        rm -f "$config_file" "$node"
        echo "[*] Restarting authentication (attempt $((auth_attempt + 1))/$max_auth_attempts) in 10 seconds..."
        sleep 10
        continue
    fi
    
    rm -f "$config_output"
    # Reset auth attempt count on success
    auth_attempt=0

    echo "[*] RevoRide configuration complete!"

    # Run the node with logging
    echo "[*] Starting node..."
    NODE_LOG_LEVEL=info $node
    exit_code=$?

    echo "[!] Node crashed with exit code $exit_code; restarting from scratch..."
    sleep 5
done
