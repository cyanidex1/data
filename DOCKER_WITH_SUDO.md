# Running Datagram in Docker with Multiple WireGuard Interfaces

## Overview

The existing Docker setup **already supports** running `sudo datagram run` inside containers, with each container creating its own WireGuard interface (wg0, wg1, wg2, etc.) in isolated network namespaces.

## How It Works

When you run datagram in a Docker container:

1. Each container runs with **sudo-like privileges** via Linux capabilities (NET_ADMIN, NET_RAW, SYS_MODULE)
2. Each container has its own **network namespace** (isolated from other containers and host)
3. When datagram runs inside the container, it creates WireGuard interfaces (wg0, wg1, wg2, etc.)
4. These interfaces are **isolated** - they don't conflict with interfaces in other containers

### Example

```
Host System
├── Container: node1 (172.17.0.2)
│   └── Inside: wg0, wg1, wg2... (isolated to this container)
│
├── Container: node2 (172.17.0.3)
│   └── Inside: wg0, wg1, wg2... (isolated to this container)
│
└── Container: node3 (172.17.0.4)
    └── Inside: wg0, wg1, wg2... (isolated to this container)
```

Each container can create wg0, wg1, wg2, etc. without conflicts because they're in separate network namespaces!

## Quick Start

### Method 1: Using the Start Script (Recommended)

```bash
cd datagram

# Start first instance
./start.sh 92bcf2ae4e326968f40f8670a3596b80

# Start second instance with different key
./start.sh a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

# Start third instance
./start.sh b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7
```

### Method 2: Using the Web Interface

1. Build the datagram image (one-time):
   ```bash
   cd datagram && ./download-binaries.sh && cd ..
   docker build --platform linux/amd64 -t datagram datagram/
   ```

2. Start the control panel:
   ```bash
   docker compose up -d
   ```

3. Open http://localhost:5000 and add containers through the web interface

### Method 3: Direct Docker Command

```bash
# First container (node1)
docker run -d \
  --platform linux/amd64 \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  --cap-add=SYS_MODULE \
  --device=/dev/net/tun:/dev/net/tun \
  --network=bridge \
  --env LICENSE_KEY="92bcf2ae4e326968f40f8670a3596b80" \
  --name node1 \
  --restart unless-stopped \
  --ulimit nofile=8192:8192 \
  datagram

# Second container (node2)
docker run -d \
  --platform linux/amd64 \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  --cap-add=SYS_MODULE \
  --device=/dev/net/tun:/dev/net/tun \
  --network=bridge \
  --env LICENSE_KEY="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
  --name node2 \
  --restart unless-stopped \
  --ulimit nofile=8192:8192 \
  datagram
```

## Verify WireGuard Interfaces Inside Containers

Each container creates its own WireGuard interfaces:

```bash
# Check interfaces in first container
docker exec node1 ip addr show

# Example output:
# 1: lo: <LOOPBACK,UP,LOWER_UP> ...
# 2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
# 4: wg0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1420 ...

# Check interfaces in second container
docker exec node2 ip addr show

# Example output (also has wg0, but it's a different interface!):
# 1: lo: <LOOPBACK,UP,LOWER_UP> ...
# 2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
# 4: wg0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1420 ...
```

Both containers can have `wg0` because they're in **separate network namespaces** - they don't conflict!

## Verify Network Isolation

Confirm each container has its own network namespace:

```bash
# Get network namespace ID for each container
docker exec node1 readlink /proc/self/ns/net
# Output: net:[4026532236]

docker exec node2 readlink /proc/self/ns/net
# Output: net:[4026532302]

# Different IDs = different namespaces = full isolation ✅
```

## View Container Logs

```bash
# View logs for a specific container
docker logs node1

# Follow logs in real-time
docker logs -f node1

# View last 50 lines
docker logs --tail 50 node1
```

