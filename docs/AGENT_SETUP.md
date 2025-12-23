# Agent Setup Guide

This guide explains how to install and configure the Datagram Agent on hosts for remote container management.

## Architecture Overview

```
┌──────────────────────────────────────────────┐
│  Control Plane (Cloud/External)              │
│  ┌────────────────────────────────────┐     │
│  │  Flask WebApp                       │     │
│  │  + WebSocket Server                 │     │
│  │  + Agent Manager                    │     │
│  └──────────────┬─────────────────────┘     │
└─────────────────┼───────────────────────────┘
                  │ WebSocket/REST API
   ───────────────┼────────────────────
                  │
┌─────────────────┼───────────────────────────┐
│  Host (Proxmox) │                           │
│  ┌──────────────▼────────────────────┐     │
│  │  Lightweight Agent (50MB)          │     │
│  │  - Docker client                   │     │
│  │  - WebSocket client                │     │
│  │  - Command executor                │     │
│  └──────────────┬─────────────────────┘     │
│                 │                            │
│  ┌──────────────▼─────────────────────┐     │
│  │  Docker Daemon                      │     │
│  │  - Datagram nodes (100+)           │     │
│  └─────────────────────────────────────┘     │
└────────────────────────────────────────────┘
```

## Benefits of Agent-Based Architecture

1. **External Hosting**: Host control plane on cloud platforms (Railway, Render, etc.)
2. **Multi-Host Management**: Manage containers across multiple physical hosts
3. **Better Security**: No Docker socket exposure to internet
4. **Scalability**: Easy to add new hosts without VPN or firewall changes
5. **Real-Time Monitoring**: Health metrics reported every 30 seconds

## Prerequisites

- Docker installed on the host
- Network access to the control plane
- Docker images built on the host (datagram, element-node, etc.)

## Installation Steps

### 1. Generate API Key

On the control plane (webapp), generate an API key:

```bash
# Option 1: Use Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Option 2: Use OpenSSL
openssl rand -hex 32

# Option 3: Use the webapp UI (Admin Panel → Generate Agent Key)
```

Save this key securely - you'll need it for agent configuration.

### 2. Add API Key to Control Plane

Update the control plane's environment variables:

```bash
# Edit docker-compose.yml or .env file
AGENT_API_KEYS=your-generated-key-here,another-key-if-needed
```

Restart the control plane:

```bash
docker-compose restart datagram-control-panel
```

### 3. Deploy Agent on Host

Create a `.env` file for the agent:

```bash
# /path/to/agent/.env
CONTROL_PLANE_URL=https://your-control-plane.example.com
AGENT_API_KEY=your-generated-key-here
HOST_ID=production-server-1
```

