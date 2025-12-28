# WireGuard and Network Mode Configuration

## Important: Network Mode Requirements for WireGuard

### Summary

**For WireGuard (wg0) interfaces to work properly, containers MUST use `--network=host` mode.**

However, this creates a critical trade-off:
- ✅ **PRO**: WireGuard interface (wg0) is created and functions properly
- ❌ **CON**: All containers share the host's network namespace - NO isolation
- ❌ **CON**: Only ONE container can create a wg0 interface at a time
- ❌ **CON**: Running 500 containers with host network will cause conflicts

### The Problem

The original problem statement shows that with `--network=bridge` mode, the wg0 interface is NOT created:

```bash
$ docker exec <container> ip link show
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
2: eth0@if63: <BROADCAST,MULTICAST,UP,LOWER_UP,M-DOWN> mtu 1500 qdisc noqueue state UP 
    link/ether 0e:6a:16:04:d1:46 brd ff:ff:ff:ff:ff:ff
# No wg0 interface! ❌
```

### Why Bridge Mode Doesn't Show wg0

When using `--network=bridge`:
- Each container gets its own network namespace
- The Datagram VPN CLI tries to create a WireGuard interface
- The interface may be created but with limited functionality
- The WireGuard interface needs direct host network access to function properly

### Why Host Mode is Required

When using `--network=host`:
- Container shares the host's network namespace
- Full access to host networking stack
- WireGuard can create and manage wg0 interface
- VPN traffic routes properly through the host

### The Trade-Off: Isolation vs. Functionality

#### Option 1: Bridge Mode (Current Configuration)
```bash
docker run \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  --cap-add=SYS_MODULE \
  --device=/dev/net/tun:/dev/net/tun \
  --network=bridge \
  ...
```

**Pros:**
- ✅ Full container isolation
- ✅ Can run 500+ containers simultaneously
- ✅ Each container has its own network namespace
- ✅ Secure and follows best practices

**Cons:**
- ❌ WireGuard wg0 interface may not be created
- ❌ VPN functionality may be limited

#### Option 2: Host Mode (Required for WireGuard)
```bash
docker run \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  --cap-add=SYS_MODULE \
  --device=/dev/net/tun:/dev/net/tun \
  --network=host \
  ...
```

**Pros:**
- ✅ WireGuard wg0 interface is created
- ✅ Full VPN functionality
- ✅ Proper network routing

**Cons:**
- ❌ NO container isolation
- ❌ All containers share the same network namespace
- ❌ Only ONE container can create wg0 interface
- ❌ Running 500 containers will cause conflicts
- ❌ Containers can interfere with each other
- ❌ Less secure

### Answer to "Can 500 containers with host network mode each create their own interface?"

**NO.** When using `--network=host`:
- All 500 containers share the SAME host network namespace
- Only the FIRST container can successfully create a wg0 interface
- Subsequent containers will either:
  - Fail to create the interface (already exists)
  - Overwrite/conflict with the existing interface
  - Cause network instability

This is exactly the problem that the current bridge mode configuration was designed to solve.

### Recommendation

**Choose based on your needs:**

1. **If you need to run 500+ containers**: Use bridge mode (current configuration)
   - Accept that wg0 interface may not be visible
   - VPN functionality may still work using userspace implementation

2. **If you need WireGuard wg0 interface**: Use host mode
   - Accept that you can only run a small number of containers
   - Maximum ~10-20 containers before conflicts arise
   - Not suitable for 500+ container deployments

3. **Hybrid approach** (recommended for large deployments):
   - Use bridge mode for most containers (isolation)
   - Use host mode for a few dedicated VPN gateway containers
   - Route traffic through the VPN gateways

### Prerequisites for WireGuard

Before running containers, ensure the WireGuard kernel module is loaded on the host:

```bash
# Check if WireGuard module is loaded
lsmod | grep wireguard

# Load the module if not present
sudo modprobe wireguard

# Verify it's loaded
lsmod | grep wireguard
```

If the module is not available:
```bash
# On Ubuntu/Debian
sudo apt-get update
sudo apt-get install wireguard

# On RHEL/CentOS
sudo yum install epel-release
sudo yum install wireguard-tools
```

### Testing

Test with host network mode:
```bash
# Load WireGuard module
sudo modprobe wireguard

# Run container with host network
docker run \
  --platform linux/amd64 \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  --cap-add=SYS_MODULE \
  --device=/dev/net/tun:/dev/net/tun \
  --network=host \
  --env LICENSE_KEY="your-key" \
  --name test-wg \
  -d \
  datagram

# Wait 30-60 seconds for VPN to connect
sleep 60

# Check for wg0 interface
docker exec test-wg ip link show
# Should show wg0 if everything is working
```

### Current Project Configuration

The current configuration in this project uses `--network=bridge` because:
1. The project is designed to run 500+ containers
2. Container isolation is a priority
3. Security is prioritized over visible wg0 interfaces
4. The VPN may use userspace implementation that doesn't require kernel interfaces

If you need to modify the configuration to use host network mode, update:
- `webapp/app.py` - Change `'network_mode': 'bridge'` to `'network_mode': 'host'`
- `datagram/start.sh` - Change `--network=bridge` to `--network=host`
- `dockerfiles/datagram-entrypoint.sh` - No changes needed

**Warning**: Making this change will break the ability to run 500+ isolated containers.
