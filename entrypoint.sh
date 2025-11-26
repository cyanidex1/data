#!/bin/bash

echo "[*] Starting Datagram container..."

if [ -z "$DATAGRAM_KEY" ]; then
  echo "[!] Error: DATAGRAM_KEY environment variable is not set." >&2
  exit 1
fi

echo "[*] Running datagram with key: $DATAGRAM_KEY"
datagram run -- -key "$DATAGRAM_KEY"
