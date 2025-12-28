# WireGuard Interface Setup Guide

This guide explains how to set up WireGuard interfaces (wg0, wg1, wg2, etc.) on the host system.

## Overview

WireGuard interfaces can be created on the host system for:
- Direct VPN connections to remote peers
- Testing WireGuard functionality
- Creating VPN tunnels that containers can use
- Network isolation and routing

## Quick Setup

Run the setup script with default settings (creates 3 interfaces: wg0, wg1, wg2):

```bash
sudo ./setup-wireguard.sh
```

## Custom Setup

### Create a Different Number of Interfaces

```bash
# Create 5 interfaces (wg0 through wg4)
sudo ./setup-wireguard.sh 5

# Create 10 interfaces with custom base port
sudo ./setup-wireguard.sh 10 52000
```

### Syntax

```bash
sudo ./setup-wireguard.sh [NUM_INTERFACES] [BASE_PORT]
```

- **NUM_INTERFACES**: Number of WireGuard interfaces to create (default: 3)
- **BASE_PORT**: Starting port number, increments for each interface (default: 51820)

## What the Script Does

1. **Checks Prerequisites**
   - Verifies root/sudo access
   - Installs WireGuard tools if not present
   - Loads WireGuard kernel module

2. **Creates Interfaces**
   - Generates unique private/public key pairs for each interface
   - Creates configuration files in `/etc/wireguard/`
   - Assigns IP addresses (10.0.0.1/24, 10.0.1.1/24, 10.0.2.1/24, etc.)
   - Assigns ports (51820, 51821, 51822, etc.)

3. **Brings Up Interfaces**
   - Starts all created interfaces
   - Enables them to start on boot (if systemd is available)

## Configuration Files

Configuration files are stored in `/etc/wireguard/`:
- `/etc/wireguard/wg0.conf`
- `/etc/wireguard/wg1.conf`
- `/etc/wireguard/wg2.conf`
- etc.

Each file contains:
- Private key (keep secure!)
- IP address assignment
- Listen port
- Placeholder for peer configurations

## Managing Interfaces

### View All Interfaces

```bash
# Show all WireGuard interfaces
sudo wg show

# Show all network interfaces (including WireGuard)
ip a | grep wg
```

### Manage Individual Interfaces

```bash
# Start an interface
sudo wg-quick up wg0

# Stop an interface
sudo wg-quick down wg0

# Restart an interface
sudo wg-quick down wg0 && sudo wg-quick up wg0

# Show interface details
sudo wg show wg0
```

### Enable/Disable on Boot

```bash
# Enable interface to start on boot
sudo systemctl enable wg-quick@wg0

# Disable interface from starting on boot
sudo systemctl disable wg-quick@wg0

# Check status
sudo systemctl status wg-quick@wg0
```

## Adding Peers

To connect to other WireGuard peers, edit the configuration file and add a `[Peer]` section:

```bash
sudo nano /etc/wireguard/wg0.conf
```

Add peer configuration:

```ini
[Peer]
PublicKey = PEER_PUBLIC_KEY_HERE
AllowedIPs = 10.0.0.2/32
Endpoint = peer.example.com:51820
PersistentKeepalive = 25
```

Then restart the interface:

```bash
sudo wg-quick down wg0
sudo wg-quick up wg0
```

## IP Address Scheme

Each interface is assigned an IP in the 10.0.X.1/24 range:
- wg0: 10.0.0.1/24
- wg1: 10.0.1.1/24
- wg2: 10.0.2.1/24
- wg3: 10.0.3.1/24
- etc.

## Port Assignments

Ports start at 51820 (default WireGuard port) and increment:
- wg0: 51820
- wg1: 51821
- wg2: 51822
- wg3: 51823
- etc.

## Firewall Configuration

If you have a firewall enabled, allow WireGuard ports:

```bash
# For UFW (Ubuntu/Debian)
sudo ufw allow 51820:51830/udp

# For firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=51820-51830/udp
sudo firewall-cmd --reload

# For iptables
sudo iptables -A INPUT -p udp --dport 51820:51830 -j ACCEPT
```

