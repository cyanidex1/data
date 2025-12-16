#!/usr/bin/env bash
set -e

# check for params
while getopts b:e: flag
do
    case "${flag}" in
        b) b=${OPTARG};;
        e) env=${OPTARG};;
    esac
done

if [[ -z "$b" ]]; then
    echo "ERR: brand variable required, use '-b {BRAND}' and optionally add an environment variable '-e {ENV}'"
    exit 1
fi

# Validate required environment variables
if [[ -z "$NODE_EMAIL" ]]; then
    echo "ERR: NODE_EMAIL environment variable is required"
    exit 1
fi
if [[ -z "$NODE_PASSWORD" ]]; then
    echo "ERR: NODE_PASSWORD environment variable is required"
    exit 1
fi

node_name="${NODE_NAME:-win-node}"

# prep brand name for download
brand="$b-$env"
if [[ $env != "dev" && $env != "stage" ]]; then
    brand="$b-node"
    env="release"
fi

# ensure string is lowercase
brand=$(echo "$brand" | tr '[:upper:]' '[:lower:]')

# set download vars
domain="static.connectblockchain.net"
node="/usr/local/bin/$brand"
config_file="/root/.${brand}/config.json"

# set log level based on environment
log="debug"
if [[ $env != "dev" && $env != "stage" ]]; then
    log="info"
fi

# Authentication retry settings - exit after 3 failed attempts
max_auth_attempts=3
auth_attempt=0
max_node_restarts=3
node_restart_count=0

# Loop to handle node crash, redownload and reconfigure (limited restarts)
while true; do
    echo "[*] Downloading and configuring the binary..."

    # Prepare download URL with fresh timestamp
    date=$(date +%s)
    download_url="https://$domain/go-node/$env/${brand}_linux-amd64?$date"
    
    echo "[*] brand=$brand"
    echo "[*] download_url=$download_url"

    # Download the binary
    wget "$download_url" --output-document "$node" --quiet || {
        echo "[!] Failed to download binary, retrying in 10 seconds..."
        sleep 10
        continue
    }
    chmod +x "$node"

    # Auto-fill Win Email and Win Password using expect with error detection
    config_output=$(mktemp)
    expect <<EOF > "$config_output" 2>&1 || true
        set timeout 30
        spawn $node config
        expect {
            "Win Username or Email:" {
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
            "Win Password:" {
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
            "Win Node Name:" {
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

    echo "[*] Win configuration complete!"

    # Run the node with logging
    echo "[*] Starting node..."
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
