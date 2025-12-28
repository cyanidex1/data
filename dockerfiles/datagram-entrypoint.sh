#!/bin/sh
set -e

echo "[*] Starting Datagram container..."

if [ -z "$LICENSE_KEY" ]; then
  echo "[!] Error: LICENSE_KEY environment variable is not set." >&2
  exit 1
fi

echo "[*] Running datagram with provided key"
exec sudo -H /usr/local/bin/datagram run -- -key "$LICENSE_KEY"
