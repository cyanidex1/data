#!/usr/bin/env bash
set -e

# Default variables for Element Node
brand="element"
chain="element"
domain="elementunited.com"
env="prod"
version="v2.6.1-b"
arch=$(uname -m)
node_name="${NODE_NAME:-element-node}"

# Check for params
while getopts b:c:e:a:v:d: flag
do
    case "${flag}" in
        b) brand=${OPTARG};;
        c) chain=${OPTARG};;
        e) env=${OPTARG};;
        a) arch=${OPTARG};;
        v) version=${OPTARG};;
        d) domain=${OPTARG};;
    esac
done

# Validate required environment variables
if [[ -z "$NODE_EMAIL" ]]; then
    echo "ERR: NODE_EMAIL environment variable is required"
    exit 1
fi
if [[ -z "$NODE_PASSWORD" ]]; then
    echo "ERR: NODE_PASSWORD environment variable is required"
    exit 1
fi

# Validate required variables
if [[ -z "$brand" ]]; then
    echo "ERR: brand variable required, use '-b {BRAND}'"
    exit 1
fi
if [[ -z "$chain" ]]; then
    echo "ERR: chain variable required, use '-c {CHAIN}'"
    exit 1
fi

# Ensure string is lowercase
chain=$(echo "$chain" | tr '[:upper:]' '[:lower:]')
name="$chain-$env"
log="debug"

if [[ -z "$env" || ($env != "dev" && $env != "stage") ]]; then
    env="prod"
    name="$chain"
    log="info"
fi

# Determine architecture type
type="amd64"
if [[ $arch == "arm64" ]]; then
    type=$arch
fi

# Set node binary path
node="/usr/local/bin/$name"
config_file="/root/.${name}/config.json"

# Authentication retry settings - exit after 3 failed attempts
max_auth_attempts=3
auth_attempt=0
max_node_restarts=3
node_restart_count=0

# Loop to handle node crash, redownload and reconfigure (limited restarts)
while true; do
    echo "Redownloading and configuring the binary..."

    # Prepare download URL
    base_url="download.$env.$domain"
    [ "$env" = "prod" ] && base_url="download.$domain"
    date=$(date +%s)
    download_url="${base_url}/node-binaries/${version}/${chain}-${version}_linux-$type?$date"
    
    echo "brand=$brand"
    echo "chain=$chain"
    echo "env=$env"
    echo "arch=$arch"
    echo "version=$version"
    echo "domain=$domain"
    echo "download_url=$download_url"
    echo "name=$name"

    # Redownload the binary
    wget "$download_url" -O "$node" --quiet || {
        echo "[!] Failed to download binary, retrying in 10 seconds..."
        sleep 10
        continue
    }
    chmod +x "$node"

    # Auto-fill configuration using expect with error detection
    config_output=$(mktemp)
    expect <<EOF > "$config_output" 2>&1 || true
        set timeout 30
        spawn $node config
        expect {
            "Element Username or Email:" {
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
            "Element Password:" {
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
            "Element Node Name:" {
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

    # Check for authentication errors
    if grep -qi "firebase\|invalid\|429\|unauthorized\|authentication" "$config_output"; then
        auth_attempt=$((auth_attempt + 1))
        echo "[!] Authentication error detected (attempt $auth_attempt/$max_auth_attempts)"
        cat "$config_output"
        rm -f "$config_output"
        
        if [[ $auth_attempt -ge $max_auth_attempts ]]; then
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

    echo "Element configuration complete!"

    # Run the node with logging
    NODE_LOG_LEVEL=$log $node
    exit_code=$?

    # Increment restart counter
    node_restart_count=$((node_restart_count + 1))
    echo "[!] Node crashed with exit code $exit_code (restart $node_restart_count/$max_node_restarts)"
    
    # Exit if max restarts reached
    if [[ $node_restart_count -ge $max_node_restarts ]]; then
        echo "[!] ============================================"
        echo "[!] FAILED: Max node restarts reached ($max_node_restarts)"
        echo "[!] Container will exit. Check logs for errors."
        echo "[!] ============================================"
        exit 1
    fi
    
    echo "[*] Restarting from scratch in 5 seconds..."
    sleep 5
done
