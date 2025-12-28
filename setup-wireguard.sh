#!/bin/bash
# setup-wireguard.sh - Create WireGuard interfaces on the host
# This script creates wg0, wg1, wg2, etc. interfaces on the host system

set -e

# Configuration
NUM_INTERFACES="${1:-3}"  # Default to 3 interfaces if not specified
BASE_PORT="${2:-51820}"   # Base port for WireGuard (increments for each interface)
BASE_IP="10.0"            # Base IP prefix (will be 10.0.0.1/24, 10.0.1.1/24, etc.)

echo "🔧 Setting up WireGuard interfaces on the host..."
echo "   Number of interfaces: $NUM_INTERFACES"
echo "   Starting port: $BASE_PORT"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: This script must be run as root or with sudo"
  exit 1
fi

# Check if WireGuard is installed
if ! command -v wg &> /dev/null; then
  echo "⚠️  WireGuard tools not found. Installing..."
  
  # Detect OS and install WireGuard
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    case "$ID" in
      ubuntu|debian)
        apt-get update
        apt-get install -y wireguard wireguard-tools
        ;;
      centos|rhel|fedora)
        yum install -y wireguard-tools
        ;;
      alpine)
        apk add --no-cache wireguard-tools
        ;;
      *)
        echo "❌ Unsupported OS: $ID"
        echo "Please install WireGuard manually: https://www.wireguard.com/install/"
        exit 1
        ;;
    esac
  else
    echo "❌ Cannot detect OS. Please install WireGuard manually."
    exit 1
  fi
fi

# Load WireGuard kernel module
echo "📦 Loading WireGuard kernel module..."
modprobe wireguard || {
  echo "⚠️  Warning: Could not load wireguard module. This is normal on some systems."
  echo "   WireGuard may be built into the kernel or use userspace implementation."
}

# Create WireGuard configuration directory
WIREGUARD_DIR="/etc/wireguard"
mkdir -p "$WIREGUARD_DIR"
chmod 700 "$WIREGUARD_DIR"

# Create interfaces
for i in $(seq 0 $((NUM_INTERFACES - 1))); do
  INTERFACE="wg${i}"
  PORT=$((BASE_PORT + i))
  IP_OCTET="${i}"
  IP_ADDRESS="10.0.${IP_OCTET}.1/24"
  CONFIG_FILE="${WIREGUARD_DIR}/${INTERFACE}.conf"
  
  echo "🔨 Creating interface ${INTERFACE}..."
  
  # Generate private and public keys
  PRIVATE_KEY=$(wg genkey)
  PUBLIC_KEY=$(echo "$PRIVATE_KEY" | wg pubkey)
  
  # Create WireGuard configuration file
  cat > "$CONFIG_FILE" << EOF
[Interface]
# WireGuard interface ${INTERFACE}
# Created: $(date)
PrivateKey = ${PRIVATE_KEY}
Address = ${IP_ADDRESS}
ListenPort = ${PORT}
SaveConfig = false

# Example peer configuration (uncomment and configure as needed):
# [Peer]
# PublicKey = PEER_PUBLIC_KEY_HERE
# AllowedIPs = 10.0.${IP_OCTET}.2/32
# Endpoint = PEER_IP:PORT
EOF

  chmod 600 "$CONFIG_FILE"
  
  # Bring up the interface
  echo "   Bringing up ${INTERFACE}..."
  wg-quick up "$INTERFACE" 2>/dev/null || {
    echo "   ⚠️  Interface ${INTERFACE} may already be up, attempting to reload..."
    wg-quick down "$INTERFACE" 2>/dev/null || true
    wg-quick up "$INTERFACE"
  }
  
  # Show interface details
  echo "   ✅ ${INTERFACE} configured:"
  echo "      - IP Address: ${IP_ADDRESS}"
  echo "      - Listen Port: ${PORT}"
  echo "      - Public Key: ${PUBLIC_KEY}"
  echo ""
done

# Enable WireGuard interfaces on boot
echo "🔄 Enabling WireGuard interfaces on boot..."
for i in $(seq 0 $((NUM_INTERFACES - 1))); do
  INTERFACE="wg${i}"
  systemctl enable "wg-quick@${INTERFACE}" 2>/dev/null || {
    echo "   ⚠️  Could not enable ${INTERFACE} on boot (systemd may not be available)"
  }
done

echo ""
echo "✅ WireGuard setup complete!"
echo ""
echo "📊 Current network interfaces:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ip addr show | grep -E "^[0-9]+: wg[0-9]+" || echo "   (checking interfaces...)"
sleep 1
ip addr show | grep -E "^[0-9]+: wg[0-9]+" || echo "   No WireGuard interfaces found - they may not have started yet"

echo ""
echo "🔍 Verify interfaces with:"
echo "   ip a | grep wg"
echo "   wg show"
echo ""
echo "📝 Configuration files location: ${WIREGUARD_DIR}/"
echo ""
echo "🛠️  To manage interfaces:"
echo "   sudo wg-quick up wg0     # Start interface"
echo "   sudo wg-quick down wg0   # Stop interface"
echo "   sudo wg show wg0         # Show interface details"
echo ""
echo "⚠️  Note: Configuration files contain private keys - keep them secure!"
