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
date=$(date +%s)
download_url="https://$domain/go-node/$env/${brand}_linux-amd64?$date"
node="/usr/local/bin/$brand"

# check if binary already exists
if [ ! -f "$node" ]; then
    echo "Binary not found. Downloading and configuring..."
    # download and config node
    wget "$download_url" --output-document "$node" --quiet
    chmod +x "$node"
    
    # Auto-fill Win Email and Win Password using expect
    expect <<EOF
        spawn $node config
        expect "Win Username or Email:"
        send "mdshafiulbashar13@gmail.com\r"
        expect "Win Password:"
        send "Jafri1234@\r"
        expect "Win Node Name:"
        send "win-node\r"
        expect eof
EOF
else
    echo "Binary already exists. Skipping download and configuration."
fi

# set log level based on environment
log="debug"
if [[ $env != "dev" && $env != "stage" ]]; then
    brand="$b"
    log="info"
fi

# run the node in a loop to keep it running
while true; do
    NODE_LOG_LEVEL=$log $node
    echo "Node crashed with exit code $?; restarting..."
    sleep 5
done
