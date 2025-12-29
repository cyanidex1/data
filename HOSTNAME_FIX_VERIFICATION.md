# Hostname Fix Verification Guide

## Overview

This guide helps you verify that the hostname fix resolves the issue where only the last started container shows as "online" on the datagram.network dashboard.

## What Was Fixed

### Problem
When multiple datagram containers were started on the same host:
- All containers would run successfully in the local control panel
- Only the last started container would show as "online" on datagram.network's website dashboard
- Other containers appeared offline or "shows up as nothing"

### Root Cause
Containers were using Docker's auto-generated hostnames (random hex strings), which didn't provide consistent unique identifiers for the datagram.network service to distinguish between multiple containers running on the same host with the same public IP.

### Solution
Set explicit `--hostname` parameter for each container, matching the container name. This ensures:
- Each container has a predictable, unique hostname
- The datagram.network service can distinguish between containers from the same host
- All containers report their status correctly to datagram.network

## Files Changed

1. **datagram/start.sh** - Added `--hostname="$CONTAINER_NAME"` parameter
2. **webapp/app.py** - Added `'hostname': current_container_name` to container creation
3. **TESTING_GUIDE.md** - Added hostname verification steps
4. **CONTAINER_ISOLATION.md** - Updated documentation with hostname parameter

## Testing Instructions

### Prerequisites

1. Download the datagram binaries:
   ```bash
   cd datagram
   ./download-binaries.sh
   ```

2. Build the datagram image:
   ```bash
   docker build --platform linux/amd64 -t datagram .
   ```

### Test Scenario: Start Multiple Containers

#### Option 1: Using the Shell Script

```bash
cd datagram

# Start first container
./start.sh <your-first-key> test

# Start second container
./start.sh <your-second-key> test

# Start third container (optional)
./start.sh <your-third-key> test
```

#### Option 2: Using the Web Interface

1. Open http://localhost:5000
2. Start a container with your first key
3. Start another container with your second key
4. Start a third container (optional)

### Verification Steps

#### 1. Verify Containers Are Running

```bash
# Check all datagram containers are running
docker ps --filter ancestor=datagram

# You should see all containers in "Up" status
```

#### 2. Verify Unique Hostnames and MAC Addresses

```bash
# Check hostname for each container
docker exec test1 hostname
# Expected output: test1

docker exec test2 hostname
# Expected output: test2

docker exec test3 hostname
# Expected output: test3

# Check MAC address for each container
docker exec test1 cat /sys/class/net/eth0/address
# Expected output: 02:42:ac:11:XX:XX (unique per container)

docker exec test2 cat /sys/class/net/eth0/address
# Expected output: 02:42:ac:11:YY:YY (different from test1)

docker exec test3 cat /sys/class/net/eth0/address
# Expected output: 02:42:ac:11:ZZ:ZZ (different from test1 and test2)
```

Each container should report:
- Its container name as the hostname
- A unique MAC address derived from its name

#### 3. Verify on datagram.network Dashboard

This is the critical test:

1. Log in to your datagram.network account dashboard
2. Navigate to the nodes/devices section
3. **Expected Result**: All containers should show as "online"
4. **Previous Behavior**: Only the last started container (test3) would show as online

### Additional Verification

#### Check Docker Configuration

Verify the hostname and MAC address are properly set in Docker:

```bash
# Inspect container configuration
docker inspect test1 --format '{{.Config.Hostname}}'
# Expected output: test1

docker inspect test1 --format '{{.NetworkSettings.MacAddress}}'
# Expected output: 02:42:ac:11:XX:XX (unique MAC)

docker inspect test2 --format '{{.Config.Hostname}}'
# Expected output: test2

docker inspect test2 --format '{{.NetworkSettings.MacAddress}}'
# Expected output: 02:42:ac:11:YY:YY (different from test1)
```

#### Check Container Logs

Monitor the logs to ensure containers are running without issues:

```bash
# Check logs for each container
docker logs test1 | tail -20
docker logs test2 | tail -20
docker logs test3 | tail -20
```

Look for successful connection messages and no authentication errors.

## Expected Results

### Before the Fix
- ❌ Container 1 starts and shows online
- ❌ Container 2 starts, only Container 2 shows online (Container 1 disappears)
- ❌ Container 3 starts, only Container 3 shows online (Containers 1 & 2 disappear)

### After the Fix
- ✅ Container 1 starts and shows online
- ✅ Container 2 starts, both Container 1 and 2 show online
- ✅ Container 3 starts, all Containers 1, 2, and 3 show online

## Troubleshooting

### Containers Still Not Showing Online

If containers are not showing as online on datagram.network:

1. **Wait for initial connection**: Give each container 30-60 seconds to establish connection after starting

2. **Verify keys are valid**: Ensure you're using valid, active license keys

3. **Check container logs for errors**:
   ```bash
   docker logs test1
   docker logs test2
   ```

4. **Verify network connectivity**:
   ```bash
   docker exec test1 ping -c 3 8.8.8.8
   ```

5. **Restart containers**:
   ```bash
   docker restart test1 test2 test3
   ```

### Only One Container Still Shows Online

If the issue persists after the fix:

1. **Verify the fix is applied**:
   ```bash
   # Check if hostname is set correctly
   docker inspect test1 --format '{{.Config.Hostname}}'
   ```
   
   If it shows a random hex string instead of "test1", the fix wasn't applied.

2. **Rebuild containers**:
   ```bash
   # Stop and remove old containers
   docker stop test1 test2 test3
   docker rm test1 test2 test3
   
   # Start new containers with the fix
   cd datagram
   ./start.sh <key1> test
   ./start.sh <key2> test
   ./start.sh <key3> test
   ```

### Verify You're Using Updated Code

```bash
# Check if the hostname parameter is in the script
cd datagram
grep "hostname" start.sh
# Should show: --hostname="$CONTAINER_NAME" \

# Check Python code
cd ../webapp
grep "hostname" app.py
# Should show: 'hostname': current_container_name,
```

## Additional Notes

### Hostname Naming Convention

- Hostnames match container names for consistency
- Valid hostname characters: letters, numbers, hyphens
- Container names like "test1", "node1", "92bcf2ae..." all create valid hostnames

### Compatibility

This fix is compatible with:
- All datagram node types (datagram, element, elevate, grow, revo, rlink, switch, win)
- Both shell script and web interface container creation
- Existing containers (though they won't have the fix until recreated)

### Network Isolation

This fix complements the existing network isolation:
- Each container still has its own network namespace
- Containers remain isolated from each other
- The hostname fix only affects how datagram.network identifies the containers

## Success Criteria

The fix is successful when:
1. ✅ Multiple containers can run simultaneously on the same host
2. ✅ Each container has a unique hostname matching its container name
3. ✅ All containers show as "online" on datagram.network dashboard
4. ✅ Containers continue to operate independently without interference
5. ✅ No additional configuration is required by users

## Support

If you encounter issues after applying this fix:
1. Check the troubleshooting section above
2. Verify all verification steps pass
3. Review container logs for error messages
4. Open an issue with:
   - Output of verification steps
   - Container logs
   - Screenshots of datagram.network dashboard
