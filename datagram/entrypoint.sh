#!/bin/sh

echo "[*] Starting Datagram container..."

if [ -z "$LICENSE_KEY" ]; then
  echo "[!] Error: LICENSE_KEY environment variable is not set." >&2
  exit 1
fi

# Check if this is first run (volume is empty)
if [ ! -d "/root/.datagram/vpn" ] || [ ! -d "/root/.datagram/conference" ]; then
  echo "[*] First run detected - VPN and Conference CLI will be downloaded"
  echo "[*] This may take 30-60 seconds..."
fi

echo "[*] Running datagram with key: $LICENSE_KEY"
exec /usr/local/bin/datagram run -- -key "$LICENSE_KEY"
