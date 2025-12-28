#!/bin/bash
# Diagnostic script to identify why multiple containers don't show as online

echo "=== Datagram Container Diagnostics ==="
echo ""
echo "This script helps diagnose why only one container shows online on datagram.network"
echo ""

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not available"
    exit 1
fi

echo "1. Checking running datagram containers..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
CONTAINERS=$(docker ps --filter "ancestor=datagram" --format "{{.Names}}" 2>/dev/null)

if [ -z "$CONTAINERS" ]; then
    echo "⚠️  No running datagram containers found"
    echo ""
    echo "To test, start containers with:"
    echo "  cd datagram"
    echo "  ./start.sh <key1> test"
    echo "  ./start.sh <key2> test"
    exit 0
fi

echo "Found containers:"
echo "$CONTAINERS" | while read container; do
    echo "  ✓ $container"
done
echo ""

# For each container, perform diagnostics
echo "$CONTAINERS" | while read container; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Container: $container"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Check container status
    echo "📊 Container Status:"
    docker inspect "$container" --format '  State: {{.State.Status}}' 2>/dev/null
    docker inspect "$container" --format '  Running: {{.State.Running}}' 2>/dev/null
    docker inspect "$container" --format '  Started: {{.State.StartedAt}}' 2>/dev/null
    echo ""
    
    # Check network configuration
    echo "🌐 Network Configuration:"
    docker inspect "$container" --format '  Network Mode: {{.HostConfig.NetworkMode}}' 2>/dev/null
    docker inspect "$container" --format '  Hostname: {{.Config.Hostname}}' 2>/dev/null
    docker inspect "$container" --format '  MAC Address: {{.NetworkSettings.MacAddress}}' 2>/dev/null
    docker inspect "$container" --format '  IP Address: {{.NetworkSettings.IPAddress}}' 2>/dev/null
    echo ""
    
    # Check volume mounts
    echo "💾 Volume Mounts:"
    docker inspect "$container" --format '{{range .Mounts}}  {{.Type}}: {{.Name}} → {{.Destination}}{{"\n"}}{{end}}' 2>/dev/null
    echo ""
    
    # Check network interfaces
    echo "🔌 Network Interfaces:"
    docker exec "$container" ip addr show 2>/dev/null | grep -E '^[0-9]+:|inet ' | sed 's/^/  /' || echo "  (failed to retrieve)"
    echo ""
    
    # Check for VPN/WireGuard interfaces
    echo "🔐 VPN/WireGuard Status:"
    if docker exec "$container" ip addr show 2>/dev/null | grep -q "tun0\|wg0"; then
        echo "  ✓ VPN interface found"
        docker exec "$container" ip addr show 2>/dev/null | grep -A 2 "tun0\|wg0" | sed 's/^/    /'
    else
        echo "  ⚠️  No VPN interface (tun0/wg0) found"
    fi
    echo ""
    
    # Check processes
    echo "⚙️  Running Processes:"
    docker exec "$container" ps aux 2>/dev/null | grep -v grep | grep -E "datagram|vpn|wireguard|conference" | sed 's/^/  /' || echo "  (no datagram processes found)"
    echo ""
    
    # Check for errors in logs (last 50 lines)
    echo "📋 Recent Log Errors/Warnings:"
    docker logs "$container" 2>&1 | tail -50 | grep -i -E "error|fail|warn|cannot|unable" | tail -10 | sed 's/^/  /' || echo "  (no errors found in recent logs)"
    echo ""
    
    # Check last 10 lines of logs
    echo "📜 Last 10 Log Lines:"
    docker logs "$container" 2>&1 | tail -10 | sed 's/^/  /'
    echo ""
    
done

# Summary section
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

CONTAINER_COUNT=$(echo "$CONTAINERS" | wc -l)
echo "Total Containers Running: $CONTAINER_COUNT"
echo ""

# Check for VPN interfaces
VPN_COUNT=0
echo "$CONTAINERS" | while read container; do
    if docker exec "$container" ip addr show 2>/dev/null | grep -q "tun0\|wg0"; then
        VPN_COUNT=$((VPN_COUNT + 1))
    fi
done

echo "Containers with VPN: Check individual status above"
echo ""

echo "🔍 Potential Issues to Look For:"
echo "  1. Are all containers actually running?"
echo "  2. Do all containers have VPN interfaces (tun0/wg0)?"
echo "  3. Are there any error messages in the logs?"
echo "  4. Do containers have unique volumes mounted?"
echo "  5. Are there any port binding conflicts?"
echo ""

echo "💡 Next Steps:"
echo "  • If containers are running but no VPN: Check license keys"
echo "  • If VPN is up but not showing online: Might be datagram.network limitation"
echo "  • If seeing errors: Share the error messages for troubleshooting"
echo ""

echo "📝 To share diagnostics, run:"
echo "  ./diagnose_containers.sh > diagnostics.txt"
echo "  # Then share diagnostics.txt"
