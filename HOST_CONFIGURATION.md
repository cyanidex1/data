# Host Configuration for Ulimit Changes

## Do I Need to Configure the Host?

**Short Answer: YES** - For datagram VPN/WireGuard nodes to work properly, you need to configure your host system limits.

## Current Requirements

The containers require a ulimit of 1,048,576 file descriptors to properly run VPN/WireGuard operations. Your host system must support this:

```
✓ fs.nr_open (per-process limit):    1,048,576 or higher
✓ fs.file-max (system-wide limit):   Very large (e.g., 9,223,372,036,854,775,807)
```

## When Is Host Configuration Needed?

You **MUST** configure the host system if:

1. `fs.nr_open` is less than 1,048,576
2. You see "too many open files" errors when starting containers
3. Containers fail to bring up WireGuard devices

## How to Check Your Host Limits

Run these commands on your Docker host:

```bash
# Check per-process limit (must be >= container ulimit)
cat /proc/sys/fs/nr_open

# Check system-wide limit
cat /proc/sys/fs/file-max

# Check current user limit
ulimit -n
```

## Configure Host Limits (Required)

### Quick One-Liner (Recommended)

Run this command to configure all limits at once:

```bash
sudo bash -c 'echo "fs.nr_open = 1048576" > /etc/sysctl.d/99-docker-limits.conf && echo "fs.file-max = 9223372036854775807" >> /etc/sysctl.d/99-docker-limits.conf && sysctl -p /etc/sysctl.d/99-docker-limits.conf && grep -q "nofile.*1048576" /etc/security/limits.conf || echo -e "*    soft    nofile    1048576\n*    hard    nofile    1048576\nroot soft    nofile    1048576\nroot hard    nofile    1048576" >> /etc/security/limits.conf && systemctl restart docker'
```

This command will:
- Set `fs.nr_open` to 1,048,576 (per-process limit)
- Set `fs.file-max` to 9,223,372,036,854,775,807 (system-wide limit)
- Update user limits in `/etc/security/limits.conf` (only if not already configured)
- Restart Docker daemon to apply changes

**Note**: The command is safe to run multiple times as it checks if limits are already configured before appending to limits.conf.

### Manual Configuration Steps

Alternatively, you can configure each component manually:

### 1. Increase System Limits (requires root)

Edit `/etc/sysctl.conf` or create `/etc/sysctl.d/99-custom-limits.conf`:

```bash
# Maximum number of file descriptors per process
fs.nr_open = 1048576

# Maximum number of file descriptors system-wide  
fs.file-max = 9223372036854775807
```

Apply the changes:
```bash
sudo sysctl -p
```

### 2. Increase User Limits (requires root)

Edit `/etc/security/limits.conf`:

```
*    soft    nofile    1048576
*    hard    nofile    1048576
root soft    nofile    1048576
root hard    nofile    1048576
```

### 3. Restart Docker Daemon

```bash
sudo systemctl restart docker
```

## Why This Matters

- **Container ulimit (1,048,576)** ≤ **Host fs.nr_open (1,048,576)** ✓
- Docker containers inherit limits from the host
- If container ulimit > host limit, container will fail to start
- VPN/WireGuard operations require higher file descriptor limits than typical applications

## Verification After Container Start

Once you start a container with the new ulimit, you can verify it's working:

```bash
# Get container ID
docker ps

# Check the container's ulimit
docker exec <container_id> sh -c "ulimit -n"
# Should show: 1048576

# Or check from the host
docker inspect <container_id> | grep -A 5 Ulimits
```

## Summary

⚠️ **Host configuration IS needed** - Configure your system limits before starting containers  
✅ **Container ulimit: 1,048,576** - Required for VPN/WireGuard operations  
✅ **One-liner available** - Use the quick one-liner command above to configure everything at once

The changes to `datagram/start.sh` and `webapp/app.py` set the container ulimit to 1,048,576, which requires matching host system configuration.

## Why 1,048,576?

VPN/WireGuard operations require higher file descriptor limits:
- **Tunnel interfaces (TUN/TAP devices)** - Each VPN connection needs multiple file descriptors
- **Network connections** - Multiple concurrent connections for VPN traffic
- **WireGuard peer connections** - Each peer maintains file descriptors
- **Log files and other I/O operations**

The ulimit of 1,048,576 provides sufficient headroom for these operations while still allowing multiple containers to run on a single host.
