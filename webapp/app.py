#!/usr/bin/env python3
"""
Docker Control Panel for Datagram Nodes
Web application for managing Docker containers across multiple hosts
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import docker
import json
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the control panel.'

# Store Docker hosts configuration
HOSTS_FILE = '/data/docker_hosts.json'
USERS_FILE = '/data/users.json'
DEFAULT_IMAGE = 'datagram'


class User(UserMixin):
    """User model for authentication"""
    
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class UserManager:
    """Manages user authentication"""
    
    def __init__(self, users_file):
        self.users_file = users_file
        self.users = self.load_users()
        
        # Create default admin user if no users exist
        if not self.users:
            default_username = os.environ.get('ADMIN_USERNAME', 'admin')
            default_password = os.environ.get('ADMIN_PASSWORD', 'admin')
            self.add_user(default_username, default_password)
            print(f"[*] Created default admin user: {default_username} / {default_password}")
            print("[!] IMPORTANT: Change the default password immediately!")
    
    def load_users(self):
        """Load users from configuration file"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    return {u['id']: User(u['id'], u['username'], u['password_hash']) for u in data}
            except Exception as e:
                print(f"Error loading users: {e}")
                return {}
        return {}
    
    def save_users(self):
        """Save users to configuration file"""
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        data = [{'id': user.id, 'username': user.username, 'password_hash': user.password_hash} 
                for user in self.users.values()]
        with open(self.users_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_user(self, username, password):
        """Add a new user"""
        user_id = len(self.users) + 1
        password_hash = generate_password_hash(password)
        user = User(user_id, username, password_hash)
        self.users[user_id] = user
        self.save_users()
        return user
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username):
        """Get user by username"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def change_password(self, user_id, new_password):
        """Change user password"""
        user = self.users.get(user_id)
        if user:
            user.password_hash = generate_password_hash(new_password)
            self.save_users()
            return True
        return False


# Initialize user manager
user_manager = UserManager(USERS_FILE)


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return user_manager.get_user_by_id(int(user_id))


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
    
    def get_host(self, host_id):
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = user_manager.get_user_by_username(username)
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match', 'error')
        elif len(new_password) < 6:
            flash('Password must be at least 6 characters', 'error')
        else:
            user_manager.change_password(current_user.id, new_password)
            flash('Password changed successfully', 'success')
            return redirect(url_for('index'))
    
    return render_template('change_password.html')


@app.route('/')
@login_required
def index():
    """Main dashboard page"""
    return render_template('index.html', hosts=host_manager.hosts)


@app.route('/api/hosts', methods=['GET'])
@login_required
def list_hosts():
    """List all Docker hosts"""
    return jsonify({'hosts': host_manager.hosts})


@app.route('/api/hosts', methods=['POST'])
@login_required
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
@login_required
def remove_host(host_id):
    """Remove a Docker host"""
    host_manager.remove_host(host_id)
    return jsonify({'success': True})


@app.route('/api/containers', methods=['GET'])
@login_required
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
@login_required
def start_container():
    """Start a new container with a given key"""
    data = request.json
    host_id = data.get('host_id')
    key = data.get('key')
    
    if not key or len(key) != 32:
        return jsonify({'error': 'Invalid key. Must be 32 characters'}), 400
    
    if host_id is None:
        return jsonify({'error': 'Host ID is required'}), 400
    
    client = host_manager.get_client(host_id)
    if not client:
        return jsonify({'error': 'Could not connect to Docker host'}), 500
    
    try:
        # Use the key as the container name
        container_name = key
        
        # Check if container with this name already exists
        existing_containers = client.containers.list(all=True)
        if any(c.name == container_name for c in existing_containers):
            return jsonify({'error': f'Container with key "{key}" already exists'}), 400
        
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
