# Datagram Node Control Panel

Web-based control panel for managing Docker containers running Datagram nodes across multiple hosts.

![Control Panel Screenshot](https://github.com/user-attachments/assets/56856c2c-0b96-4104-ad49-869eaf15f998)

## Quick Start

```bash
docker build --platform linux/amd64 -t datagram datagram/ && docker compose up -d
```

Access the web interface at **http://localhost:5000** (default credentials: `admin/admin`)

**Note:** Containers download VPN/Conference CLI binaries on first run (~30-60 seconds).

## Features

- 🚀 Start/stop/restart containers with 32-character keys
- 📊 Monitor all containers across multiple Docker hosts in real-time
- 🖥️ Multi-host management from a single interface
- 📦 Bulk operations on multiple containers
- 📝 View container logs
- 🔄 Auto-refresh every 10 seconds
- ⚡ Optimized for managing 100+ containers

## Usage

### Start a Container

**Web Interface:** Select host → Enter 32-char key → Click "Start Container"

**Command Line:**
```bash
./datagram/start.sh <32-char-key> node
```

**API:**
```bash
curl -X POST http://localhost:5000/api/containers/start \
  -H "Content-Type: application/json" \
  -d '{"host_id": 0, "key": "<your-key>", "container_prefix": "node"}'
```

### Add Remote Host

1. Click "➕ Add Host"
2. Enter name and URL: `tcp://hostname:2375`
3. Configure Docker daemon on remote host to accept connections

⚠️ **Security:** Use TLS for remote connections in production.

## Configuration

### Environment Variables
- `SECRET_KEY`: Flask secret key (required for production)
- `DEBUG`: Debug mode (`True`/`False`)
- `ADMIN_USERNAME`: Admin username (default: `admin`)
- `ADMIN_PASSWORD`: Admin password (default: `admin`)
- `CONTAINER_ULIMIT`: File descriptor limit per container (default: `8192`)

### API Endpoints

**Hosts:**
- `GET /api/hosts` - List hosts
- `POST /api/hosts` - Add host
- `DELETE /api/hosts/<id>` - Remove host

**Containers:**
- `GET /api/containers` - List all containers
- `POST /api/containers/start` - Start new container
- `POST /api/containers/<host_id>/<container_id>/{start,stop,restart,kill}` - Container operations
- `DELETE /api/containers/<host_id>/<container_id>/remove` - Remove container
- `GET /api/containers/<host_id>/<container_id>/logs` - Get logs

## Troubleshooting

### "Too many open files" error
Default ulimit is 8,192 file descriptors (supports 500+ containers). If needed, increase with:
```bash
export CONTAINER_ULIMIT=16384
docker compose up -d
```

### Cannot connect to Docker daemon
Ensure Docker socket is mounted: `-v /var/run/docker.sock:/var/run/docker.sock`

### Image 'datagram' not found
Build the image first: `docker build --platform linux/amd64 -t datagram datagram/`

## Security

⚠️ **Production Setup:**
1. Change default credentials (`admin/admin`)
2. Set strong `SECRET_KEY`: `export SECRET_KEY=$(openssl rand -hex 32)`
3. Use TLS for remote Docker connections
4. Restrict network access with firewall/reverse proxy
5. Set `DEBUG=False`

## License

This project is provided as-is for managing Datagram nodes.
