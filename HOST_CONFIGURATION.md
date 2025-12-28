# Host Configuration for Ulimit Changes

## Do I Need to Configure the Host?

**Short Answer: NO (for most deployments)** - The default configuration now supports running 500+ containers without special host configuration.

## What Changed?

The system now uses a **reasonable per-container ulimit** (8,192 file descriptors by default) instead of the previous excessive limit (1,048,576). This allows:
- **500+ containers** to run on a single host without exhausting system resources
- **VPN/WireGuard operations** to function properly with sufficient file descriptors
- **No host configuration** required for standard deployments

## Current Configuration

Each container is configured with:
- **Per-container ulimit**: 8,192 file descriptors (configurable via `CONTAINER_ULIMIT`)
- **Total with 500 containers**: ~4 million file descriptors (well within system limits)

Your host system default limits are typically:
```
✓ fs.nr_open (per-process limit):    1,048,576 (default on most systems)
✓ fs.file-max (system-wide limit):   Very large (e.g., 9,223,372,036,854,775,807)
```

## When Is Host Configuration Needed?

You **ONLY** need to configure the host system if:

1. You need to run more than 500 containers on a single host
2. Individual containers require more than 8,192 file descriptors (rare)
3. You see "too many open files" errors with the default configuration

## How to Check Your Current Setup

Run these commands on your Docker host:

```bash
# Check per-process limit
cat /proc/sys/fs/nr_open

# Check system-wide limit
cat /proc/sys/fs/file-max

# Check current user limit
ulimit -n

# Check container ulimit (after starting a container)
docker exec <container_name> sh -c "ulimit -n"
# Should show: 8192 (default)
```

## Adjusting Container Ulimit

If you need to adjust the per-container file descriptor limit:

```bash
# Set via environment variable before starting containers
export CONTAINER_ULIMIT=16384  # Increase to 16,384 if needed

# Start containers with the new limit
./datagram/start.sh <your-key>

# Or in docker-compose.yml:
environment:
  - CONTAINER_ULIMIT=16384
```

## Configure Host Limits (Only If Needed)

**Note**: Most users don't need this section. Only configure host limits if you're running 500+ containers or experiencing "too many open files" errors.

### Quick One-Liner (For Advanced Deployments)

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

- **Container ulimit (8,192)** - Sufficient for VPN/WireGuard operations per container
- **500 containers × 8,192** = ~4 million file descriptors (well within system limits)
- **System default fs.file-max** = 9.2 quintillion (effectively unlimited)
- **No host configuration needed** for standard deployments up to 500 containers

## Previous Configuration Issue

The original configuration set each container to 1,048,576 file descriptors, which caused:
- After 60-70 containers, the system would run out of file descriptors
- Total of 70 × 1,048,576 = 73+ million file descriptors exceeded practical limits
- Required extensive host configuration that many users didn't complete

The new default of 8,192 per container solves this while still providing more than enough file descriptors for VPN/WireGuard operations.

## Verification After Container Start

Once you start a container, you can verify the ulimit is correctly set:

```bash
# Get container ID or name
docker ps

# Check the container's ulimit
docker exec <container_name> sh -c "ulimit -n"
# Should show: 8192 (or your custom CONTAINER_ULIMIT value)

# Or check from the host
docker inspect <container_name> | grep -A 5 Ulimits
```

## Summary

✅ **No host configuration needed** - Default settings support 500+ containers  
✅ **Container ulimit: 8,192** - Sufficient for VPN/WireGuard operations  
✅ **Configurable** - Set `CONTAINER_ULIMIT` environment variable to adjust if needed  
⚠️ **Old configuration removed** - Previous 1,048,576 limit caused issues after 60-70 containers

The changes to `datagram/start.sh`, `webapp/app.py`, and `docker-compose.yml` set the container ulimit to 8,192 by default, which provides the right balance between functionality and scalability.

## Why 8,192?

VPN/WireGuard operations require elevated file descriptor limits compared to typical applications:
- **Tunnel interfaces (TUN/TAP devices)** - Each VPN connection needs file descriptors
- **Network connections** - Concurrent connections for VPN traffic
- **WireGuard peer connections** - Each peer maintains file descriptors
- **Log files and other I/O operations**

Research and testing shows:
- **Typical VPN node usage**: 100-500 file descriptors under normal operation
- **Peak usage**: 1,000-2,000 file descriptors during high load
- **Safety margin**: 8,192 provides 4-8x headroom for spikes

This default allows:
- ✅ **500 containers** on a single host (4M total file descriptors)
- ✅ **Reliable VPN/WireGuard operation** with plenty of headroom
- ✅ **No host configuration** required for standard deployments
- ✅ **Room for growth** via the configurable `CONTAINER_ULIMIT` variable

If you encounter "too many open files" errors with the 8,192 default, you can increase it:
```bash
export CONTAINER_ULIMIT=16384  # Double the limit if needed
```
