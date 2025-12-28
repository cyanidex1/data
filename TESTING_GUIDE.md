# Testing Guide for Container Isolation Fix

## Overview

This guide helps you verify that the container isolation fix works correctly and that multiple containers can run simultaneously without interference.

## What Was Fixed

**Problem**: Using `--privileged` flag caused only 1 container to show as online at a time.

**Solution**: Replaced `--privileged` with specific capabilities and network isolation.

## Quick Test

### 1. Start Multiple Containers

Using the web interface or command line, start at least 3 containers:

```bash
# Using the start.sh script
cd datagram
./start.sh key1 test
./start.sh key2 test
./start.sh key3 test
```

Or use the web interface to start 3+ containers with different keys.

### 2. Verify All Show as Online

Check the dashboard or run:

```bash
docker ps --filter ancestor=datagram
```

**Expected Result**: All 3+ containers should be running and showing as online.

**Previous Behavior**: Only 1 would show as online.

## Detailed Verification

### Check Container Configuration

Verify each container has the correct security settings:

```bash
# Pick a container name
CONTAINER_NAME="test1"  # or node1, etc.

# Check capabilities (should show only NET_ADMIN, NET_RAW, SYS_MODULE)
docker inspect $CONTAINER_NAME --format '{{.HostConfig.CapAdd}}'

# Check it's NOT privileged (should show false)
docker inspect $CONTAINER_NAME --format '{{.HostConfig.Privileged}}'

# Check network mode (should show "bridge" or "default")
docker inspect $CONTAINER_NAME --format '{{.HostConfig.NetworkMode}}'

# Check device access (should include /dev/net/tun)
docker inspect $CONTAINER_NAME --format '{{.HostConfig.Devices}}'
```

### Check Container Isolation

Verify containers have separate network namespaces:

```bash
# Get network namespace for each container
docker exec test1 readlink /proc/self/ns/net
docker exec test2 readlink /proc/self/ns/net
docker exec test3 readlink /proc/self/ns/net
```

**Expected**: Each should show a different namespace ID (e.g., `net:[4026532123]`, `net:[4026532456]`, etc.)

### Check VPN Functionality

Verify VPN is working in each container:

```bash
# Check container logs for VPN CLI activity
docker logs test1 | tail -20
docker logs test2 | tail -20
docker logs test3 | tail -20
```

**Expected**: Logs should show VPN CLI running without errors like "operation not permitted" or "cannot create tunnel".

### Check Network Interfaces

Verify each container can create its own VPN interface:

```bash
# Check interfaces in each container
docker exec test1 ip link show
docker exec test2 ip link show
docker exec test3 ip link show
```

**Expected**: Each container should have:
- `lo` (loopback)
- `eth0` (container network)
- VPN tunnel interface (if VPN is active)

No conflicts between containers.

## Common Test Scenarios

### Scenario 1: Start and Stop Containers

```bash
# Start 3 containers
./start.sh key1 test
./start.sh key2 test
./start.sh key3 test

# Verify all are running
docker ps | grep datagram

# Stop one container
docker stop test2

# Verify others are still online
docker ps | grep datagram

# Start it again
docker start test2

# Verify all are back online
docker ps | grep datagram
```

**Expected**: Starting/stopping one container should not affect others.

### Scenario 2: Restart Containers

```bash
# Restart each container while others are running
docker restart test1
docker restart test2
docker restart test3

# Verify all come back online
docker ps | grep datagram
```

**Expected**: All containers should successfully restart without affecting each other.

### Scenario 3: Scale Up

```bash
# Start many containers
for i in {1..10}; do
  ./start.sh "key$i" scale
  sleep 2
done

# Verify all are running
docker ps | grep datagram | wc -l
```

**Expected**: Should show 10 containers running.

## Troubleshooting

### If only 1 container shows as online:

1. **Check if changes were applied**:
   ```bash
   docker inspect <container> --format '{{.HostConfig.Privileged}}'
   ```
   Should show `false`. If `true`, the old configuration is still in use.

2. **Rebuild and restart**:
   ```bash
   docker stop $(docker ps -q --filter ancestor=datagram)
   docker rm $(docker ps -a -q --filter ancestor=datagram)
   docker rmi datagram
   cd datagram && ./build.sh
   ```

3. **Check Docker version**:
   ```bash
   docker version
   ```
   Ensure you're running Docker 20.10 or newer.

### If containers fail to start:

1. **Check TUN device exists**:
   ```bash
   ls -l /dev/net/tun
   ```
   Should exist and be accessible.

2. **Load WireGuard module** (if needed):
   ```bash
   sudo modprobe wireguard
   ```

3. **Check logs for errors**:
   ```bash
   docker logs <container_name>
   ```

### If VPN doesn't work:

1. **Verify capabilities**:
   ```bash
   docker inspect <container> --format '{{.HostConfig.CapAdd}}'
   ```
   Should show `[NET_ADMIN NET_RAW SYS_MODULE]`.

2. **Check device access**:
   ```bash
   docker exec <container> ls -l /dev/net/tun
   ```
   Should succeed.

3. **Check kernel support**:
   ```bash
   # On host
   lsmod | grep tun
   lsmod | grep wireguard
   ```

## Success Criteria

✅ Multiple containers (3+) run simultaneously
✅ All containers show as "online" on the dashboard
✅ Each container has its own network namespace
✅ VPN functionality works in all containers
✅ No "operation not permitted" errors
✅ Starting/stopping one container doesn't affect others
✅ Containers can be restarted without issues

## Performance Check

### Monitor Resource Usage

```bash
# Check system resources
docker stats

# Check if all containers are healthy
docker ps --format "table {{.Names}}\t{{.Status}}"
```

**Expected**: All containers should be "Up" with reasonable CPU/memory usage.

## Reporting Issues

If you encounter problems after applying the fix, gather this information:

```bash
# Container configuration
docker inspect <container_name> > container_inspect.json

# Container logs
docker logs <container_name> > container_logs.txt

# System info
docker version > docker_version.txt
uname -a > system_info.txt
lsmod | grep -E "tun|wireguard" > kernel_modules.txt

# Network info
docker network ls > networks.txt
docker exec <container_name> ip addr > container_network.txt
```

Share these files when reporting the issue.

## Next Steps

After successful testing:
1. Monitor containers in production for 24-48 hours
2. Verify all expected functionality works
3. Check that multiple containers remain online
4. Review logs for any unexpected errors

## Additional Resources

- [CONTAINER_ISOLATION.md](CONTAINER_ISOLATION.md) - Detailed explanation of the fix
- [HOST_CONFIGURATION.md](HOST_CONFIGURATION.md) - Host configuration guide
- [README.md](README.md) - General usage documentation
