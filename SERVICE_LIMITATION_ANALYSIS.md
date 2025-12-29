# Understanding the Datagram.Network Limitation

## The Issue

Multiple attempts to fix the "only last container shows online" problem have not worked:
1. ❌ Hostname fix - Didn't work
2. ❌ MAC address fix - Didn't work  
3. ❌ Separate volumes fix - Didn't work

## What This Suggests

This pattern suggests the issue might not be with the container configuration at all, but rather **a limitation of how datagram.network identifies and displays nodes**.

## Likely Explanation: One Node Per Public IP

VPN services like datagram.network typically identify nodes using a combination of:
- License key (unique per node)
- Public IP address (same for all containers on one host)
- VPN connection details

**The service might be designed to show only ONE active node per public IP address**, regardless of:
- Different license keys
- Container isolation
- Separate configurations

This would be expected behavior for many VPN services that:
- Track nodes by public IP for security/billing
- Prevent multiple simultaneous connections from same IP
- Limit nodes per account/location

## How to Verify This

### Test 1: Check Container Status
Run the diagnostic script to verify all containers are running and connected:
```bash
./diagnose_containers.sh
```

Look for:
- ✅ Both containers running
- ✅ Both have VPN interfaces (tun0/wg0)
- ✅ No errors in logs
- ✅ Separate volumes mounted

If all these are true, the containers are working correctly and the limitation is service-side.

### Test 2: Different Public IPs
The definitive test: Run containers on **different hosts with different public IPs**:

Host 1 (Public IP: X.X.X.X):
```bash
./datagram/start.sh f84e576e16b6c0fa5fb98db88e475ac2 test
```

Host 2 (Public IP: Y.Y.Y.Y):
```bash
./datagram/start.sh 92bcf2ae4e326968f40f8670a3596b80 test
```

If both show as online when on different public IPs, this confirms it's an IP-based limitation.

### Test 3: Check Datagram Documentation
Check if datagram.network documentation mentions:
- Limits on nodes per IP address
- Requirements for running multiple nodes
- Whether multiple nodes per IP is supported

## What This Means for Your Use Case

### If It's a Service Limitation

You have several options:

1. **Accept one node per host** - This might be the intended design
2. **Use multiple hosts** - Deploy containers across multiple servers with different IPs
3. **Use VPN/Proxy** - Give each container a different public IP via VPN or proxy
4. **Contact support** - Ask datagram.network if multiple nodes per IP is supported

### If Containers Aren't Working

If the diagnostic script shows errors or containers aren't getting VPN interfaces, then there IS a container configuration issue to fix.

## Architecture Solutions

### Option 1: Multi-Host Deployment (Recommended)
```
Host 1 (IP: X.X.X.X) → Container 1 → datagram.network (shows online)
Host 2 (IP: Y.Y.Y.Y) → Container 2 → datagram.network (shows online)
Host 3 (IP: Z.Z.Z.Z) → Container 3 → datagram.network (shows online)
```

### Option 2: NAT with Unique IPs
Give each container its own public IP via NAT:
```
Host (Multiple Public IPs)
├── Container 1 → IP1 → datagram.network
├── Container 2 → IP2 → datagram.network
└── Container 3 → IP3 → datagram.network
```

This requires:
- Multiple public IPs
- Advanced networking configuration
- May not be practical for all setups

### Option 3: Accept the Limitation
If datagram.network only supports one node per IP:
```
Host → Run ONE container → datagram.network (shows online)
```

Use multiple hosts if you need multiple nodes.

## Diagnostic Checklist

Run through this checklist to determine the actual issue:

- [ ] Run `./diagnose_containers.sh` and save output
- [ ] Verify both containers are running (`docker ps`)
- [ ] Check both have VPN interfaces (`ip addr show` in container)
- [ ] Check logs for connection errors
- [ ] Check datagram.network documentation for IP limits
- [ ] Test with containers on different public IPs (if possible)
- [ ] Contact datagram.network support to confirm behavior

## Next Steps

1. **Run diagnostics**: `./diagnose_containers.sh > diagnostics.txt`
2. **Share results**: Post the diagnostics output
3. **Check service docs**: Look for IP-based limitations
4. **Test different IPs**: If possible, test on different hosts

Based on the diagnostic results, we can determine if this is:
- A container configuration issue (fixable)
- A datagram.network service limitation (need different approach)
- Something else entirely

## Conclusion

After three different fix attempts failed, the most likely explanation is that **datagram.network only displays one node per public IP address as a service-level limitation**. This would be normal for VPN services.

The fix isn't changing the container configuration—it's understanding the service's architecture and deploying accordingly (multiple hosts or multiple public IPs).

Run the diagnostic script to confirm whether the containers themselves are working correctly.
