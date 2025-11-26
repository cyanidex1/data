#!/usr/bin/env python3
"""
Docker Control Panel for Datagram Nodes
Web application for managing Docker containers across multiple hosts
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, make_response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import docker
import json
import os
import re
import threading
import time
from datetime import datetime, timedelta
from io import StringIO
import csv

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the control panel.'

# Store Docker hosts configuration
DATA_DIR = os.environ.get('DATA_DIR', '/data')
HOSTS_FILE = os.path.join(DATA_DIR, 'docker_hosts.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
DEFAULT_IMAGE = 'datagram'


class User(UserMixin):
    """User model for authentication"""
    
    def __init__(self, id, username, password_hash, password_changed=False, role='admin', theme='dark'):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.password_changed = password_changed
        self.role = role  # 'viewer', 'editor', 'admin'
        self.theme = theme  # User's theme preference
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def can_view(self):
        return self.role in ['viewer', 'editor', 'admin']
    
    def can_edit(self):
        return self.role in ['editor', 'admin']
    
    def is_admin(self):
        return self.role == 'admin'


class UserManager:
    """Manages user authentication"""
    
    def __init__(self, users_file):
        self.users_file = users_file
        self.users = self.load_users()
        
        # Create default admin user if no users exist
        if not self.users:
            default_username = os.environ.get('ADMIN_USERNAME', 'admin')
            default_password = os.environ.get('ADMIN_PASSWORD', 'admin')
            self.add_user(default_username, default_password, password_changed=False, role='admin')
            print(f"[*] Created default admin user: {default_username} / {default_password}")
            print("[!] IMPORTANT: Change the default password immediately!")
    
    def load_users(self):
        """Load users from configuration file"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    return {u['id']: User(
                        u['id'], 
                        u['username'], 
                        u['password_hash'], 
                        u.get('password_changed', False),
                        u.get('role', 'admin'),
                        u.get('theme', 'dark')
                    ) for u in data}
            except Exception as e:
                print(f"Error loading users: {e}")
                return {}
        return {}
    
    def save_users(self):
        """Save users to configuration file"""
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        data = [{
            'id': user.id, 
            'username': user.username, 
            'password_hash': user.password_hash, 
            'password_changed': user.password_changed,
            'role': user.role,
            'theme': user.theme
        } for user in self.users.values()]
        with open(self.users_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_user(self, username, password, password_changed=False, role='viewer'):
        """Add a new user"""
        user_id = len(self.users) + 1
        password_hash = generate_password_hash(password)
        user = User(user_id, username, password_hash, password_changed, role)
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
            user.password_changed = True
            self.save_users()
            return True
        return False
    
    def delete_user(self, user_id):
        """Delete a user"""
        if user_id in self.users:
            del self.users[user_id]
            self.save_users()
            return True
        return False
    
    def update_user(self, user_id, username=None, password=None, role=None):
        """Update user details"""
        user = self.users.get(user_id)
        if not user:
            return None
        
        if username is not None:
            # Check if username already exists (excluding current user)
            for u in self.users.values():
                if u.username == username and u.id != user_id:
                    return {'error': 'Username already exists'}
            user.username = username
        
        if password is not None:
            user.password_hash = generate_password_hash(password)
            user.password_changed = True
        
        if role is not None:
            if role not in ['viewer', 'editor', 'admin']:
                return {'error': 'Invalid role'}
            user.role = role
        
        self.save_users()
        return user
    
    def update_theme(self, user_id, theme):
        """Update user theme preference"""
        user = self.users.get(user_id)
        if user:
            user.theme = theme
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
    
    def update_host(self, host_id, name=None, url=None, description=None):
        """Update a Docker host"""
        host = self.get_host(host_id)
        if not host:
            return None
        
        if name is not None:
            host['name'] = name
        if url is not None:
            host['url'] = url
        if description is not None:
            host['description'] = description
        
        self.save_hosts()
        return host
    
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
    
    # Check if there are any users with changed passwords
    show_default_creds = all(not user.password_changed for user in user_manager.users.values())
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = user_manager.get_user_by_username(username)
        
        if user and user.check_password(password):
            login_user(user)
            
            # If user hasn't changed password from default, force password change
            if not user.password_changed:
                flash('Please change your password from the default.', 'error')
                return redirect(url_for('change_password', force=True))
            
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html', show_default_creds=show_default_creds)


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
    force = request.args.get('force', 'false').lower() == 'true'
    
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
    
    return render_template('change_password.html', force=force)


@app.route('/admin')
@login_required
def admin_panel():
    """Admin panel page - only accessible to admins"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    return render_template('admin.html', 
                         hosts=host_manager.hosts, 
                         users=list(user_manager.users.values()))


@app.route('/api/users', methods=['GET'])
@login_required
def list_users():
    """List all users - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
    users_list = [{
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'password_changed': user.password_changed
    } for user in user_manager.users.values()]
    
    return jsonify({'users': users_list})


@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    """Create a new user - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'viewer')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    if role not in ['viewer', 'editor', 'admin']:
        return jsonify({'error': 'Invalid role. Must be viewer, editor, or admin'}), 400
    
    # Check if username already exists
    if user_manager.get_user_by_username(username):
        return jsonify({'error': 'Username already exists'}), 400
    
    user = user_manager.add_user(username, password, password_changed=True, role=role)
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    })


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete a user - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
    # Prevent deleting yourself
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    if user_manager.delete_user(user_id):
        return jsonify({'success': True})
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Update a user - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    
    # Validate role if provided
    if role and role not in ['viewer', 'editor', 'admin']:
        return jsonify({'error': 'Invalid role. Must be viewer, editor, or admin'}), 400
    
    # Validate password if provided (must be at least 6 characters)
    if password and len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    # Don't update password if empty string
    if password == '':
        password = None
    
    result = user_manager.update_user(user_id, username=username, password=password, role=role)
    
    if result is None:
        return jsonify({'error': 'User not found'}), 404
    
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 400
    
    return jsonify({
        'success': True,
        'user': {
            'id': result.id,
            'username': result.username,
            'role': result.role
        }
    })


@app.route('/api/theme', methods=['POST'])
@login_required
def update_theme():
    """Update user theme preference"""
    data = request.json
    theme = data.get('theme')
    
    if not theme:
        return jsonify({'error': 'Theme is required'}), 400
    
    if user_manager.update_theme(current_user.id, theme):
        # Reload the user to get updated theme
        current_user.theme = theme
        return jsonify({'success': True, 'theme': theme})
    return jsonify({'error': 'Failed to update theme'}), 500


@app.route('/')
@login_required
def index():
    """Main dashboard page"""
    # Pass user role information to template
    return render_template('index.html', 
                         can_edit=current_user.can_edit(),
                         can_view=current_user.can_view(),
                         is_admin=current_user.is_admin())


@app.route('/api/hosts', methods=['GET'])
@login_required
def list_hosts():
    """List all Docker hosts - editors and admins can view hosts"""
    if not current_user.can_edit():
        return jsonify({'error': 'Edit privileges required'}), 403
    
    return jsonify({'hosts': host_manager.hosts})


@app.route('/api/hosts', methods=['POST'])
@login_required
def add_host():
    """Add a new Docker host - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
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
    """Remove a Docker host - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
    host_manager.remove_host(host_id)
    return jsonify({'success': True})


@app.route('/api/hosts/<int:host_id>', methods=['PUT'])
@login_required
def update_host(host_id):
    """Update a Docker host - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
    data = request.json
    name = data.get('name')
    url = data.get('url')
    description = data.get('description')
    
    # Validate that at least one field is provided
    if name is None and url is None and description is None:
        return jsonify({'error': 'At least one field (name, url, or description) is required'}), 400
    
    result = host_manager.update_host(host_id, name=name, url=url, description=description)
    
    if result is None:
        return jsonify({'error': 'Host not found'}), 404
    
    return jsonify({'success': True, 'host': result})


@app.route('/api/containers', methods=['GET'])
@login_required
def list_containers():
    """List all containers across all hosts - requires view permission"""
    if not current_user.can_view():
        return jsonify({'error': 'View privileges required'}), 403
    
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
                license_key = None
                expiration_date = None
                for env in env_vars:
                    if env.startswith('LICENSE_KEY='):
                        license_key = env.split('=', 1)[1]
                    elif env.startswith('EXPIRATION_DATE='):
                        expiration_date = env.split('=', 1)[1]
                
                # Determine container status
                status = container.status
                if expiration_date:
                    try:
                        exp_dt = datetime.fromisoformat(expiration_date)
                        if datetime.now() > exp_dt:
                            status = 'expired'
                    except:
                        pass
                
                all_containers.append({
                    'host_id': host['id'],
                    'host_name': host['name'],
                    'id': container.id[:12],
                    'name': container.name,
                    'status': status,
                    'image': container.image.tags[0] if container.image.tags else container.image.id[:12],
                    'created': container.attrs['Created'],
                    'key': license_key,
                    'expiration_date': expiration_date
                })
        except Exception as e:
            print(f"Error listing containers on host {host['name']}: {e}")
    
    return jsonify({'containers': all_containers})


@app.route('/api/containers/start', methods=['POST'])
@login_required
def start_container():
    """Start a new container with a given key - requires edit permission"""
    if not current_user.can_edit():
        return jsonify({'error': 'Edit privileges required'}), 403
    
    data = request.json
    host_id = data.get('host_id')
    key = data.get('key')
    expiration_date = data.get('expiration_date')  # Optional expiration date
    
    # Validate key format: 32 characters, only 0-9 and a-z
    if not key or len(key) != 32:
        return jsonify({'error': 'Invalid key. Must be exactly 32 characters'}), 400
    
    if not re.match(r'^[0-9a-z]{32}$', key):
        return jsonify({'error': 'Invalid key. Must contain only numbers (0-9) and lowercase letters (a-z)'}), 400
    
    if host_id is None:
        return jsonify({'error': 'Host ID is required'}), 400
    
    client = host_manager.get_client(host_id)
    if not client:
        return jsonify({'error': 'Could not connect to Docker host'}), 500
    
    try:
        # Use the key as the container name
        container_name = key
        
        # Check if container with this key already exists across all hosts
        for host in host_manager.hosts:
            check_client = host_manager.get_client(host['id'])
            if check_client:
                try:
                    existing_containers = check_client.containers.list(all=True)
                    for c in existing_containers:
                        env_vars = c.attrs.get('Config', {}).get('Env', [])
                        for env in env_vars:
                            if env.startswith('LICENSE_KEY=') and env.split('=', 1)[1] == key:
                                return jsonify({'error': f'Container with key "{key}" already exists on host "{host["name"]}"'}), 400
                except:
                    pass
        
        # Check if image exists, if not return error (user should build it on the host)
        try:
            client.images.get(DEFAULT_IMAGE)
        except docker.errors.ImageNotFound:
            return jsonify({'error': f'Image "{DEFAULT_IMAGE}" not found on host. Please build it first.'}), 400
        
        # Prepare environment variables
        env_vars = {'LICENSE_KEY': key}
        if expiration_date:
            # Validate and store expiration date
            try:
                exp_dt = datetime.fromisoformat(expiration_date)
                env_vars['EXPIRATION_DATE'] = expiration_date
            except:
                return jsonify({'error': 'Invalid expiration date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'}), 400
        
        # Start the container
        container = client.containers.run(
            DEFAULT_IMAGE,
            name=container_name,
            environment=env_vars,
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
    """Start an existing container - requires edit permission"""
    if not current_user.can_edit():
        return jsonify({'error': 'Edit privileges required'}), 403
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
    """Stop a running container - requires edit permission"""
    if not current_user.can_edit():
        return jsonify({'error': 'Edit privileges required'}), 403
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
    """Restart a container - requires edit permission"""
    if not current_user.can_edit():
        return jsonify({'error': 'Edit privileges required'}), 403
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
    """Kill a running container - requires edit permission"""
    if not current_user.can_edit():
        return jsonify({'error': 'Edit privileges required'}), 403
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
    """Remove a container - requires edit permission"""
    if not current_user.can_edit():
        return jsonify({'error': 'Edit privileges required'}), 403
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
    """Get container logs - requires view permission"""
    if not current_user.can_view():
        return jsonify({'error': 'View privileges required'}), 403
    
    try:
        client = host_manager.get_client(int(host_id))
        if not client:
            return jsonify({'error': 'Could not connect to Docker host'}), 500
        
        container = client.containers.get(container_id)
        logs = container.logs(tail=100).decode('utf-8')
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/export-keys', methods=['GET'])
@login_required
def export_keys():
    """Export all container keys to CSV - requires view permission"""
    if not current_user.can_view():
        return jsonify({'error': 'View privileges required'}), 403
    
    try:
        # Collect all keys from all hosts
        all_keys = []
        
        for host in host_manager.hosts:
            client = host_manager.get_client(host['id'])
            if not client:
                continue
            
            try:
                containers = client.containers.list(all=True)
                for container in containers:
                    env_vars = container.attrs.get('Config', {}).get('Env', [])
                    license_key = None
                    expiration_date = None
                    
                    for env in env_vars:
                        if env.startswith('LICENSE_KEY='):
                            license_key = env.split('=', 1)[1]
                        elif env.startswith('EXPIRATION_DATE='):
                            expiration_date = env.split('=', 1)[1]
                    
                    if license_key:
                        all_keys.append({
                            'host': host['name'],
                            'container': container.name,
                            'key': license_key,
                            'status': container.status,
                            'expiration': expiration_date or 'N/A'
                        })
            except Exception as e:
                print(f"Error getting keys from host {host['name']}: {e}")
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Host', 'Container', 'Key', 'Status', 'Expiration'])
        
        for item in all_keys:
            writer.writerow([item['host'], item['container'], item['key'], item['status'], item['expiration']])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=container_keys_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/import-keys', methods=['POST'])
@login_required
def import_keys():
    """Import container keys from CSV - requires edit permission"""
    if not current_user.can_edit():
        return jsonify({'error': 'Edit privileges required'}), 403
    
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Read and parse CSV
        stream = StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)
        
        # Validate headers
        expected_headers = {'Host', 'Container', 'Key', 'Status', 'Expiration'}
        if not expected_headers.issubset(set(reader.fieldnames or [])):
            return jsonify({'error': f'Invalid CSV format. Expected headers: {", ".join(expected_headers)}'}), 400
        
        # Process each row
        results = {
            'success': [],
            'skipped': [],
            'failed': []
        }
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            host_name = row.get('Host', '').strip()
            key = row.get('Key', '').strip()
            expiration = row.get('Expiration', '').strip()
            
            # Validate key
            if not key:
                results['failed'].append({
                    'row': row_num,
                    'key': key,
                    'error': 'Missing key'
                })
                continue
            
            if len(key) != 32 or not re.match(r'^[0-9a-z]{32}$', key):
                results['failed'].append({
                    'row': row_num,
                    'key': key,
                    'error': 'Invalid key format (must be 32 characters, 0-9 and a-z only)'
                })
                continue
            
            # Find host by name
            host = None
            for h in host_manager.hosts:
                if h['name'] == host_name:
                    host = h
                    break
            
            if not host:
                results['failed'].append({
                    'row': row_num,
                    'key': key,
                    'error': f'Host "{host_name}" not found'
                })
                continue
            
            # Check if container already exists
            client = host_manager.get_client(host['id'])
            if not client:
                results['failed'].append({
                    'row': row_num,
                    'key': key,
                    'error': f'Could not connect to host "{host_name}"'
                })
                continue
            
            # Check if container with this key already exists
            exists = False
            try:
                containers = client.containers.list(all=True)
                for c in containers:
                    env_vars = c.attrs.get('Config', {}).get('Env', [])
                    for env in env_vars:
                        if env.startswith('LICENSE_KEY=') and env.split('=', 1)[1] == key:
                            exists = True
                            break
                    if exists:
                        break
            except:
                pass
            
            if exists:
                results['skipped'].append({
                    'row': row_num,
                    'key': key,
                    'reason': 'Container with this key already exists'
                })
                continue
            
            # Check if image exists
            try:
                client.images.get(DEFAULT_IMAGE)
            except docker.errors.ImageNotFound:
                results['failed'].append({
                    'row': row_num,
                    'key': key,
                    'error': f'Image "{DEFAULT_IMAGE}" not found on host "{host_name}"'
                })
                continue
            
            # Prepare environment variables
            env_vars = {'LICENSE_KEY': key}
            if expiration and expiration != 'N/A':
                try:
                    # Try to parse the expiration date
                    exp_dt = datetime.fromisoformat(expiration)
                    env_vars['EXPIRATION_DATE'] = expiration
                except:
                    # If parsing fails, skip expiration date
                    pass
            
            # Start the container
            try:
                container = client.containers.run(
                    DEFAULT_IMAGE,
                    name=key,
                    environment=env_vars,
                    platform='linux/amd64',
                    detach=True,
                    restart_policy={'Name': 'unless-stopped'},
                    mem_limit='100m',
                    memswap_limit='200m'
                )
                
                results['success'].append({
                    'row': row_num,
                    'key': key,
                    'host': host_name,
                    'container_id': container.id[:12]
                })
            except Exception as e:
                results['failed'].append({
                    'row': row_num,
                    'key': key,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'summary': {
                'total': len(results['success']) + len(results['skipped']) + len(results['failed']),
                'imported': len(results['success']),
                'skipped': len(results['skipped']),
                'failed': len(results['failed'])
            },
            'details': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/hosts/<int:host_id>/stats', methods=['GET'])
@login_required
def get_host_stats(host_id):
    """Get host statistics (CPU, RAM, Disk usage)"""
    try:
        client = host_manager.get_client(host_id)
        if not client:
            return jsonify({'error': 'Could not connect to Docker host'}), 500
        
        # Get system info
        info = client.info()
        
        # Get disk usage
        df = client.df()
        
        # Calculate stats
        stats = {
            'cpu': {
                'cores': info.get('NCPU', 0),
            },
            'memory': {
                'total': info.get('MemTotal', 0),
                'total_gb': round(info.get('MemTotal', 0) / (1024**3), 2),
                # Note: Docker info() doesn't provide current memory usage
                # This shows total system memory available to Docker
            },
            'containers': {
                'total': info.get('Containers', 0),
                'running': info.get('ContainersRunning', 0),
                'stopped': info.get('ContainersStopped', 0),
                'paused': info.get('ContainersPaused', 0),
            },
            'images': info.get('Images', 0),
            'docker_version': info.get('ServerVersion', 'Unknown'),
            'os': info.get('OperatingSystem', 'Unknown'),
            'architecture': info.get('Architecture', 'Unknown'),
        }
        
        # Add disk usage if available
        if df:
            volumes_data = df.get('Volumes', [])
            images_data = df.get('Images', [])
            containers_data = df.get('Containers', [])
            
            total_size = 0
            if volumes_data:
                total_size += sum(v.get('UsageData', {}).get('Size', 0) for v in volumes_data if v.get('UsageData'))
            if images_data:
                total_size += sum(i.get('Size', 0) for i in images_data)
            if containers_data:
                total_size += sum(c.get('SizeRw', 0) for c in containers_data)
            
            stats['disk'] = {
                'used_bytes': total_size,
                'used_gb': round(total_size / (1024**3), 2),
            }
        
        return jsonify({'stats': stats})
    except Exception as e:
        print(f"Error getting host stats: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Add local host if no hosts exist
    if not host_manager.hosts:
        host_manager.add_host('Local Docker', 'local', 'Local Docker daemon via socket')
    
    # Start background thread to monitor expired containers
    def monitor_expired_containers():
        """Background thread to stop expired containers and remove old ones"""
        while True:
            try:
                for host in host_manager.hosts:
                    client = host_manager.get_client(host['id'])
                    if not client:
                        continue
                    
                    try:
                        containers = client.containers.list(all=True)
                        for container in containers:
                            env_vars = container.attrs.get('Config', {}).get('Env', [])
                            expiration_date = None
                            
                            for env in env_vars:
                                if env.startswith('EXPIRATION_DATE='):
                                    expiration_date = env.split('=', 1)[1]
                                    break
                            
                            if expiration_date:
                                try:
                                    exp_dt = datetime.fromisoformat(expiration_date)
                                    now = datetime.now()
                                    
                                    # Stop container if expired and still running
                                    if now > exp_dt and container.status == 'running':
                                        print(f"Stopping expired container: {container.name}")
                                        container.stop()
                                    
                                    # Remove container if expired for more than 7 days
                                    removal_date = exp_dt + timedelta(days=7)
                                    if now > removal_date:
                                        print(f"Removing expired container (>7 days): {container.name}")
                                        container.remove(force=True)
                                except Exception as e:
                                    print(f"Error processing expiration for {container.name}: {e}")
                    except Exception as e:
                        print(f"Error monitoring containers on host {host['name']}: {e}")
            except Exception as e:
                print(f"Error in monitor thread: {e}")
            
            # Check every 5 minutes
            time.sleep(300)
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_expired_containers, daemon=True)
    monitor_thread.start()
    print("[*] Started container expiration monitor thread")
    
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('DEBUG', 'False').lower() == 'true')
