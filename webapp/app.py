#!/usr/bin/env python3
"""
Docker Control Panel for Datagram Nodes
Web application for managing Docker containers across multiple hosts
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import docker
import json
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Store Docker hosts configuration
HOSTS_FILE = '/data/docker_hosts.json'
DEFAULT_IMAGE = 'datagram'


class DockerHostManager:
    """Manages connections to multiple Docker hosts"""
    
    def __init__(self, hosts_file):
        self.hosts_file = hosts_file
        self.hosts = self.load_hosts()
        self.next_id = self._get_next_id()
    
    def _get_next_id(self):
        """Get the next available ID"""
        if not self.hosts:
            return 0
        return max(host['id'] for host in self.hosts) + 1
    
    def load_hosts(self):
        """Load Docker hosts from configuration file"""
        if os.path.exists(self.hosts_file):
            try:
                with open(self.hosts_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading hosts: {e}")
                return []
        return []
    
    def save_hosts(self):
        """Save Docker hosts to configuration file"""
        os.makedirs(os.path.dirname(self.hosts_file), exist_ok=True)
        with open(self.hosts_file, 'w') as f:
            json.dump(self.hosts, f, indent=2)
    
    def add_host(self, name, url, description=''):
        """Add a new Docker host"""
        host = {
            'id': len(self.hosts),
            'name': name,
            'url': url,
            'description': description,
            'added_at': datetime.now().isoformat()
        }
        self.hosts.append(host)
        self.save_hosts()
        return host
    
    def add_host(self, name, url, description=''):
        """Add a new Docker host"""
        host = {
            'id': self.next_id,
            'name': name,
            'url': url,
            'description': description,
            'added_at': datetime.now().isoformat()
        }
        self.hosts.append(host)
        self.next_id += 1
        self.save_hosts()
        return host
    
    def remove_host(self, host_id):
        """Remove a Docker host"""
        self.hosts = [h for h in self.hosts if h['id'] != host_id]
        self.save_hosts()
        """Get a specific Docker host"""
        for host in self.hosts:
            if host['id'] == host_id:
                return host
        return None
    
    def get_client(self, host_id):
        """Get Docker client for a specific host"""
        host = self.get_host(host_id)
        if not host:
            return None
        
        try:
            if host['url'] == 'local':
                return docker.from_env()
            else:
                return docker.DockerClient(base_url=host['url'])
        except Exception as e:
            print(f"Error connecting to host {host['name']}: {e}")
            return None


# Initialize host manager
host_manager = DockerHostManager(HOSTS_FILE)


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html', hosts=host_manager.hosts)


@app.route('/api/hosts', methods=['GET'])
def list_hosts():
    """List all Docker hosts"""
    return jsonify({'hosts': host_manager.hosts})


@app.route('/api/hosts', methods=['POST'])
def add_host():
    """Add a new Docker host"""
    data = request.json
    name = data.get('name')
    url = data.get('url')
    description = data.get('description', '')
    
    if not name or not url:
        return jsonify({'error': 'Name and URL are required'}), 400
    
    host = host_manager.add_host(name, url, description)
    return jsonify({'success': True, 'host': host})


@app.route('/api/hosts/<int:host_id>', methods=['DELETE'])
def remove_host(host_id):
    """Remove a Docker host"""
    host_manager.remove_host(host_id)
    return jsonify({'success': True})


@app.route('/api/containers', methods=['GET'])
def list_containers():
    """List all containers across all hosts"""
    all_containers = []
    
    for host in host_manager.hosts:
        client = host_manager.get_client(host['id'])
        if not client:
            continue
        
        try:
            containers = client.containers.list(all=True)
            for container in containers:
                # Get environment variables to extract the key
                env_vars = container.attrs.get('Config', {}).get('Env', [])
                datagram_key = None
                for env in env_vars:
                    if env.startswith('DATAGRAM_KEY='):
                        datagram_key = env.split('=', 1)[1]
                        break
                
                all_containers.append({
                    'host_id': host['id'],
                    'host_name': host['name'],
                    'id': container.id[:12],
                    'name': container.name,
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else container.image.id[:12],
                    'created': container.attrs['Created'],
                    'key': datagram_key
                })
        except Exception as e:
            print(f"Error listing containers on host {host['name']}: {e}")
    
    return jsonify({'containers': all_containers})


@app.route('/api/containers/start', methods=['POST'])
def start_container():
    """Start a new container with a given key"""
    data = request.json
    host_id = data.get('host_id')
    key = data.get('key')
    container_prefix = data.get('container_prefix', 'node')
    
    if not key or len(key) != 32:
        return jsonify({'error': 'Invalid key. Must be 32 characters'}), 400
    
    if host_id is None:
        return jsonify({'error': 'Host ID is required'}), 400
    
    client = host_manager.get_client(host_id)
    if not client:
        return jsonify({'error': 'Could not connect to Docker host'}), 500
    
    try:
        # Find next available container name
        existing_containers = client.containers.list(all=True)
        index = 1
        while True:
            container_name = f"{container_prefix}{index}"
            if not any(c.name == container_name for c in existing_containers):
                break
            index += 1
        
        # Check if image exists, if not return error (user should build it on the host)
        try:
            client.images.get(DEFAULT_IMAGE)
        except docker.errors.ImageNotFound:
            return jsonify({'error': f'Image "{DEFAULT_IMAGE}" not found on host. Please build it first.'}), 400
        
        # Start the container
        container = client.containers.run(
            DEFAULT_IMAGE,
            name=container_name,
            environment={'DATAGRAM_KEY': key},
            platform='linux/amd64',
            detach=True,
            restart_policy={'Name': 'unless-stopped'},
            mem_limit='100m',
            memswap_limit='200m'
        )
        
        return jsonify({
            'success': True,
            'container_id': container.id[:12],
            'container_name': container_name
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/<host_id>/<container_id>/start', methods=['POST'])
def start_existing_container(host_id, container_id):
    """Start an existing container"""
    try:
        client = host_manager.get_client(int(host_id))
        if not client:
            return jsonify({'error': 'Could not connect to Docker host'}), 500
        
        container = client.containers.get(container_id)
        container.start()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/<host_id>/<container_id>/stop', methods=['POST'])
def stop_container(host_id, container_id):
    """Stop a running container"""
    try:
        client = host_manager.get_client(int(host_id))
        if not client:
            return jsonify({'error': 'Could not connect to Docker host'}), 500
        
        container = client.containers.get(container_id)
        container.stop()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/<host_id>/<container_id>/restart', methods=['POST'])
def restart_container(host_id, container_id):
    """Restart a container"""
    try:
        client = host_manager.get_client(int(host_id))
        if not client:
            return jsonify({'error': 'Could not connect to Docker host'}), 500
        
        container = client.containers.get(container_id)
        container.restart()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/<host_id>/<container_id>/kill', methods=['POST'])
def kill_container(host_id, container_id):
    """Kill a running container"""
    try:
        client = host_manager.get_client(int(host_id))
        if not client:
            return jsonify({'error': 'Could not connect to Docker host'}), 500
        
        container = client.containers.get(container_id)
        container.kill()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/<host_id>/<container_id>/remove', methods=['DELETE'])
def remove_container(host_id, container_id):
    """Remove a container"""
    try:
        client = host_manager.get_client(int(host_id))
        if not client:
            return jsonify({'error': 'Could not connect to Docker host'}), 500
        
        container = client.containers.get(container_id)
        container.remove(force=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/<host_id>/<container_id>/logs', methods=['GET'])
def get_container_logs(host_id, container_id):
    """Get container logs"""
    try:
        client = host_manager.get_client(int(host_id))
        if not client:
            return jsonify({'error': 'Could not connect to Docker host'}), 500
        
        container = client.containers.get(container_id)
        logs = container.logs(tail=100).decode('utf-8')
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs('/data', exist_ok=True)
    
    # Add local host if no hosts exist
    if not host_manager.hosts:
        host_manager.add_host('Local Docker', 'local', 'Local Docker daemon via socket')
    
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('DEBUG', 'False').lower() == 'true')
