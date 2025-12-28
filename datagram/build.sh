#!/bin/bash
# Build script for datagram Docker image
# This script ensures binaries are downloaded before building

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARIES_DIR="$SCRIPT_DIR/binaries/.datagram"

echo "[*] Datagram Docker Image Build"
echo ""

# Check if binaries exist
if [ ! -d "$BINARIES_DIR" ]; then
    echo "[!] Error: Binaries not found at $BINARIES_DIR"
    echo ""
    echo "You need to download the VPN and Conference CLI binaries first."
    echo "Run the following command:"
    echo ""
    echo "    cd $SCRIPT_DIR && ./download-binaries.sh"
    echo ""
    echo "This will take about 90 seconds to download both CLIs."
    exit 1
fi

# Verify both CLI tools exist
CONFERENCE_CLI="$BINARIES_DIR/conference/binaries/datagram-conference-cli-x86_64-linux"
VPN_CLI="$BINARIES_DIR/vpn/binaries/datagram-vpn-cli-x86_64-linux"

if [ ! -f "$CONFERENCE_CLI" ]; then
    echo "[!] Error: Conference CLI binary not found"
    echo "Expected at: $CONFERENCE_CLI"
    echo "Please run: ./download-binaries.sh"
    exit 1
fi

if [ ! -f "$VPN_CLI" ]; then
    echo "[!] Error: VPN CLI binary not found"
    echo "Expected at: $VPN_CLI"
    echo "Please run: ./download-binaries.sh"
    exit 1
fi

echo "[*] Pre-downloaded binaries verified:"
echo "    ✓ Conference CLI"
echo "    ✓ VPN CLI"
echo ""

# Build the image
echo "[*] Building datagram Docker image..."
docker build --platform linux/amd64 -t datagram "$SCRIPT_DIR"

if [ $? -eq 0 ]; then
    echo ""
    echo "[*] ✓ Image built successfully!"
    echo ""
    echo "You can now run containers with:"
    echo "    docker run -d --privileged -e LICENSE_KEY='your-key' datagram"
else
    echo ""
    echo "[!] Build failed!"
    exit 1
fi
