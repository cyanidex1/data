# Quick Start Guide

## Prerequisites
- Docker installed and running
- Docker Compose installed (or Docker with compose plugin)

## Installation & Deployment

### Step 1: Build the Datagram Image
Before starting the control panel, build the datagram node image:

```bash
docker build --platform linux/amd64 -t datagram datagram/
```

### Step 2: Start the Control Panel

Using Docker Compose (recommended):
```bash
docker compose up -d
```

Or using Docker directly:
```bash
cd webapp
docker build -t datagram-control-panel .
cd ..

docker run -d \
  --name datagram-control-panel \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/data:/data \
  -e SECRET_KEY=your-secret-key-here \
  --user root \
  datagram-control-panel
```

### Step 3: Access the Web Interface
Open your browser and navigate to:
```
http://localhost:5000
```

## Using the Control Panel

### Starting a New Container
1. Select "Local Docker" from the Docker Host dropdown
2. Enter your 32-character Datagram key
3. (Optional) Change the container name prefix from "node" to something else
4. Click "Start Container"

The panel will automatically assign the next available container name (e.g., node1, node2, etc.)

### Managing Containers
From the "Running Containers" section, you can:
- **Stop**: Gracefully stop a running container
- **Restart**: Restart a container
- **Kill**: Forcefully stop a container
- **Remove**: Delete a container permanently
- **Logs**: View the last 100 lines of container logs

### Adding Remote Docker Hosts

To manage containers on remote servers:

1. Click the "➕ Add Host" button
2. Fill in the details:
   - **Name**: A friendly name (e.g., "Production Server 1")
   - **URL**: Docker daemon URL (e.g., `tcp://192.168.1.100:2375`)
   - **Description**: Optional notes about this host

3. Click "Add Host"

#### Configuring Remote Docker Host

On the remote server, configure Docker to accept remote connections:

Edit `/etc/docker/daemon.json`:
```json
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}
```

Then restart Docker:
```bash
sudo systemctl restart docker
```

⚠️ **Security Warning**: Exposing Docker on TCP without TLS is insecure. Only use this in trusted networks or configure TLS authentication.

## Integration with Existing Cron Job

The control panel works seamlessly with your existing `datagram/unhealthy.sh` cron job (runs every 30 minutes). The cron job provides automatic recovery:
- Restarts unhealthy containers
- Starts exited containers

The web panel complements this by providing:
- Real-time monitoring
- Manual control and management
- Multi-host support
- Container logs viewing

## Environment Variables

Configure the control panel using these environment variables:

- `SECRET_KEY`: Flask secret key (change in production!) - default: "dev-secret-key-change-in-production"
- `DEBUG`: Enable debug mode (`True` or `False`) - default: "False"

Example in docker-compose.yml:
```yaml
environment:
  - SECRET_KEY=your-random-secret-key-here
  - DEBUG=False
```

## API Usage

The control panel provides a REST API for automation:

### Start a new container
```bash
curl -X POST http://localhost:5000/api/containers/start \
  -H "Content-Type: application/json" \
  -d '{
    "host_id": 0,
    "key": "92bcf2ae4e326968f40f8670a3596b80",
    "container_prefix": "node"
  }'
```

### List all containers
```bash
curl http://localhost:5000/api/containers
```

### Stop a container
```bash
curl -X POST http://localhost:5000/api/containers/0/fda5d98ee9fb/stop
```

### Remove a container
```bash
curl -X DELETE http://localhost:5000/api/containers/0/fda5d98ee9fb/remove
```

See README.md for complete API documentation.

## Troubleshooting

### Cannot access the web interface
- Check that the container is running: `docker ps | grep datagram-control-panel`
- Check logs: `docker logs datagram-control-panel`
- Verify port 5000 is not in use: `netstat -an | grep 5000`

### "Image 'datagram' not found" error
Build the datagram image first:
```bash
docker build --platform linux/amd64 -t datagram datagram/
```

### Remote host connection fails
1. Verify Docker daemon is running on remote host
2. Check firewall allows connections on port 2375
3. Test connection: `curl http://remote-host:2375/version`

### Permission denied accessing Docker socket
Ensure the container runs as root:
```yaml
services:
  datagram-control-panel:
    user: root  # Add this line
```

## Stopping the Control Panel

```bash
docker compose down
```

Or if running manually:
```bash
docker stop datagram-control-panel
docker rm datagram-control-panel
```

## Upgrading

1. Pull the latest changes
2. Rebuild the control panel:
   ```bash
   docker compose down
   docker compose up -d --build
   ```

Your Docker host configuration in `data/docker_hosts.json` will be preserved.