## Troubleshooting

### WireGuard Not Installed

If WireGuard tools are not found, the script will attempt to install them. If installation fails:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install wireguard wireguard-tools
```

**CentOS/RHEL:**
```bash
sudo yum install wireguard-tools
```

**Alpine:**
```bash
sudo apk add wireguard-tools
```

### Kernel Module Not Loading

Some systems have WireGuard built into the kernel or use userspace implementation. This is normal and WireGuard should still work.

To verify:
```bash
# Check if module is loaded
lsmod | grep wireguard

# Try loading manually
sudo modprobe wireguard
```

### Interface Already Exists

If an interface already exists, the script will attempt to bring it down and recreate it. To manually clean up:

```bash
sudo wg-quick down wg0
sudo rm /etc/wireguard/wg0.conf
```

### Permission Denied

Ensure you're running the script with sudo:
```bash
sudo ./setup-wireguard.sh
```

### Port Already in Use

If ports are already in use, specify a different base port:
```bash
sudo ./setup-wireguard.sh 3 52000
```

## Security Considerations

1. **Private Keys**: Configuration files contain private keys and are set to mode 600 (owner read/write only)
2. **Root Access**: The `/etc/wireguard/` directory is accessible only by root
3. **Backup Keys**: Keep backups of your configuration files in a secure location
4. **Peer Authentication**: Always verify peer public keys before adding them
5. **Firewall**: Configure your firewall to allow only necessary WireGuard ports

## Integration with Docker Containers

### Using Host Network Mode

If you want containers to use host WireGuard interfaces, modify the container start command:

```bash
docker run --network=host ...
```

⚠️ **Warning**: This removes network isolation between containers and the host.

### Using Bridge Mode with Port Forwarding

To keep container isolation while allowing WireGuard access, use port forwarding:

```bash
docker run -p 51820:51820/udp ...
```

### Routing Container Traffic Through WireGuard

Configure iptables rules to route container traffic through WireGuard interfaces:

```bash
# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1

# NAT container traffic through wg0
sudo iptables -t nat -A POSTROUTING -o wg0 -j MASQUERADE
sudo iptables -A FORWARD -i docker0 -o wg0 -j ACCEPT
sudo iptables -A FORWARD -i wg0 -o docker0 -m state --state RELATED,ESTABLISHED -j ACCEPT
```

## Verification

After running the setup script, verify that interfaces are created:

```bash
# Check interfaces in network list
ip a | grep wg

# Expected output:
# 10: wg0: <POINTOPOINT,NOARP,UP,LOWER_UP> ...
# 11: wg1: <POINTOPOINT,NOARP,UP,LOWER_UP> ...
# 12: wg2: <POINTOPOINT,NOARP,UP,LOWER_UP> ...

# Show WireGuard status
sudo wg show

# Expected output shows interfaces with their public keys and ports
```

## Removing WireGuard Interfaces

To remove all WireGuard interfaces:

```bash
# Stop and disable interfaces
for i in 0 1 2; do
  sudo wg-quick down wg${i}
  sudo systemctl disable wg-quick@wg${i} 2>/dev/null
done

# Remove configuration files
sudo rm /etc/wireguard/wg*.conf
```

## Additional Resources

- [WireGuard Official Documentation](https://www.wireguard.com/)
- [WireGuard Quick Start](https://www.wireguard.com/quickstart/)
- [WireGuard Configuration Examples](https://wiki.archlinux.org/title/WireGuard)
- [Container Isolation Guide](CONTAINER_ISOLATION.md)

## Support

For issues specific to:
- **WireGuard installation**: Refer to [WireGuard's installation guide](https://www.wireguard.com/install/)
- **Container networking**: See [CONTAINER_ISOLATION.md](CONTAINER_ISOLATION.md)
- **Docker setup**: Check [README.md](README.md)
