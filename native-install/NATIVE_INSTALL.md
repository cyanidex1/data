# Native Installation Guide for Datagram

This guide explains how to install and run Datagram natively on your host system (not in Docker containers) with sudo privileges. Each instance will create its own WireGuard network interface (wg0, wg1, wg2, wg3, etc.).

## Overview

The native installation allows you to run multiple Datagram instances directly on your host machine using systemd services. Each instance:
- Runs with the necessary capabilities (NET_ADMIN, NET_RAW, SYS_MODULE)
- Creates its own WireGuard interface
- Starts automatically on boot
- Can be managed using a simple command-line interface

## Prerequisites

- Linux system with systemd (Ubuntu 20.04+, Debian 11+, CentOS 8+, etc.)
- Root/sudo access
- curl installed
- WireGuard kernel module (usually pre-installed on modern kernels)

## Quick Start

### 1. Initialize the Installation

```bash
cd native-install
sudo ./datagram-manager.sh init
```

This will:
- Download the datagram binary to `/usr/local/bin/datagram`
- Install the systemd service template to `/etc/systemd/system/`
- Create configuration directories (`/etc/datagram/instances/`, `/var/lib/datagram/`)

### 2. Add and Start Instances

**⚠️ Important**: Replace the example keys below with your actual Datagram license keys!

**Quick method (auto-increment names):**
```bash
# Add instance with auto-increment name (node0, node1, node2, etc.)
# Replace with your actual license key
sudo ./datagram-manager.sh quick-add YOUR_LICENSE_KEY_HERE

# Add more instances with different keys
sudo ./datagram-manager.sh quick-add YOUR_SECOND_KEY_HERE
sudo ./datagram-manager.sh quick-add YOUR_THIRD_KEY_HERE

# Use custom prefix
sudo ./datagram-manager.sh quick-add YOUR_KEY_HERE vpn
```

**Manual method (custom names):**
```bash
# Add an instance (replace with your actual license key)
sudo ./datagram-manager.sh add node0 YOUR_LICENSE_KEY_HERE

# Start the instance
sudo ./datagram-manager.sh start node0
```

### 3. Manage Instances

```bash
# List all instances
sudo ./datagram-manager.sh list

# Check instance status
sudo ./datagram-manager.sh status node0

# View logs
sudo ./datagram-manager.sh logs node0

# Restart an instance
sudo ./datagram-manager.sh restart node0

# Stop an instance
sudo ./datagram-manager.sh stop node0

# Remove an instance
sudo ./datagram-manager.sh remove node0
```

## Network Interface Verification

Each running instance creates its own WireGuard interface. You can verify this:

```bash
# Check network interfaces
ip addr show

# Look for wg interfaces
ip addr show | grep wg

# Example output:
# 4: wg0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1420 ...
# 5: wg1: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1420 ...
# 6: wg2: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1420 ...
```

Each instance will have its own interface:
- First instance: wg0
- Second instance: wg1
- Third instance: wg2
- And so on...

## Systemd Service Details

The instances are managed by systemd using a template service (`datagram@.service`). Each instance:

- **Service name**: `datagram@<instance-name>.service`
- **Configuration**: `/etc/datagram/instances/<instance-name>.conf`
- **Data directory**: `/var/lib/datagram/`
- **Logs**: `journalctl -u datagram@<instance-name>.service`

### Service Features

- **Auto-restart**: Service automatically restarts if it crashes
- **Boot persistence**: Instances started via the manager are enabled on boot
- **Security**: Runs with minimal required capabilities (NET_ADMIN, NET_RAW, SYS_MODULE)
- **Resource limits**: 8,192 file descriptors per instance (sufficient for WireGuard)

## Advanced Usage

### Direct systemd Management

You can also manage instances directly with systemctl:

```bash
# Start
sudo systemctl start datagram@node0.service

# Stop
sudo systemctl stop datagram@node0.service

# Restart
sudo systemctl restart datagram@node0.service

# Status
sudo systemctl status datagram@node0.service

# Enable on boot
sudo systemctl enable datagram@node0.service

# Disable on boot
sudo systemctl disable datagram@node0.service

# View logs
sudo journalctl -u datagram@node0.service -f
```

### Manual Configuration

Instance configurations are stored in `/etc/datagram/instances/`:

```bash
# View instance configuration
sudo cat /etc/datagram/instances/node0.conf

# Edit instance configuration
sudo nano /etc/datagram/instances/node0.conf

# After editing, restart the instance
sudo systemctl restart datagram@node0.service
```

Example configuration file:
```ini
LICENSE_KEY=92bcf2ae4e326968f40f8670a3596b80
```

