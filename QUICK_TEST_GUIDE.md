# Quick Test Guide - Volume Fix

## Test the Fix with Your Keys

You provided these test keys:
- Key 1: `f84e576e16b6c0fa5fb98db88e475ac2`
- Key 2: `92bcf2ae4e326968f40f8670a3596b80`

### Step-by-Step Test

1. **Build the datagram image** (if not already built):
   ```bash
   cd /home/runner/work/data/data/datagram
   ./download-binaries.sh
   docker build --platform linux/amd64 -t datagram .
   ```

2. **Start first container with key 1**:
   ```bash
   ./start.sh f84e576e16b6c0fa5fb98db88e475ac2
   ```
   
   Expected output:
   ```
   [*] Using MAC address: 02:42:ac:11:7c:66
   [*] Creating volume: f84e576e16b6c0fa5fb98db88e475ac2-datagram-data
   [*] Launching container 'f84e576e16b6c0fa5fb98db88e475ac2' in background...
   ```

3. **Start second container with key 2**:
   ```bash
   ./start.sh 92bcf2ae4e326968f40f8670a3596b80
   ```
   
   Expected output:
   ```
   [*] Using MAC address: 02:42:ac:11:5b:12
   [*] Creating volume: 92bcf2ae4e326968f40f8670a3596b80-datagram-data
   [*] Launching container '92bcf2ae4e326968f40f8670a3596b80' in background...
   ```

4. **Verify both containers are running**:
   ```bash
   docker ps --filter ancestor=datagram
   ```
   
   Expected: Both containers listed with "Up" status

5. **Verify separate volumes were created**:
   ```bash
   docker volume ls | grep datagram-data
   ```
   
   Expected output:
   ```
   local   f84e576e16b6c0fa5fb98db88e475ac2-datagram-data
   local   92bcf2ae4e326968f40f8670a3596b80-datagram-data
   ```

6. **Check each container's .datagram directory**:
   ```bash
   docker exec f84e576e16b6c0fa5fb98db88e475ac2 ls -la /root/.datagram/
   docker exec 92bcf2ae4e326968f40f8670a3596b80 ls -la /root/.datagram/
   ```
   
   Expected: Each shows different content (or downloading on first run)

7. **Check container logs** (wait 30-60 seconds for VPN to connect):
   ```bash
   docker logs f84e576e16b6c0fa5fb98db88e475ac2 | tail -20
   docker logs 92bcf2ae4e326968f40f8670a3596b80 | tail -20
   ```
   
   Look for successful connection messages

8. **Check datagram.network dashboard**:
   - Log in to your datagram.network account
   - Navigate to nodes/devices section
   - **Expected**: Both containers show as "online" ✅
   - **Previous behavior**: Only the last one (key 2) would show online

## What Changed

### Before the Fix
```
Container 1 + Container 2 → Same .datagram directory → Conflict → Only last online
```

### After the Fix
```
Container 1 → Volume 1 → Own .datagram → ✅ Online
Container 2 → Volume 2 → Own .datagram → ✅ Online
```

## Troubleshooting

### If only one container shows online:

1. **Check logs for errors**:
   ```bash
   docker logs f84e576e16b6c0fa5fb98db88e475ac2
   docker logs 92bcf2ae4e326968f40f8670a3596b80
   ```

2. **Verify volumes are different**:
   ```bash
   docker inspect f84e576e16b6c0fa5fb98db88e475ac2 | grep -A 5 Mounts
   docker inspect 92bcf2ae4e326968f40f8670a3596b80 | grep -A 5 Mounts
   ```
   
   Should show different volume names

3. **Check VPN interfaces**:
   ```bash
   docker exec f84e576e16b6c0fa5fb98db88e475ac2 ip addr show
   docker exec 92bcf2ae4e326968f40f8670a3596b80 ip addr show
   ```
   
   Look for `tun0` or `wg0` interfaces

4. **Restart containers** if needed:
   ```bash
   docker restart f84e576e16b6c0fa5fb98db88e475ac2
   docker restart 92bcf2ae4e326968f40f8670a3596b80
   ```

### Clean up and retry:

```bash
# Stop and remove containers
docker stop f84e576e16b6c0fa5fb98db88e475ac2 92bcf2ae4e326968f40f8670a3596b80
docker rm f84e576e16b6c0fa5fb98db88e475ac2 92bcf2ae4e326968f40f8670a3596b80

# Remove volumes (forces fresh download)
docker volume rm f84e576e16b6c0fa5fb98db88e475ac2-datagram-data
docker volume rm 92bcf2ae4e326968f40f8670a3596b80-datagram-data

# Start fresh
./start.sh f84e576e16b6c0fa5fb98db88e475ac2
./start.sh 92bcf2ae4e326968f40f8670a3596b80
```

## Success Criteria

✅ Both containers running (`docker ps`)
✅ Separate volumes created (`docker volume ls`)
✅ Both containers have own .datagram content
✅ **Both show as online on datagram.network dashboard**

## Why This Should Work

The previous shared `.datagram` directory caused VPN/Conference CLI configuration conflicts. Now each container has its own configuration, so both can connect to datagram.network independently without interfering with each other.
