# Migration Guide: Docker Socket to Agent-Based Architecture

This guide explains how to migrate from the traditional Docker socket-based architecture to the agent-based architecture.

## Table of Contents

1. [Overview](#overview)
2. [Migration Strategy](#migration-strategy)
3. [Hybrid Mode](#hybrid-mode)
4. [Step-by-Step Migration](#step-by-step-migration)
5. [Rollback Procedure](#rollback-procedure)
6. [Post-Migration Verification](#post-migration-verification)

## Overview

### Before: Docker Socket Architecture

```
┌────────────────────────────────────┐
│  Same Host                         │
│  ┌──────────────────────────┐     │
│  │  WebApp                   │     │
│  │  /var/run/docker.sock     │     │
│  └──────────┬───────────────┘     │
│             │ Docker Socket        │
│  ┌──────────▼───────────────┐     │
│  │  Docker Daemon            │     │
│  │  - All containers         │     │
│  └───────────────────────────┘     │
└────────────────────────────────────┘
```

**Limitations**:
- Single point of failure
- Cannot scale across multiple hosts
- Security concerns with Docker socket access
- Webapp must be on same host as containers

### After: Agent-Based Architecture

```
┌──────────────────────────────────────┐
│  Control Plane (External)             │
│  ┌────────────────────────────┐     │
│  │  WebApp (Cloud/Railway)     │     │
│  │  + WebSocket Server         │     │
│  └──────────┬─────────────────┘     │
└─────────────┼───────────────────────┘
              │ WebSocket/REST
   ───────────┼────────────────
              │
┌─────────────▼───────────────────────┐
│  Host 1                              │
│  ┌────────────────────────────┐     │
│  │  Agent (50MB)               │     │
│  └──────────┬─────────────────┘     │
│  ┌──────────▼─────────────────┐     │
│  │  Docker Daemon              │     │
│  └─────────────────────────────┘     │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  Host 2                              │
│  ┌────────────────────────────┐     │
│  │  Agent (50MB)               │     │
│  └──────────┬─────────────────┘     │
│  ┌──────────▼─────────────────┐     │
│  │  Docker Daemon              │     │
│  └─────────────────────────────┘     │
└──────────────────────────────────────┘
```

**Benefits**:
- External hosting (Railway, Render, etc.)
- Multi-host management
- Better security
- Scalability
- Real-time monitoring

## Migration Strategy

### Recommended Approach: Gradual Migration

The system supports **hybrid mode**, where some hosts use Docker socket and others use agents. This allows zero-downtime migration:

1. **Phase 1**: Add agent mode support to control plane (already done)
2. **Phase 2**: Deploy agents on hosts (one at a time)
3. **Phase 3**: Switch hosts from Docker socket to agent mode (gradual)
4. **Phase 4**: Move control plane to external hosting (optional)

### Migration Timeline

- **Small deployments** (1-3 hosts): 1-2 hours
- **Medium deployments** (4-10 hosts): 4-8 hours
- **Large deployments** (10+ hosts): Plan 1-2 days with staged rollout

## Hybrid Mode

The system automatically detects connection type per host:

```python
# Host configuration
{
  "id": 0,
  "name": "Host 1",
  "connection_type": "docker_socket",  # or "agent"
  "agent_api_key": "...",
  "agent_status": {
    "connected": false,
    "last_health_check": null
  }
}
```

**How it works**:
1. When a container operation is requested, the system checks the host's `connection_type`
2. If `agent`, it routes the command via WebSocket
3. If `docker_socket`, it uses direct Docker API
4. No changes needed in frontend or API calls

## Step-by-Step Migration

### Prerequisites

- [ ] Control plane running with agent support
- [ ] Access to all hosts you want to migrate
- [ ] API keys generated for each host
- [ ] Network connectivity between hosts and control plane

### Step 1: Update Control Plane

1. **Update the control plane code**:
   ```bash
   git pull origin main
   ```

2. **Update dependencies**:
   ```bash
   cd webapp
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   # Generate API keys for each host
   python3 -c "import secrets; print(secrets.token_hex(32))"
   
   # Add to docker-compose.yml or .env
   AGENT_API_KEYS=key1,key2,key3
   ```

4. **Restart control plane**:
   ```bash
   docker-compose restart datagram-control-panel
   ```

5. **Verify WebSocket is working**:
   ```bash
   docker logs datagram-control-panel | grep "SocketIO initialized"
   ```

### Step 2: Deploy Agent on First Host

Choose a non-critical host for the first migration.

1. **Prepare configuration**:
   ```bash
   # On the host
   cat > .env << EOF
   CONTROL_PLANE_URL=https://your-control-plane.example.com
   AGENT_API_KEY=your-first-host-key
   HOST_ID=host-1
   EOF
   ```

2. **Start the agent**:
   ```bash
   # Option 1: Using docker-compose
   docker-compose -f docker-compose-agent.yml up -d
   
   # Option 2: Using docker run
   docker run -d \
     --name datagram-agent \
     -v /var/run/docker.sock:/var/run/docker.sock:ro \
     -e CONTROL_PLANE_URL=https://your-control-plane.example.com \
     -e AGENT_API_KEY=your-first-host-key \
     -e HOST_ID=host-1 \
     --restart unless-stopped \
     datagram-agent:latest
   ```

3. **Verify connection**:
   ```bash
   docker logs datagram-agent
   ```
   
   Should see:
   ```
   [*] WebSocket connected to control plane
   [*] Started health reporting thread
   ```

### Step 3: Update Host Configuration

1. **Log in to the control plane UI**

2. **Go to Admin Panel**

3. **Find your host in the hosts list**

4. **Edit the host**:
   - Change `connection_type` from `docker_socket` to `agent`
   - Add the `agent_api_key` (the one you used for the agent)
   - Save

   Or via API:
   ```bash
   curl -X PUT https://your-control-plane.example.com/api/hosts/0 \
     -H "Content-Type: application/json" \
     -H "Cookie: session=..." \
     -d '{
       "connection_type": "agent",
       "agent_api_key": "your-first-host-key"
     }'
   ```

### Step 4: Test the Migration

1. **Check agent status** in Admin Panel:
   - Agent should show as "Connected" (green)
   - Health metrics should be visible

2. **Test container operations**:
   ```bash
   # Start a test container
   curl -X POST https://your-control-plane.example.com/api/containers/start \
     -H "Content-Type: application/json" \
     -d '{
       "host_id": 0,
       "node_type": "datagram",
       "key": "test0000000000000000000000000000"
     }'
   ```

3. **Verify the container started**:
   ```bash
   # On the host
   docker ps | grep test0000000000000000000000000000
   ```

4. **Test other operations**:
   - Stop container
   - Restart container
   - View logs
   - Remove container

### Step 5: Migrate Remaining Hosts

Repeat Steps 2-4 for each remaining host:

1. Deploy agent on host
2. Verify agent connection
3. Update host configuration to use agent
4. Test operations

**Tip**: Migrate one host at a time and verify before proceeding.

### Step 6: Move Control Plane (Optional)

Once all hosts are using agents, you can move the control plane to external hosting:

1. **Choose a hosting platform**:
   - Railway
   - Render
   - Heroku
   - AWS ECS
   - Your own VPS

2. **Deploy control plane**:
   ```bash
   # Example for Railway
   railway init
   railway up
   
   # Configure environment variables
   railway variables set SECRET_KEY=...
   railway variables set AGENT_API_KEYS=...
   ```

3. **Update agent configurations**:
   ```bash
   # On each host
   docker-compose -f docker-compose-agent.yml down
   
   # Update CONTROL_PLANE_URL in .env
   CONTROL_PLANE_URL=https://your-new-url.railway.app
   
   docker-compose -f docker-compose-agent.yml up -d
   ```

4. **Verify all agents reconnect**

## Rollback Procedure

If you encounter issues during migration, you can quickly rollback:

### Rollback a Single Host

1. **Stop the agent**:
   ```bash
   docker-compose -f docker-compose-agent.yml down
   ```

2. **Update host configuration** in UI:
   - Change `connection_type` back to `docker_socket`
   - Remove `agent_api_key`

3. **Verify Docker socket access**:
   - The host should work immediately via Docker socket

### Rollback All Hosts

1. **For each host**:
   ```bash
   docker-compose -f docker-compose-agent.yml down
   ```

2. **Update control plane**:
   - Set all hosts to `connection_type: docker_socket`
   - Or restore from backup if you have one

3. **Restart control plane** without agent support:
   ```bash
   # Remove SocketIO dependencies if desired
   docker-compose restart datagram-control-panel
   ```

### Emergency Rollback

If the control plane is unreachable:

1. **Stop all agents** on all hosts

2. **Manage containers directly** on each host:
   ```bash
   # Traditional docker commands work
   docker ps
   docker start container_name
   docker stop container_name
   ```

3. **Fix control plane** and restore service

4. **Redeploy agents** when ready

## Post-Migration Verification

### Health Checks

1. **Agent Connectivity**:
   - [ ] All agents show "Connected" in Admin Panel
   - [ ] Health metrics are being reported (check timestamps)
   - [ ] No errors in agent logs

2. **Container Operations**:
   - [ ] Can start new containers
   - [ ] Can stop/restart existing containers
   - [ ] Can view container logs
   - [ ] Can remove containers
   - [ ] Bulk operations work

3. **Performance**:
   - [ ] Container list loads within 2-3 seconds
   - [ ] Commands execute within 5 seconds
   - [ ] No timeout errors
   - [ ] UI remains responsive

### Monitoring Setup

1. **Set up alerting** for agent disconnections:
   ```bash
   # Monitor agent logs for errors
   docker logs -f datagram-agent | grep -i error
   ```

2. **Monitor control plane** for WebSocket issues:
   ```bash
   docker logs -f datagram-control-panel | grep -i websocket
   ```

3. **Check resource usage**:
   ```bash
   # Agent should use <50MB RAM
   docker stats datagram-agent
   ```

### Common Issues

#### Agent Won't Connect

**Symptom**: Agent shows "Disconnected" in UI

**Solution**:
1. Check agent logs: `docker logs datagram-agent`
2. Verify API key matches
3. Check network connectivity
4. Verify control plane URL is accessible

#### Commands Time Out

**Symptom**: "Command timed out" errors

**Solution**:
1. Check if agent is connected
2. Verify Docker daemon on host is responsive: `docker ps`
3. Check host resource usage: `top` or `htop`
4. Restart agent if needed: `docker restart datagram-agent`

#### Containers Not Visible

**Symptom**: Containers exist on host but don't show in UI

**Solution**:
1. Check if agent is sending health reports
2. Verify host ID matches
3. Clear browser cache
4. Check for errors in control plane logs

## Best Practices

1. **Test on Non-Production First**: Always migrate dev/test environments first

2. **One Host at a Time**: Don't migrate all hosts simultaneously

3. **Monitor Closely**: Watch logs and metrics during migration

4. **Keep Backups**: Backup host configurations before changes

5. **Document Custom Changes**: Note any custom configurations or workarounds

6. **Have Rollback Plan Ready**: Know how to quickly revert changes

7. **Schedule During Low Usage**: Migrate during off-peak hours

8. **Communicate Changes**: Notify team members of the migration

## Troubleshooting

See [AGENT_SETUP.md](AGENT_SETUP.md#troubleshooting) for detailed troubleshooting steps.

## Support

If you encounter issues during migration:

1. Check agent logs: `docker logs datagram-agent`
2. Check control plane logs: `docker logs datagram-control-panel`
3. Review this guide's troubleshooting section
4. Open an issue on GitHub with logs and error messages

## Next Steps

After successful migration:

1. Monitor agent health metrics
2. Set up alerting for agent disconnections
3. Consider adding more hosts
4. Explore external hosting options for control plane
5. Implement TLS/SSL for production security

---

**Questions?** See [AGENT_SETUP.md](AGENT_SETUP.md) or contact support.
