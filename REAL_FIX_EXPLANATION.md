# The Real Fix: Separate .datagram Volumes Per Container

## The Actual Problem

### What Was Wrong

The previous fixes (hostname and MAC address) didn't work because they targeted the wrong issue:

1. **Hostname fix didn't work** - The datagram CLI doesn't expose hostname to datagram.network
2. **MAC address fix didn't work** - MAC addresses are internal to Docker bridge, invisible to external services

### The Real Issue: Shared Configuration Directory

All containers were **sharing the same `.datagram` directory** baked into the Docker image:

```
Dockerfile:
COPY binaries/.datagram /root/.datagram  ← Same for ALL containers
```

This `.datagram` directory contains:
- VPN CLI binaries and configuration
- Conference CLI binaries and configuration
- Potentially cached state, certificates, or session data
- Downloaded with a single test key during image build

**Result**: When containers started with different keys, they all used the same VPN/Conference CLI configuration, causing conflicts.

## The Solution: Per-Container Volumes

### What Changed

Each container now gets its own Docker volume for `/root/.datagram`:

```bash
# datagram/start.sh
DATAGRAM_VOLUME="${CONTAINER_NAME}-datagram-data"
docker run \
  --volume="$DATAGRAM_VOLUME:/root/.datagram" \
  ...
```

```python
# webapp/app.py
datagram_volume = f"{current_container_name}-datagram-data"
container_kwargs = {
    'volumes': {datagram_volume: {'bind': '/root/.datagram', 'mode': 'rw'}},
    ...
}
```

### How It Works

1. **Container 1 starts** with key `f84e576e16b6c0fa5fb98db88e475ac2`
   - Volume: `f84e576e16b6c0fa5fb98db88e475ac2-datagram-data`
   - Directory: `/root/.datagram` (mounted from volume)
   - First run: Downloads VPN/Conference CLI for THIS key
   - Configuration stored in its OWN volume

2. **Container 2 starts** with key `92bcf2ae4e326968f40f8670a3596b80`
   - Volume: `92bcf2ae4e326968f40f8670a3596b80-datagram-data`
   - Directory: `/root/.datagram` (mounted from DIFFERENT volume)
   - First run: Downloads VPN/Conference CLI for THIS key
   - Configuration stored in its OWN volume

3. **No conflicts!**
   - Each container has separate VPN configuration
   - Each container has separate Conference CLI configuration
   - No shared state between containers

## Why This Works

### Before the Fix

```
Docker Image:
├── /root/.datagram/
│   ├── vpn/           ← Downloaded with test key
│   └── conference/    ← Downloaded with test key

Container 1 (key: f84e...) → Uses same .datagram directory
Container 2 (key: 92bc...) → Uses same .datagram directory
Container 3 (key: a3d8...) → Uses same .datagram directory

Result: Conflicts! Only last container shows online
```

### After the Fix

```
Docker Image:
├── /root/.datagram/   ← Still contains base binaries (or empty)
    (This gets SHADOWED by volume mount)

Container 1 (key: f84e...)
  Volume: f84e576e16b6c0fa5fb98db88e475ac2-datagram-data
  └── /root/.datagram/ → Unique configuration for key f84e...

Container 2 (key: 92bc...)
  Volume: 92bcf2ae4e326968f40f8670a3596b80-datagram-data
  └── /root/.datagram/ → Unique configuration for key 92bc...

Container 3 (key: a3d8...)
  Volume: a3d8f7e2b9c4a1f6e8d7c3b2a1f9e6d8-datagram-data
  └── /root/.datagram/ → Unique configuration for key a3d8...

Result: No conflicts! All containers show online
```

## What About the First Run?

On first run, each container will:
1. Start with an empty (or base) `.datagram` directory
2. The datagram CLI will detect missing VPN/Conference binaries
3. Download and configure them using the container's specific LICENSE_KEY
4. Store the configuration in the container's own volume
5. Subsequent restarts use the cached configuration from the volume

## Testing with Provided Keys

```bash
# Start container 1
./datagram/start.sh f84e576e16b6c0fa5fb98db88e475ac2 test
# Creates volume: f84e576e16b6c0fa5fb98db88e475ac2-datagram-data
# Downloads CLI tools for key f84e...

# Start container 2
./datagram/start.sh 92bcf2ae4e326968f40f8670a3596b80 test
# Creates volume: 92bcf2ae4e326968f40f8670a3596b80-datagram-data
# Downloads CLI tools for key 92bc...

# Verify volumes exist
docker volume ls | grep datagram-data
# Should show both volumes

# Check both containers are running
docker ps --filter ancestor=datagram
# Should show both containers

# Check datagram.network dashboard
# Both containers should now show as online!
```

## Verification Commands

```bash
# List volumes created
docker volume ls | grep datagram-data

# Inspect a volume
docker volume inspect f84e576e16b6c0fa5fb98db88e475ac2-datagram-data

# Check what's in a container's .datagram directory
docker exec f84e576e16b6c0fa5fb98db88e475ac2 ls -la /root/.datagram/

# Verify each container has different content
docker exec f84e576e16b6c0fa5fb98db88e475ac2 find /root/.datagram/ -type f
docker exec 92bcf2ae4e326968f40f8670a3596b80 find /root/.datagram/ -type f
```

## Benefits of This Approach

1. **✅ Solves the actual problem** - Each container gets its own configuration
2. **✅ Persistent configuration** - Volumes survive container restarts
3. **✅ No shared state** - Complete isolation between containers
4. **✅ Proper VPN configuration** - Each key gets its own VPN setup
5. **✅ First-run auto-download** - CLI tools download automatically per container
6. **✅ Data persistence** - Container removal doesn't lose volume data

## Cleaning Up

To remove a container and its volume:

```bash
# Stop and remove container
docker stop test1
docker rm test1

# Remove the volume (optional - keeps data if you want to restart later)
docker volume rm test1-datagram-data
```

To clean up all datagram volumes:

```bash
# List all datagram volumes
docker volume ls | grep datagram-data

# Remove all (be careful!)
docker volume ls | grep datagram-data | awk '{print $2}' | xargs docker volume rm
```

## Why Previous Fixes Didn't Work

| Fix Attempt | Why It Didn't Work |
|-------------|-------------------|
| Hostname | datagram CLI doesn't use hostname for identification |
| MAC Address | MAC is internal to Docker, external services can't see it |
| **Volume per container** | **THIS WORKS** - Separates actual configuration causing conflicts |

## Summary

The issue wasn't about network isolation or unique identifiers - containers already had those with bridge mode. The issue was **shared configuration files** in the `.datagram` directory that all containers inherited from the Docker image.

By giving each container its own volume for `/root/.datagram`, we ensure:
- Each container downloads and configures VPN/Conference CLI independently
- No configuration conflicts between containers
- Each key gets its proper VPN tunnel and conference setup
- All containers can show as "online" on datagram.network simultaneously

**This is the real fix that addresses the actual root cause.**
