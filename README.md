# Datagram Node Control Panel

A web-based control panel for managing Docker containers running Datagram nodes across multiple Docker hosts.

![Control Panel Screenshot](https://github.com/user-attachments/assets/87489b65-e330-411d-ab3b-15f8a3e1b131)

## 🚀 Getting Started in 3 Steps

### Step 1: Build the Datagram Image
```bash
docker build --platform linux/amd64 -t datagram .
```

### Step 2: Start the Control Panel
```bash
docker compose up -d
```

### Step 3: Access the Web Interface
Open your browser and go to: **http://localhost:5000**

That's it! You can now start managing your Datagram nodes through the web interface.

## Features

- 🚀 **Start Containers**: Enter a 32-character key and start a new Datagram node container
- 📊 **Monitor Containers**: View all running containers across multiple hosts in real-time
- 🖥️ **Multi-Host Management**: Add and manage multiple Docker hosts from a single interface
- 🎮 **Container Operations**: Start, stop, restart, kill, and remove containers
- 📝 **View Logs**: Check container logs directly from the web interface
- 🔄 **Auto-Refresh**: Dashboard automatically refreshes every 10 seconds
- 🐳 **Docker Integration**: Works seamlessly with the existing `unhealthy.sh` cron job

## Detailed Installation Guide

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

## 📖 Usage Guide

### Starting a New Container

**Via Web Interface:**
1. Select a Docker host from the dropdown (e.g., "Local Docker")
2. Enter your 32-character Datagram key (e.g., `92bcf2ae4e326968f40f8670a3596b80`)
3. (Optional) Change the container name prefix from `node` to something else
4. Click "Start Container"

The control panel will automatically find the next available container name (e.g., `node1`, `node2`, etc.)

**Via Command Line (existing method still works):**
```bash
./start.sh 92bcf2ae4e326968f40f8670a3596b80 node
```

**Via API:**
```bash
curl -X POST http://localhost:5000/api/containers/start \
  -H "Content-Type: application/json" \
  -d '{
    "host_id": 0,
    "key": "92bcf2ae4e326968f40f8670a3596b80",
    "container_prefix": "node"
  }'
```

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

From the Running Containers table, you can perform these operations with a single click:
- **Start**: Start a stopped container
- **Stop**: Gracefully stop a running container (sends SIGTERM)
- **Restart**: Restart a container (useful for applying changes)
- **Kill**: Forcefully stop a container (sends SIGKILL)
- **Remove**: Delete a container permanently (cannot be undone)
- **Logs**: View the last 100 lines of container logs

**Example Workflow:**
1. Start multiple nodes with different keys
2. Monitor their status in real-time
3. Check logs if a node is misbehaving
4. Restart unhealthy nodes
5. Remove old/unused containers

### Managing Multiple Containers

**Best Practices:**
- Use descriptive prefixes for different environments (e.g., `prod-`, `test-`)
- Keep track of which keys are used for which containers
- Regularly check the logs to ensure nodes are running correctly
- Use the auto-refresh feature to monitor container health

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

## 💡 Complete Example

Here's a complete workflow from installation to running multiple nodes:

```bash
# 1. Clone the repository (if not already done)
cd /path/to/data

# 2. Build the datagram image
docker build --platform linux/amd64 -t datagram .

# 3. Start the control panel
docker compose up -d

# 4. Check that the control panel is running
docker ps | grep datagram-control-panel

# 5. Open the web interface
# Navigate to http://localhost:5000 in your browser

# 6. Start your first node
# - Select "Local Docker" from the host dropdown
# - Enter your 32-char key: 92bcf2ae4e326968f40f8670a3596b80
# - Click "Start Container"

# 7. Monitor the logs
# Click the "Logs" button next to the container to see its output

# 8. Start additional nodes with different keys
# Repeat step 6 with different keys for each node

# 9. (Optional) Stop the control panel when done
docker compose down
```

### Example API Usage

Start 3 containers programmatically:
```bash
for i in {1..3}; do
  curl -X POST http://localhost:5000/api/containers/start \
    -H "Content-Type: application/json" \
    -d "{\"host_id\": 0, \"key\": \"$(openssl rand -hex 16)\", \"container_prefix\": \"node\"}"
  echo ""
done
```

List all running containers:
```bash
curl -s http://localhost:5000/api/containers | python3 -m json.tool
```

Stop a specific container:
```bash
curl -X POST http://localhost:5000/api/containers/0/node1/stop
```

## 🔧 Advanced Configuration

### Custom Port
To run the control panel on a different port, edit `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Access via http://localhost:8080
```

### Remote Docker Host Setup
On your remote server (e.g., production server):
```bash
# Edit Docker daemon configuration
sudo nano /etc/docker/daemon.json

# Add:
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}

# Restart Docker
sudo systemctl restart docker

# Allow firewall access (adjust IP as needed)
sudo ufw allow from 192.168.1.0/24 to any port 2375
```

Then in the web interface:
1. Click "➕ Add Host"
2. Name: "Production Server"
3. URL: `tcp://192.168.1.100:2375`
4. Click "Add Host"

### Production Deployment

For production use, consider:
1. Use a reverse proxy (nginx/Caddy) with HTTPS
2. Set a strong SECRET_KEY environment variable
3. Use Docker TLS for remote connections
4. Implement authentication (add to the Flask app)
5. Use proper logging and monitoring

Example with nginx:
```nginx
server {
    listen 443 ssl;
    server_name nodes.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## License

This project is provided as-is for managing Datagram nodes.

## Support

For issues or questions, please check the existing scripts and configuration files in the repository.

---

**Need help?** Check the [QUICKSTART.md](QUICKSTART.md) for a condensed guide, or review the troubleshooting section above.