**Important**: 
- Use `https://` (wss://) for production
- `HOST_ID` must be unique for each host
- Never commit API keys to version control

### 4. Start Agent Using Docker Compose

```bash
# Download the repository or copy the agent directory
git clone https://github.com/your-repo/data.git
cd data

# Create .env file with your configuration
cat > .env << EOF
CONTROL_PLANE_URL=https://your-control-plane.example.com
AGENT_API_KEY=your-generated-key-here
HOST_ID=production-server-1
EOF

# Start the agent
docker-compose -f docker-compose-agent.yml up -d

# Check logs
docker-compose -f docker-compose-agent.yml logs -f
```

### 5. Start Agent Using Docker Run

```bash
docker run -d \
  --name datagram-agent \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -e CONTROL_PLANE_URL=https://your-control-plane.example.com \
  -e AGENT_API_KEY=your-generated-key-here \
  -e HOST_ID=production-server-1 \
  --restart unless-stopped \
  your-registry/datagram-agent:latest
```

### 6. Verify Connection

Check the agent logs to confirm connection:

```bash
docker logs datagram-agent
```

You should see:
```
[*] Connected to Docker daemon
[*] Connecting to control plane: wss://your-control-plane.example.com/api/agent/ws
[*] WebSocket connected to control plane
[*] Started health reporting thread (reporting every 30 seconds)
```

Check the control plane:
- Go to Admin Panel → Agent Status
- Your agent should show as "Connected" with a green indicator

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONTROL_PLANE_URL` | Yes | - | URL of the control plane webapp |
| `AGENT_API_KEY` | Yes | - | Authentication key for the agent |
| `HOST_ID` | Yes | - | Unique identifier for this host |

### Resource Limits

The agent is designed to be lightweight:
- Memory limit: 50MB
- CPU: Minimal usage (mostly idle)
- Network: WebSocket + HTTP for health reports

## Troubleshooting

### Agent Won't Connect

**Error**: `Failed to create WebSocket connection`

**Solutions**:
1. Check if control plane is accessible: `curl https://your-control-plane.example.com`
2. Verify firewall allows outbound connections to control plane port
3. Check if API key is correct
4. Ensure control plane has `AGENT_API_KEYS` configured

### Agent Connects but Disconnects

**Error**: `WebSocket connection closed`

**Solutions**:
1. Check control plane logs for authentication errors
2. Verify API key matches on both sides
3. Check network stability between host and control plane
4. Ensure control plane is running with SocketIO enabled

### Docker Socket Permission Denied

**Error**: `Permission denied connecting to Docker daemon`

**Solutions**:
1. Ensure Docker socket is mounted: `-v /var/run/docker.sock:/var/run/docker.sock`
2. Check if agent user has Docker permissions (or run as root)
3. Verify Docker daemon is running: `docker ps`

### Agent Shows as Disconnected in UI

**Solutions**:
1. Check agent logs: `docker logs datagram-agent`
2. Verify agent container is running: `docker ps | grep datagram-agent`
3. Check network connectivity: `docker exec datagram-agent ping -c 1 your-control-plane.example.com`
4. Restart agent: `docker restart datagram-agent`

### Commands Timeout

**Error**: `Command timed out (no response from agent)`

**Solutions**:
1. Check if agent is connected
2. Verify Docker daemon on host is responsive
3. Check host resource usage (CPU, memory)
4. Increase timeout in control plane if operations are legitimately slow

## Security Best Practices

### 1. Use TLS/SSL (wss://)

Always use HTTPS for the control plane in production:

```bash
CONTROL_PLANE_URL=https://your-control-plane.example.com  # ✓ Good
CONTROL_PLANE_URL=http://your-control-plane.example.com   # ✗ Bad (dev only)
```

### 2. Strong API Keys

Generate secure API keys (minimum 32 bytes):

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Rotate Keys Regularly

Update API keys periodically:

```bash
# Generate new key
NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Add to control plane (keep old key for transition)
AGENT_API_KEYS=old-key,$NEW_KEY

# Update agent
docker-compose -f docker-compose-agent.yml down
# Update .env with NEW_KEY
docker-compose -f docker-compose-agent.yml up -d

# Remove old key from control plane after all agents updated
AGENT_API_KEYS=$NEW_KEY
```

### 4. Mount Docker Socket Read-Only

When possible, mount Docker socket as read-only:

```bash
-v /var/run/docker.sock:/var/run/docker.sock:ro
```

Note: Some operations (create, remove) require write access.

### 5. Network Isolation

Use firewall rules to restrict agent connections:

```bash
# Allow only control plane IP
sudo ufw allow from <control-plane-ip> to any port 443

# Block all other incoming
sudo ufw default deny incoming
```

### 6. Monitor Agent Logs

Regularly check agent logs for suspicious activity:

```bash
docker logs datagram-agent --since 24h | grep -i error
```

## Maintenance

### Updating the Agent

```bash
# Pull latest image
docker pull your-registry/datagram-agent:latest

# Restart agent
docker-compose -f docker-compose-agent.yml pull
docker-compose -f docker-compose-agent.yml up -d
```

### Health Monitoring

The agent reports health metrics every 30 seconds:
- Container counts
- Docker version
- System resources
- Connection status

View health data in the control plane Admin Panel.

### Logs

View agent logs:

```bash
# Follow live logs
docker logs -f datagram-agent

# Last 100 lines
docker logs --tail 100 datagram-agent

# Since specific time
docker logs --since 1h datagram-agent
```

## Advanced Configuration

### Custom Network

```yaml
# docker-compose-agent.yml
services:
  datagram-agent:
    # ...
    networks:
      - custom-network

networks:
  custom-network:
    external: true
```

### Resource Limits

```yaml
# docker-compose-agent.yml
services:
  datagram-agent:
    # ...
    mem_limit: 100m  # Increase if needed
    cpus: 0.5        # Limit CPU usage
```

### Logging

```yaml
# docker-compose-agent.yml
services:
  datagram-agent:
    # ...
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review agent logs: `docker logs datagram-agent`
3. Check control plane logs
4. Open an issue on GitHub

## Next Steps

- See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for migrating from Docker socket to agent
- See [README.md](../README.md) for general usage
