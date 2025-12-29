#!/bin/sh

echo "[*] Starting Datagram container..."

if [ -z "$LICENSE_KEY" ]; then
  echo "[!] Error: LICENSE_KEY environment variable is not set." >&2
  exit 1
fi

# Initialize /root/.datagram from template if it's empty or doesn't exist
# This happens on first run when a new volume is mounted
if [ ! -d "/root/.datagram/vpn" ] || [ ! -d "/root/.datagram/conference" ]; then
  echo "[*] Initializing .datagram directory from template..."
  
  # Check if template exists
  if [ -d "/opt/.datagram-template" ]; then
    # Copy template contents to /root/.datagram
    cp -r /opt/.datagram-template/* /root/.datagram/ 2>/dev/null || true
    cp -r /opt/.datagram-template/.[!.]* /root/.datagram/ 2>/dev/null || true
    echo "[*] Template copied successfully"
  else
    echo "[!] Warning: Template directory not found at /opt/.datagram-template"
    echo "[*] Datagram will download VPN and Conference CLI binaries on first run"
  fi
else
  echo "[*] Using existing .datagram configuration from volume"
fi

echo "[*] Running datagram with key: $LICENSE_KEY"
exec /usr/local/bin/datagram run -- -key "$LICENSE_KEY"