Expected output:
```
[*] Starting Datagram container...
[*] Running datagram with key: 92bcf2ae4e326968f40f8670a3596b80
App version: 1.2.3
Downloading datagram-vpn-cli...
Downloading datagram-conference-cli...
VPN version: 1.1.0
2025-12-28 15:53:28.068	[info]	Signal connected
Conference version: 1.1.4
Running...
```

## Managing Multiple Containers

### List all running containers

```bash
docker ps --filter ancestor=datagram
```

### Stop a container

```bash
docker stop node1
```

### Start a stopped container

```bash
docker start node1
```

### Restart a container

```bash
docker restart node1
```

### Remove a container

```bash
docker stop node1
docker rm node1
```

### View resource usage

```bash
docker stats node1 node2 node3
```

## Understanding the Capabilities

The containers run with these Linux capabilities (not full `--privileged`):

- **CAP_NET_ADMIN**: Create and manage network interfaces (required for WireGuard)
- **CAP_NET_RAW**: Use raw and packet sockets
- **CAP_SYS_MODULE**: Load kernel modules (for WireGuard kernel module if needed)

This provides the **minimum required privileges** for WireGuard to work, while maintaining security and isolation.

## Key Differences: Docker vs Native Installation

| Feature | Docker (This Guide) | Native (native-install/) |
|---------|---------------------|--------------------------|
| Isolation | ✅ Full isolation per container | ❌ All instances on host |
| Interface Names | All can use wg0 (isolated) | Must use wg0, wg1, wg2... |
| Management | Docker commands or Web UI | Systemd services |
| Security | Containerized | Direct host access |
| Resource Usage | Container overhead | Lower overhead |
| Setup Complexity | Simple (docker run) | Requires systemd setup |

## Why Docker is Recommended for This Use Case

1. **Better Isolation**: Each container is completely isolated from others
2. **No Name Conflicts**: All containers can create wg0 without conflicts
3. **Easier Management**: Use Docker commands or the web interface
4. **Safer**: Containers are sandboxed and can't affect the host system
5. **Portable**: Works the same on any Docker-capable system

## Troubleshooting

### Container won't start

```bash
# Check container logs
docker logs node1

# Check if datagram image exists
docker images | grep datagram

# Rebuild if needed
cd datagram
docker build --platform linux/amd64 -t datagram .
```

### Check if WireGuard is working inside container

```bash
# Enter the container
docker exec -it node1 sh

# Inside container, check interfaces
ip addr show

# Check if wg interfaces exist
ip link show | grep wg

# Exit container
exit
```

### View detailed container info

```bash
# Inspect container configuration
docker inspect node1

# Check capabilities
docker inspect node1 | grep -A 20 CapAdd
```

## Advanced: Bulk Operations

### Start multiple containers at once

```bash
# Create a simple script
for i in {1..5}; do
    KEY=$(openssl rand -hex 16)
    ./datagram/start.sh "$KEY"
    echo "Started container with key: $KEY"
    sleep 2
done
```

### Stop all datagram containers

```bash
docker stop $(docker ps -q --filter ancestor=datagram)
```

### Remove all datagram containers

```bash
docker stop $(docker ps -q --filter ancestor=datagram)
docker rm $(docker ps -aq --filter ancestor=datagram)
```

### View logs from all containers

```bash
docker ps --filter ancestor=datagram --format '{{.Names}}' | \
    xargs -I {} sh -c 'echo "=== {} ===" && docker logs --tail 10 {}'
```

## Additional Resources

- Main README: [../README.md](../README.md)
- Network Isolation Details: [../NETWORK_ISOLATION_EXPLAINED.md](../NETWORK_ISOLATION_EXPLAINED.md)
- Container Isolation: [../CONTAINER_ISOLATION.md](../CONTAINER_ISOLATION.md)
- Testing Guide: [../TESTING_GUIDE.md](../TESTING_GUIDE.md)
- Native Installation (alternative): [../native-install/NATIVE_INSTALL.md](../native-install/NATIVE_INSTALL.md)
