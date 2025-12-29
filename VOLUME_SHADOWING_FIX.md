# The Volume Shadowing Problem and Solution

## Critical Issue: Empty Volumes

### What Was Wrong

When we mounted volumes over `/root/.datagram`, the volumes **shadowed** the binaries from the Docker image:

```dockerfile
# In Dockerfile
COPY binaries/.datagram /root/.datagram  # Binaries in image

# In docker run
--volume="$VOLUME:/root/.datagram"  # Volume shadows image contents!
```

**Result**: Volumes were EMPTY on first run, containers had no VPN/Conference CLI binaries.

### Why This Caused Container Conflicts

When containers started with empty `/root/.datagram`:
1. Container 1 starts → empty volume → tries to download/configure binaries
2. Container 2 starts → empty volume → tries to download/configure binaries
3. Conflicts occur during download, initialization, or runtime
4. Only the last container succeeds or stays "online"

### User's Critical Discovery

The user tested and found:
- ✅ **Two separate datagram panels on two VMs (same IP)** → Both containers work fine
- ❌ **Two containers in one panel (same host)** → First drops when second starts

This proved it's NOT an IP limitation but a **host-level container conflict**.

## The Solution: Template-Based Initialization

### Architecture

```
Docker Image:
├── /opt/.datagram-template/  ← Binaries stored here (template)
│   ├── vpn/
│   └── conference/
└── /root/.datagram/  ← Empty, will be volume mount point

Container Runtime:
├── Volume mounted: /root/.datagram  (empty on first run)
├── Entrypoint checks if empty
├── If empty: cp -r /opt/.datagram-template/* /root/.datagram/
└── Now container has initialized binaries in its own volume
```

### Implementation

**Dockerfile:**
```dockerfile
# Store binaries in template location (won't be shadowed)
COPY binaries/.datagram /opt/.datagram-template
```

**entrypoint.sh:**
```sh
# Initialize volume from template if empty
if [ ! -d "/root/.datagram/vpn" ] || [ ! -d "/root/.datagram/conference" ]; then
  echo "[*] Initializing .datagram directory from template..."
  cp -r /opt/.datagram-template/* /root/.datagram/
  cp -r /opt/.datagram-template/.[!.]* /root/.datagram/
  echo "[*] Template copied successfully"
fi
```

### How It Works

1. **Image Build**: Binaries copied to `/opt/.datagram-template`
2. **Container Start**: Volume mounted at `/root/.datagram` (empty)
3. **Entrypoint Runs**: Detects empty volume, copies from template
4. **Result**: Each container has its own initialized copy

### Benefits

✅ Each container gets complete, working binaries
✅ Volumes start initialized, not empty
✅ Configurations can diverge per-container
✅ No download conflicts
✅ No shared state between containers
✅ Proper isolation maintained

## Before vs After

### Before (Broken)

```
Image: /root/.datagram (binaries) ← SHADOWED BY VOLUME
       ↓
Container 1: Volume /root/.datagram (EMPTY) → Missing binaries → Conflicts
Container 2: Volume /root/.datagram (EMPTY) → Missing binaries → Conflicts
```

### After (Fixed)

```
Image: /opt/.datagram-template (binaries) ← Accessible
       ↓
Container 1: Volume /root/.datagram (EMPTY)
             → Entrypoint copies from template
             → Volume /root/.datagram (INITIALIZED) → Works!

Container 2: Volume /root/.datagram (EMPTY)
             → Entrypoint copies from template
             → Volume /root/.datagram (INITIALIZED) → Works!
```

## Testing

```bash
# Start first container
./datagram/start.sh f84e576e16b6c0fa5fb98db88e475ac2 test
# Logs should show: "[*] Initializing .datagram directory from template..."
#                   "[*] Template copied successfully"

# Start second container  
./datagram/start.sh 92bcf2ae4e326968f40f8670a3596b80 test
# Logs should show: "[*] Initializing .datagram directory from template..."
#                   "[*] Template copied successfully"

# Verify both are running
docker ps --filter ancestor=datagram
# Should show both containers

# Check volumes are initialized
docker exec f84e576e16b6c0fa5fb98db88e475ac2 ls -la /root/.datagram/
# Should show vpn/ and conference/ directories

docker exec 92bcf2ae4e326968f40f8670a3596b80 ls -la /root/.datagram/
# Should show vpn/ and conference/ directories
```

## Why This Fixes the Issue

1. **No empty volumes**: Each container starts with initialized binaries
2. **No download conflicts**: Binaries are already present
3. **Proper isolation**: Each volume is independent
4. **Configuration divergence**: Each container can modify its own config
5. **No shadowing**: Template location is never mounted over

## What Was Learned

- Mounting volumes over directories in Docker images **shadows** the image contents
- Empty volumes cause initialization conflicts
- Template-based initialization solves the shadowing problem
- User testing (two panels vs one panel) was key to identifying the host-level conflict

## Conclusion

The volume approach was correct, but implementation had a critical flaw. By using a template location and initializing volumes on first run, we now have:

✅ Proper per-container isolation
✅ No shared configuration
✅ No empty volume issues
✅ Both containers can run simultaneously
✅ Both should show as "online" on datagram.network
