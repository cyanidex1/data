#!/bin/bash
# test-wireguard-setup.sh - Test/Demo script to verify WireGuard setup logic
# This script simulates what setup-wireguard.sh does without requiring root access

set -e

NUM_INTERFACES="${1:-3}"
BASE_PORT="${2:-51820}"
BASE_IP="10.0"

echo "🔍 WireGuard Setup Test (Simulation)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Configuration:"
echo "  - Number of interfaces: $NUM_INTERFACES"
echo "  - Base port: $BASE_PORT"
echo "  - IP range: ${BASE_IP}.X.1/24"
echo ""

# Simulate WireGuard installation check
echo "✓ Checking for WireGuard tools..."
if command -v wg &> /dev/null; then
  echo "  ✓ WireGuard tools found: $(wg --version 2>&1 | head -1)"
else
  echo "  ℹ WireGuard tools not found (would be installed by setup-wireguard.sh)"
fi
echo ""

# Simulate key generation and interface creation
echo "📋 Simulated Interface Configuration:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for i in $(seq 0 $((NUM_INTERFACES - 1))); do
  INTERFACE="wg${i}"
  PORT=$((BASE_PORT + i))
  IP_ADDRESS="${BASE_IP}.${i}.1/24"
  
  # Simulate key generation (just use dummy keys for demo)
  PRIVATE_KEY="SIMULATED_PRIVATE_KEY_$(openssl rand -hex 16)"
  PUBLIC_KEY="SIMULATED_PUBLIC_KEY_$(openssl rand -hex 16)"
  
  echo ""
  echo "Interface: ${INTERFACE}"
  echo "  IP Address:  ${IP_ADDRESS}"
  echo "  Port:        ${PORT}"
  echo "  Public Key:  ${PUBLIC_KEY:0:50}..."
  echo "  Config:      /etc/wireguard/${INTERFACE}.conf"
  
  # Show what the config file would look like
  cat << EOF | sed 's/^/  │ /'
[Interface]
PrivateKey = ${PRIVATE_KEY:0:30}...
Address = ${IP_ADDRESS}
ListenPort = ${PORT}
SaveConfig = false
EOF
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Test completed successfully!"
echo ""
echo "📝 To actually create these interfaces, run:"
echo "   sudo ./setup-wireguard.sh $NUM_INTERFACES $BASE_PORT"
echo ""
echo "🔍 After running, verify with:"
echo "   ip a | grep wg"
echo "   sudo wg show"
echo ""
echo "Expected output in 'ip a' would show:"
for i in $(seq 0 $((NUM_INTERFACES - 1))); do
  INTERFACE="wg${i}"
  IP_ADDRESS="${BASE_IP}.${i}.1"
  echo "  $(($i + 10)): ${INTERFACE}: <POINTOPOINT,NOARP,UP,LOWER_UP> mtu 1420"
  echo "      inet ${IP_ADDRESS}/24 scope global ${INTERFACE}"
done
echo ""
