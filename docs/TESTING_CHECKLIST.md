# Testing Checklist for Agent-Based Architecture

## Pre-Deployment Testing

### 1. Control Plane Verification
- [ ] Control plane starts successfully with `docker-compose up`
- [ ] WebSocket server initializes without errors
- [ ] Admin panel loads correctly
- [ ] Agent Status section displays in admin panel
- [ ] Generate API Key button works and copies to clipboard

### 2. Agent Deployment Testing
- [ ] Agent container builds successfully
- [ ] Agent connects to control plane via WebSocket
- [ ] Agent shows "Connected" status in admin panel
- [ ] Agent reports health metrics every 30 seconds
- [ ] Health metrics display correctly in admin panel

### 3. Container Operations via Agent
- [ ] Start new container via agent
- [ ] Stop container via agent
- [ ] Restart container via agent
- [ ] Kill container via agent
- [ ] Remove container via agent
- [ ] View container logs via agent

### 4. Backward Compatibility
- [ ] Docker socket mode still works for existing hosts
- [ ] Can list containers from Docker socket hosts
- [ ] Can perform operations on Docker socket hosts
- [ ] Hybrid mode works (mix of agent and socket hosts)

### 5. Disconnection/Reconnection
- [ ] Stop agent - shows "Disconnected" in admin panel
- [ ] Restart agent - auto-reconnects successfully
- [ ] Agent uses exponential backoff for reconnections
- [ ] Commands fail gracefully when agent disconnected

### 6. Security Testing
- [ ] Invalid API key is rejected
- [ ] Agent authentication works correctly
- [ ] Control plane validates API keys
- [ ] WebSocket uses TLS (wss://) in production
- [ ] No sensitive data in logs

## Manual Test Commands

### Test Agent Locally

```bash
# Terminal 1: Start control plane
cd /home/runner/work/data/data
export AGENT_API_KEYS=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "API Key: $AGENT_API_KEYS"
docker-compose up

# Terminal 2: Start agent
cd /home/runner/work/data/data
export CONTROL_PLANE_URL=http://localhost:5000
export AGENT_API_KEY=<use-key-from-terminal-1>
export HOST_ID=test-agent-1
docker-compose -f docker-compose-agent.yml up
```

### Verify Connection

```bash
# Check control plane logs
docker logs datagram-control-panel | grep -i agent

# Check agent logs
docker logs datagram-agent | grep -i connected

# Check agent status via API
curl -s http://localhost:5000/api/agents/status | python3 -m json.tool
```

### Test Container Operations

```bash
# Start a test container via agent
curl -X POST http://localhost:5000/api/containers/start \
  -H "Content-Type: application/json" \
  -d '{
    "host_id": 0,
    "node_type": "datagram",
    "key": "test0000000000000000000000000000"
  }'

# List containers
curl -s http://localhost:5000/api/containers | python3 -m json.tool

# Stop container
curl -X POST http://localhost:5000/api/containers/0/test0000000000000000000000000000/stop

# Remove container
curl -X DELETE http://localhost:5000/api/containers/0/test0000000000000000000000000000/remove
```

## Performance Testing

- [ ] Agent uses < 50MB RAM
- [ ] WebSocket connections stable under load
- [ ] Health reports don't cause performance issues
- [ ] Multiple agents can connect simultaneously
- [ ] Container list loads within 2-3 seconds

## Documentation Verification

- [ ] README.md is accurate and up-to-date
- [ ] AGENT_SETUP.md instructions work correctly
- [ ] MIGRATION_GUIDE.md steps are clear
- [ ] All links in documentation work

## Known Limitations

1. **Docker socket mount**: Agent needs Docker socket access (read-only when possible)
2. **Network connectivity**: Agent must have network access to control plane
3. **TLS requirement**: Production should use wss:// (TLS encrypted)
4. **API key security**: Keys must be stored securely and not committed to repos

## Security Scan Results

- ✅ CodeQL: 0 vulnerabilities found
- ✅ Code Review: All comments addressed
- ✅ Python syntax: No compilation errors

## Post-Testing

After successful testing:
1. Update this checklist with any issues found
2. Document workarounds or fixes
3. Update documentation if needed
4. Prepare deployment guide for production