### Managing Multiple Instances

Create multiple instances with different keys:

```bash
# Add three instances
sudo ./datagram-manager.sh quick-add 92bcf2ae4e326968f40f8670a3596b80
sudo ./datagram-manager.sh quick-add a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
sudo ./datagram-manager.sh quick-add b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7

# List all instances
sudo ./datagram-manager.sh list

# Output example:
# INSTANCE             STATUS     BOOT           
# --------             ------     ----           
# node0                running    enabled        
# node1                running    enabled        
# node2                running    enabled        
```

## Troubleshooting

### Instance won't start

```bash
# Check logs
sudo ./datagram-manager.sh logs node0 100

# Check systemd status
sudo systemctl status datagram@node0.service

# Check if datagram binary exists
ls -l /usr/local/bin/datagram

# Re-run initialization if needed
sudo ./datagram-manager.sh init
```

### WireGuard module not loaded

```bash
# Check if WireGuard module is loaded
lsmod | grep wireguard

# Load WireGuard module manually
sudo modprobe wireguard

# Make it load on boot
echo "wireguard" | sudo tee /etc/modules-load.d/wireguard.conf
```

### Permission denied errors

Ensure you're running all commands with sudo:
```bash
sudo ./datagram-manager.sh <command>
```

### Too many open files

If you see this error, increase the file descriptor limit:

```bash
# Edit the systemd service template
sudo nano /etc/systemd/system/datagram@.service

# Change this line:
# LimitNOFILE=8192
# To:
# LimitNOFILE=16384

# Reload systemd and restart instances
sudo systemctl daemon-reload
sudo ./datagram-manager.sh restart node0
```

### Check network interfaces

```bash
# Show all network interfaces
ip addr show

# Show only wg interfaces
ip link show | grep wg

# Check WireGuard status (if wg tool is installed)
sudo wg show
```

## Comparison: Native vs Docker

### Native Installation (this guide)
✅ Direct host access - no container overhead  
✅ Simpler networking - interfaces directly on host  
✅ Systemd integration - standard Linux service management  
✅ Lower resource usage - no container runtime  
❌ Less isolation - instances share host system  
❌ Manual installation - requires systemd setup  

### Docker Installation (main README)
✅ Full isolation - each instance in separate container  
✅ Easy deployment - single docker command  
✅ Cross-platform - works on any Docker host  
✅ Web UI available - manage via browser  
❌ Container overhead - requires Docker runtime  
❌ More complex networking - bridge networks and capabilities  

## Uninstallation

To completely remove the native installation:

```bash
# Stop and remove all instances
for instance in $(ls /etc/datagram/instances/*.conf 2>/dev/null | xargs -n1 basename -s .conf); do
    sudo ./datagram-manager.sh stop "$instance" 2>/dev/null || true
    sudo ./datagram-manager.sh remove "$instance" 2>/dev/null || true
done

# Remove systemd service template
sudo rm -f /etc/systemd/system/datagram@.service
sudo systemctl daemon-reload

# Remove datagram binary
sudo rm -f /usr/local/bin/datagram

# Remove configuration and data directories
sudo rm -rf /etc/datagram
sudo rm -rf /var/lib/datagram
```

## Security Considerations

### Capabilities

The service runs with these capabilities:
- **CAP_NET_ADMIN**: Create and manage network interfaces (required for WireGuard)
- **CAP_NET_RAW**: Use raw and packet sockets
- **CAP_SYS_MODULE**: Load kernel modules (for WireGuard if needed)

These are the minimum capabilities required for VPN/WireGuard functionality.

### File Permissions

- Configuration files (`/etc/datagram/instances/*.conf`): Mode 600 (root only)
- Configuration directory (`/etc/datagram/instances/`): Mode 700 (root only)
- Data directory (`/var/lib/datagram/`): Mode 755

### Network Isolation

Unlike Docker containers, native instances **share the host network namespace**. This means:
- All instances can see the same network interfaces
- IP conflicts are possible if not configured properly
- Use caution when running multiple instances

## Getting Help

For issues or questions:
1. Check the logs: `sudo ./datagram-manager.sh logs <instance-name>`
2. Check systemd status: `sudo systemctl status datagram@<instance-name>.service`
3. Review the main repository documentation
4. Check the TESTING_GUIDE.md for verification steps

## Additional Resources

- Main README: `../README.md`
- Docker Installation: See main README
- Host Configuration: `../HOST_CONFIGURATION.md`
- Testing Guide: `../TESTING_GUIDE.md`
- Container Isolation: `../CONTAINER_ISOLATION.md`
