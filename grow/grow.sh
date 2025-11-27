#!/usr/bin/env bash
set -e

# Default variables
brand="grow"
chain="grow"
domain="growblockchain.net"
env="prod"
version="v2.6.1-b"
arch=$(uname -m)

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

# Infinite loop to handle node crash, redownload and reconfigure
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
    wget "$download_url" -O "$node" --quiet
    chmod +x "$node"

    # Auto-fill configuration using expect
    expect <<EOF
        spawn $node config
        expect "Grow Username or Email:"
        send "hkabir5390@gmail.com\r"
        expect "Grow Password:"
        send "Hk07@#52\r"
        expect "Grow Node Name:"
        send "grow-node\r"
        expect eof
EOF

    # Run the node with logging
    NODE_LOG_LEVEL=$log $node
    exit_code=$?

    echo "Node crashed with exit code $exit_code; restarting from scratch..."
    sleep 5
done
