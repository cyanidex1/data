# Datagram Node Control Panel

A web-based control panel for managing Docker containers running Datagram nodes across multiple Docker hosts.

## Features

- 🚀 **Start Containers**: Enter a 32-character key and start a new Datagram node container
- 📊 **Monitor Containers**: View all running containers across multiple hosts in real-time
- 🖥️ **Multi-Host Management**: Add and manage multiple Docker hosts from a single interface
- 🎮 **Container Operations**: Start, stop, restart, kill, and remove containers
- 📝 **View Logs**: Check container logs directly from the web interface
- 🔄 **Auto-Refresh**: Dashboard automatically refreshes every 10 seconds
- 🐳 **Docker Integration**: Works seamlessly with the existing `unhealthy.sh` cron job

## Quick Start

### Method 1: Using Docker Compose (Recommended)

1. **Build and start the control panel:**
   ```bash
   docker-compose up -d
   ```

2. **Access the web interface:**
   Open your browser and navigate to `http://localhost:5000`

3. **Build the datagram image** (if not already built):
   ```bash
   docker build --platform linux/amd64 -t datagram .
   ```

### Method 2: Manual Docker Run

1. **Build the webapp image:**
   ```bash
   cd webapp
   docker build -t datagram-control-panel .
   cd ..
   ```

2. **Run the control panel:**
   ```bash
   docker run -d \
     --name datagram-control-panel \
     -p 5000:5000 \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v $(pwd)/data:/data \
     -e SECRET_KEY=your-secret-key-here \
     datagram-control-panel
   ```

3. **Access the web interface:**
   Open `http://localhost:5000`

## Usage

### Starting a New Container

1. Select a Docker host from the dropdown
2. Enter your 32-character Datagram key
3. (Optional) Change the container name prefix
4. Click "Start Container"

The control panel will automatically find the next available container name (e.g., `node1`, `node2`, etc.)

### Managing Docker Hosts

#### Add Local Host
By default, a local Docker host is added automatically. This connects to the Docker daemon via the mounted socket.

#### Add Remote Host
1. Click "➕ Add Host" button
2. Enter a name for the host (e.g., "Production Server")
3. Enter the Docker host URL:
   - For local: `local`
   - For remote: `tcp://hostname:2375` or `tcp://ip:2375`
4. (Optional) Add a description
5. Click "Add Host"

**Note:** For remote hosts, ensure the Docker daemon is configured to accept remote connections:
```bash
# On the remote host, edit /etc/docker/daemon.json
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}
```

⚠️ **Security Warning**: Exposing Docker on TCP without TLS is insecure. Use this only in trusted networks or configure TLS.

### Container Operations

From the Running Containers table, you can:
- **Start**: Start a stopped container
- **Stop**: Gracefully stop a running container
- **Restart**: Restart a container
- **Kill**: Forcefully stop a container
- **Remove**: Delete a container (permanent)
- **Logs**: View the last 100 lines of container logs

### Existing Cron Job Integration

The control panel works alongside your existing `unhealthy.sh` cron job that runs every 30 minutes. The cron job will:
- Restart unhealthy containers
- Start any exited containers

The web panel provides real-time monitoring and manual control, while the cron job provides automatic recovery.

## Directory Structure

```
.
├── Dockerfile                  # Original datagram node Dockerfile
├── docker-compose.yml          # Compose file for control panel
├── start.sh                    # Original script for starting nodes
├── unhealthy.sh               # Cron script for auto-recovery
├── entrypoint.sh              # Node entrypoint script
├── datagram-cli-x86_64-linux  # Datagram CLI binary
├── webapp/
│   ├── Dockerfile             # Control panel Dockerfile
│   ├── requirements.txt       # Python dependencies
│   ├── app.py                # Flask application
│   └── templates/
│       └── index.html        # Web interface
└── data/
    └── docker_hosts.json     # Persistent host configuration
```

## Configuration

### Environment Variables

The control panel supports the following environment variables:

- `SECRET_KEY`: Flask secret key (change in production)
- `DEBUG`: Enable debug mode (`True` or `False`)

### Persistent Data

The control panel stores Docker host configurations in `/data/docker_hosts.json`. This file is mounted as a volume to persist between container restarts.

## API Endpoints

The control panel exposes a REST API for programmatic access:

### Hosts
- `GET /api/hosts` - List all Docker hosts
- `POST /api/hosts` - Add a new Docker host
- `DELETE /api/hosts/<id>` - Remove a Docker host

### Containers
- `GET /api/containers` - List all containers across all hosts
- `POST /api/containers/start` - Start a new container with a key
- `POST /api/containers/<host_id>/<container_id>/start` - Start an existing container
- `POST /api/containers/<host_id>/<container_id>/stop` - Stop a container
- `POST /api/containers/<host_id>/<container_id>/restart` - Restart a container
- `POST /api/containers/<host_id>/<container_id>/kill` - Kill a container
- `DELETE /api/containers/<host_id>/<container_id>/remove` - Remove a container
- `GET /api/containers/<host_id>/<container_id>/logs` - Get container logs

## Requirements

- Docker 20.10+
- Docker Compose 2.0+ (for compose method)
- Python 3.11+ (for development)

## Development

To run the control panel in development mode:

```bash
cd webapp
pip install -r requirements.txt
export DEBUG=True
python app.py
```

The application will be available at `http://localhost:5000` with debug mode enabled.

## Troubleshooting

### Cannot connect to Docker daemon

**Error**: `Cannot connect to Docker host`

**Solution**: Ensure the Docker socket is properly mounted:
```bash
docker run -v /var/run/docker.sock:/var/run/docker.sock ...
```

### Image 'datagram' not found

**Error**: `Image "datagram" not found on host`

**Solution**: Build the datagram image first:
```bash
docker build --platform linux/amd64 -t datagram .
```

### Remote host connection fails

**Error**: `Could not connect to Docker host`

**Solution**: 
1. Verify the Docker daemon is running on the remote host
2. Check that the Docker daemon is configured to accept remote connections
3. Ensure firewall rules allow connections on port 2375
4. Test connection: `curl http://remote-host:2375/version`

## Security Considerations

1. **Change the SECRET_KEY** in production
2. **Use TLS** for remote Docker connections
3. **Restrict network access** to the control panel (use firewall rules or reverse proxy)
4. **Limit Docker socket access** to trusted users only
5. **Use Docker secrets** for sensitive configuration in production

## License

This project is provided as-is for managing Datagram nodes.

## Support

For issues or questions, please check the existing scripts and configuration files in the repository.
