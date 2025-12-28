# Container Isolation and VPN Support

## Overview

This document explains how containers achieve proper isolation while supporting VPN/WireGuard functionality.

## The Problem with `--privileged`

Previously, containers were run with the `--privileged` flag, which caused critical issues:

### Security Issues
- **All capabilities granted**: Containers had unrestricted access to the host system
- **Security features disabled**: AppArmor, SELinux, and seccomp were bypassed
- **Full device access**: Containers could access all host devices
- **No isolation**: Containers could see and modify each other and the host

### Operational Issues
- **Container interference**: Only one container could show as "online" at a time
- **Network conflicts**: VPN/WireGuard interfaces from different containers interfered with each other
- **Unpredictable behavior**: Containers could affect each other's network configuration

## The Solution: Specific Capabilities + Network Isolation

### Linux Capabilities

Instead of using `--privileged`, we now use specific Linux capabilities:

| Capability | Purpose |
|------------|---------|
| `NET_ADMIN` | Create and manage network interfaces (TUN/TAP devices for VPN) |
| `NET_RAW` | Use raw and packet sockets (required for some VPN operations) |
| `SYS_MODULE` | Load kernel modules (e.g., WireGuard kernel module if needed) |

### Device Access

Containers need access to the TUN/TAP device for creating VPN tunnels:
```
--device=/dev/net/tun:/dev/net/tun
```

### Network Isolation

Each container runs in bridge network mode, ensuring:
- **Separate network namespace**: Each container has its own isolated network stack
- **Independent interfaces**: VPN interfaces in one container don't affect others
- **Proper isolation**: Containers cannot see or interfere with each other's network

```
--network=bridge
```

## Implementation

### Docker Run Command

```bash
docker run \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  --cap-add=SYS_MODULE \
  --device=/dev/net/tun:/dev/net/tun \
  --network=bridge \
  -e LICENSE_KEY='your-key' \
  datagram
```

### Python Docker SDK (webapp/app.py)

```python
container_kwargs = {
    'cap_add': ['NET_ADMIN', 'NET_RAW', 'SYS_MODULE'],
    'devices': ['/dev/net/tun:/dev/net/tun'],
    'network_mode': 'bridge',
    # ... other parameters
}
```

## Benefits

✅ **Security**: Only the minimum required capabilities are granted
✅ **Isolation**: Each container operates independently in its own network namespace
✅ **Stability**: Multiple containers can run simultaneously without conflicts
✅ **Predictability**: All containers show as "online" without interfering with each other
✅ **Best Practices**: Follows Docker security recommendations

## Verification

To verify that containers are running with proper isolation:

### Check Capabilities
```bash
# Get the container PID
docker inspect <container_name> | grep Pid

# Check capabilities (should show only NET_ADMIN, NET_RAW, SYS_MODULE)
grep Cap /proc/<pid>/status
```

### Check Network Namespace
```bash
# Each container should have a unique network namespace
docker exec <container1> ip netns identify $$
docker exec <container2> ip netns identify $$
# These should be different values
```

### Check TUN Device
```bash
# Verify the container can access /dev/net/tun
docker exec <container_name> ls -l /dev/net/tun
```

### Check Multiple Containers
```bash
# Start multiple containers
./datagram/start.sh key1 node
./datagram/start.sh key2 node

# All should show as online in the dashboard
# Or check manually:
docker ps --filter ancestor=datagram
```

## Troubleshooting

### "Operation not permitted" errors

If you see permission errors related to network operations:

1. Verify capabilities are set:
   ```bash
   docker inspect <container> | grep -A 10 CapAdd
   ```

2. Check that `/dev/net/tun` is accessible:
   ```bash
   docker exec <container> ls -l /dev/net/tun
   ```

### Containers still interfering

If containers still appear to interfere:

1. Verify each container has its own network namespace:
   ```bash
   docker inspect <container> | grep NetworkMode
   # Should show "bridge" not "host"
   ```

2. Restart Docker daemon (rare, but sometimes needed):
   ```bash
   sudo systemctl restart docker
   ```

### VPN not working

If VPN functionality is broken:

1. Check kernel module support:
   ```bash
   # On the host
   lsmod | grep wireguard
   
   # Try loading manually if not present
   sudo modprobe wireguard
   ```

2. Verify TUN/TAP support:
   ```bash
   # On the host
   ls -l /dev/net/tun
   # Should exist and be accessible
   ```

## Security Comparison

| Feature | `--privileged` | Capabilities + Isolation |
|---------|----------------|-------------------------|
| Container isolation | ❌ None | ✅ Full isolation |
| Network namespace | ❌ Shared | ✅ Per-container |
| Device access | ❌ All devices | ✅ Only /dev/net/tun |
| Capabilities | ❌ All capabilities | ✅ Only 3 needed ones |
| AppArmor/SELinux | ❌ Disabled | ✅ Enabled |
| Host impact | ❌ Can modify host | ✅ Isolated from host |
| Security | ❌ Very insecure | ✅ Secure |

## Additional Notes

### Why not `--privileged`?

The `--privileged` flag was originally used because:
1. It's the "easy" way to give containers permissions
2. Early testing showed VPN CLI needed elevated permissions
3. The specific capabilities needed weren't identified

However, this approach:
- Violates the principle of least privilege
- Creates security vulnerabilities
- Causes operational issues (container interference)
- Is not recommended for production use

### Why these specific capabilities?

- **NET_ADMIN**: Required to create TUN/TAP interfaces for VPN tunnels
- **NET_RAW**: Needed for raw socket operations used by VPN protocols
- **SYS_MODULE**: Allows loading WireGuard kernel module if not already loaded

These are the minimum capabilities required for VPN/WireGuard functionality.

### One-Time Privileged Use

The `download-binaries.sh` scripts still use `--privileged` for:
- **Temporary containers only**: Used once to extract binaries, then removed
- **Build-time operation**: Not part of runtime operations
- **Controlled environment**: Runs in a controlled build environment

This is acceptable because:
- It's not running user workloads
- The container is immediately destroyed
- It's only used during the build process

## References

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Linux Capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html)
- [Docker Network Drivers](https://docs.docker.com/network/drivers/)
- [TUN/TAP Interfaces](https://www.kernel.org/doc/Documentation/networking/tuntap.txt)
