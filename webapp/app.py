#!/usr/bin/env python3
"""
Docker Control Panel for Datagram Nodes
Web application for managing Docker containers across multiple hosts
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, make_response, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import docker
import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
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
TAILSCALE_CONFIG_FILE = os.path.join(DATA_DIR, 'tailscale_config.json')
DEFAULT_IMAGE = 'datagram'

# Node type configurations
NODE_TYPES = {
    'datagram': {
        'name': 'Datagram',
        'description': 'Datagram CLI node using API key',
        'image': 'datagram',
        'auth_type': 'api_key',  # Uses LICENSE_KEY
        'dockerfile': 'datagram.Dockerfile',
        'env_vars': ['LICENSE_KEY']
    },
    'element': {
        'name': 'Element',
        'description': 'Element United node',
        'image': 'element-node',
        'auth_type': 'email_password',  # Uses email/password
        'dockerfile': 'element.Dockerfile',
        'env_vars': ['NODE_EMAIL', 'NODE_PASSWORD', 'NODE_NAME']
    },
    'elevate': {
        'name': 'Elevate',
        'description': 'Elevate United node',
        'image': 'elevate-node',
        'auth_type': 'email_password',
        'dockerfile': 'elevate.Dockerfile',
        'env_vars': ['NODE_EMAIL', 'NODE_PASSWORD', 'NODE_NAME']
    },
    'grow': {
        'name': 'Grow',
        'description': 'Grow Blockchain node',
        'image': 'grow-node',
        'auth_type': 'email_password',
        'dockerfile': 'grow.Dockerfile',
        'env_vars': ['NODE_EMAIL', 'NODE_PASSWORD', 'NODE_NAME']
    },
    'revo': {
        'name': 'Revo',
        'description': 'RevoRide node',
        'image': 'revo-node',
        'auth_type': 'email_password',
        'dockerfile': 'revo.Dockerfile',
        'env_vars': ['NODE_EMAIL', 'NODE_PASSWORD', 'NODE_NAME']
    },
    'rlink': {
        'name': 'RLink',
        'description': 'RLink Rally node',
        'image': 'rlink-node',
        'auth_type': 'email_password',
        'dockerfile': 'rlink.Dockerfile',
        'env_vars': ['NODE_EMAIL', 'NODE_PASSWORD', 'NODE_NAME']
    },
    'switch': {
        'name': 'Switch',
        'description': 'Switch Reward Card node',
        'image': 'switch-node',
        'auth_type': 'email_password',
        'dockerfile': 'switch.Dockerfile',
        'env_vars': ['NODE_EMAIL', 'NODE_PASSWORD', 'NODE_NAME']
    },
    'win': {
        'name': 'Win',
        'description': 'Win node',
        'image': 'win-node',
        'auth_type': 'email_password',
        'dockerfile': 'win.Dockerfile',
        'env_vars': ['NODE_EMAIL', 'NODE_PASSWORD', 'NODE_NAME']
    }
}


def is_expired(expiration_date_str):
    """
    Check if a container has expired based on its expiration date string.
    Handles both timezone-aware and timezone-naive datetime strings.
    
    Args:
        expiration_date_str: ISO format datetime string (e.g., '2024-11-26T20:26:10.313Z')
    
    Returns:
        bool: True if expired, False otherwise
    """
    try:
        exp_dt = datetime.fromisoformat(expiration_date_str)
        # Use UTC time if expiration date has timezone info, otherwise use local time
        if exp_dt.tzinfo is not None:
            now = datetime.now(timezone.utc)
        else:
            now = datetime.now()
        return now > exp_dt
    except (ValueError, TypeError):
        return False


def is_past_removal_date(expiration_date_str, days=7):
    """
    Check if a container is past its removal date (expiration + N days).
    Handles both timezone-aware and timezone-naive datetime strings.
    
    Args:
        expiration_date_str: ISO format datetime string
        days: Number of days after expiration before removal (default: 7)
    
    Returns:
        bool: True if past removal date, False otherwise
    """
    try:
        exp_dt = datetime.fromisoformat(expiration_date_str)
        removal_date = exp_dt + timedelta(days=days)
        # Use UTC time if expiration date has timezone info, otherwise use local time
        if exp_dt.tzinfo is not None:
            now = datetime.now(timezone.utc)
        else:
            now = datetime.now()
        return now > removal_date
    except (ValueError, TypeError):
        return False


def find_unique_container_name(client, base_name):
    """
    Find a unique container name by appending a number suffix.
    If the base_name already ends with a number suffix (e.g., 'element-user-1'),
    it strips the existing number and finds the next available number.
    
    Args:
        client: Docker client instance
        base_name: Base container name (e.g., 'element-user' or 'element-user-1')
    
    Returns:
        str: Unique container name (e.g., 'element-user-1', 'element-user-2')
    """
    # Strip existing number suffix if present (e.g., 'element-user-1' -> 'element-user')
    # Match pattern: name ending with -<number>
    match = re.match(r'^(.+)-(\d+)$', base_name)
    if match:
        base_name = match.group(1)  # Use the part before the number
    
    counter = 1
    while True:
        container_name = f'{base_name}-{counter}'
        try:
            client.containers.get(container_name)
            counter += 1
        except docker.errors.NotFound:
            return container_name


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


class TailscaleManager:
    """Manages Tailscale VPN connection"""
    
    TAILSCALE_SOCKET = '/var/run/tailscale/tailscaled.sock'
    
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """Load Tailscale configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading Tailscale config: {e}")
                return {}
        return {}
    
    def save_config(self, auth_key=None, hostname=None):
        """Save Tailscale configuration to file"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        if auth_key is not None:
            self.config['auth_key'] = auth_key
        if hostname is not None:
            self.config['hostname'] = hostname
        self.config['updated_at'] = datetime.now().isoformat()
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_saved_auth_key(self):
        """Get saved auth key from config"""
        return self.config.get('auth_key')
    
    def auto_connect(self):
        """Attempt to auto-connect using saved auth key if not already connected"""
        status = self.get_status()
        if status.get('connected'):
            return {'success': True, 'message': 'Already connected'}
        
        auth_key = self.get_saved_auth_key()
        if not auth_key:
            return {'success': False, 'message': 'No saved auth key'}
        
        hostname = self.config.get('hostname')
        return self.connect(auth_key, hostname, save_key=False)
    
    def _run_tailscale_cmd(self, args, timeout=30):
        """Run a tailscale command and return output"""
        cmd = ['tailscale', f'--socket={self.TAILSCALE_SOCKET}'] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out',
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    def get_status(self):
        """Get current Tailscale status"""
        result = self._run_tailscale_cmd(['status', '--json'])
        
        if result['success']:
            try:
                status_data = json.loads(result['stdout'])
                return {
                    'connected': status_data.get('BackendState') == 'Running',
                    'backend_state': status_data.get('BackendState', 'Unknown'),
                    'tailscale_ip': status_data.get('TailscaleIPs', ['N/A'])[0] if status_data.get('TailscaleIPs') else 'N/A',
                    'hostname': status_data.get('Self', {}).get('HostName', 'N/A'),
                    'dns_name': status_data.get('Self', {}).get('DNSName', 'N/A'),
                    'online': status_data.get('Self', {}).get('Online', False),
                    'peers': len(status_data.get('Peer') or {}),
                    'raw': status_data
                }
            except json.JSONDecodeError:
                return {
                    'connected': False,
                    'backend_state': 'Unknown',
                    'error': 'Failed to parse status JSON'
                }
        else:
            # Check if the error indicates not logged in
            if 'not logged in' in result['stderr'].lower() or 'needslogin' in result['stderr'].lower():
                return {
                    'connected': False,
                    'backend_state': 'NeedsLogin',
                    'message': 'Not connected to Tailscale network'
                }
            return {
                'connected': False,
                'backend_state': 'Error',
                'error': result['stderr'] or 'Failed to get status'
            }
    
    def connect(self, auth_key, hostname=None, save_key=True):
        """Connect to Tailscale network using auth key"""
        if not auth_key:
            return {'success': False, 'error': 'Auth key is required'}
        
        # Validate auth key format (tskey-auth-xxx or tskey-xxx)
        if not re.match(r'^tskey-[a-zA-Z0-9-]+$', auth_key):
            return {'success': False, 'error': 'Invalid auth key format. Should start with "tskey-"'}
        
        # Build the command
        args = ['up', f'--authkey={auth_key}', '--accept-routes']
        
        if hostname:
            # Sanitize hostname - replace invalid chars, remove consecutive hyphens
            hostname = re.sub(r'[^a-zA-Z0-9-]', '-', hostname)
            hostname = re.sub(r'-+', '-', hostname).strip('-')[:63]
            if hostname:
                args.append(f'--hostname={hostname}')
        
        result = self._run_tailscale_cmd(args, timeout=60)
        
        if result['success']:
            # Save auth key and hostname for reconnection on restart
            if save_key:
                self.save_config(auth_key=auth_key, hostname=hostname)
            else:
                self.save_config(hostname=hostname)
            return {
                'success': True,
                'message': 'Successfully connected to Tailscale network'
            }
        else:
            return {
                'success': False,
                'error': result['stderr'] or 'Failed to connect to Tailscale'
            }
    
    def disconnect(self):
        """Disconnect from Tailscale network"""
        result = self._run_tailscale_cmd(['down'])
        
        if result['success']:
            return {
                'success': True,
                'message': 'Successfully disconnected from Tailscale network'
            }
        else:
            return {
                'success': False,
                'error': result['stderr'] or 'Failed to disconnect from Tailscale'
            }
    
    def logout(self):
        """Logout from Tailscale (removes device from account)"""
        result = self._run_tailscale_cmd(['logout'])
        
        if result['success']:
            # Clear saved config
            self.config = {}
            self.save_config()
            return {
                'success': True,
                'message': 'Successfully logged out from Tailscale'
            }
        else:
            return {
                'success': False,
                'error': result['stderr'] or 'Failed to logout from Tailscale'
            }


# Initialize Tailscale manager
tailscale_manager = TailscaleManager(TAILSCALE_CONFIG_FILE)

# Attempt auto-connect to Tailscale if auth key is saved
def _try_tailscale_auto_connect():
    """Try to auto-connect to Tailscale on startup"""
    try:
        result = tailscale_manager.auto_connect()
        if result.get('success'):
            print("[*] Tailscale auto-connect: Already connected or reconnected successfully")
        elif result.get('message') == 'No saved auth key':
            print("[*] Tailscale auto-connect: No saved auth key, manual connection required")
        else:
            print(f"[!] Tailscale auto-connect failed: {result.get('error', result.get('message', 'Unknown error'))}")
    except Exception as e:
        print(f"[!] Tailscale auto-connect error: {e}")

# Run auto-connect in a background thread to not block startup
threading.Thread(target=_try_tailscale_auto_connect, daemon=True).start()


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


@app.route('/api/node-types', methods=['GET'])
@login_required
def get_node_types():
    """Get available node types configuration"""
    if not current_user.can_view():
        return jsonify({'error': 'View privileges required'}), 403
    
    # Return node types with their metadata (without internal details)
    node_types_info = {
        key: {
            'name': config['name'],
            'description': config['description'],
            'auth_type': config['auth_type'],
            'image': config['image']
        }
        for key, config in NODE_TYPES.items()
    }
    
    return jsonify({'node_types': node_types_info})


@app.route('/')
@login_required
def index():
    """Main dashboard page"""
    # Pass user role information to template
    return render_template('index.html', 
                         can_edit=current_user.can_edit(),
                         can_view=current_user.can_view(),
                         is_admin=current_user.is_admin())


@app.route('/favicon.ico')
def favicon():
    """Serve favicon.ico from static folder"""
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.png', mimetype='image/png')


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


# Tailscale API Endpoints
@app.route('/api/tailscale/status', methods=['GET'])
@login_required
def tailscale_status():
    """Get Tailscale connection status - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
    status = tailscale_manager.get_status()
    return jsonify({'status': status})


@app.route('/api/tailscale/connect', methods=['POST'])
@login_required
def tailscale_connect():
    """Connect to Tailscale network - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
    data = request.json
    auth_key = data.get('auth_key')
    hostname = data.get('hostname')
    
    if not auth_key:
        return jsonify({'error': 'Auth key is required'}), 400
    
    result = tailscale_manager.connect(auth_key, hostname)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@app.route('/api/tailscale/disconnect', methods=['POST'])
@login_required
def tailscale_disconnect():
    """Disconnect from Tailscale network - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
    result = tailscale_manager.disconnect()
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@app.route('/api/tailscale/logout', methods=['POST'])
@login_required
def tailscale_logout():
    """Logout from Tailscale (removes device) - admin only"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin privileges required'}), 403
    
    result = tailscale_manager.logout()
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


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
                # Get environment variables to extract credentials
                env_vars = container.attrs.get('Config', {}).get('Env', [])
                license_key = None
                expiration_date = None
                node_type = None
                node_email = None
                
                for env in env_vars:
                    if env.startswith('LICENSE_KEY='):
                        license_key = env.split('=', 1)[1]
                    elif env.startswith('EXPIRATION_DATE='):
                        expiration_date = env.split('=', 1)[1]
                    elif env.startswith('NODE_TYPE='):
                        node_type = env.split('=', 1)[1]
                    elif env.startswith('NODE_EMAIL='):
                        node_email = env.split('=', 1)[1]
                
                # Determine container status
                status = container.status
                if expiration_date and is_expired(expiration_date):
                    status = 'expired'
                
                all_containers.append({
                    'host_id': host['id'],
                    'host_name': host['name'],
                    'id': container.id[:12],
                    'name': container.name,
                    'status': status,
                    'image': container.image.tags[0] if container.image.tags else container.image.id[:12],
                    'created': container.attrs['Created'],
                    'key': license_key,
                    'email': node_email,
                    'node_type': node_type,
                    'expiration_date': expiration_date
                })
        except Exception as e:
            print(f"Error listing containers on host {host['name']}: {e}")
    
    return jsonify({'containers': all_containers})


@app.route('/api/containers/start', methods=['POST'])
@login_required
def start_container():
    """Start a new container - requires edit permission"""
    if not current_user.can_edit():
        return jsonify({'error': 'Edit privileges required'}), 403
    
    data = request.json
    host_id = data.get('host_id')
    node_type = data.get('node_type', 'datagram')
    expiration_date = data.get('expiration_date')
    container_name = data.get('container_name')
    
    # Validate node type
    if node_type not in NODE_TYPES:
        return jsonify({'error': f'Invalid node type: {node_type}'}), 400
    
    node_config = NODE_TYPES[node_type]
    
    if host_id is None:
        return jsonify({'error': 'Host ID is required'}), 400
    
    client = host_manager.get_client(host_id)
    if not client:
        return jsonify({'error': 'Could not connect to Docker host'}), 500
    
    # Prepare environment variables based on auth type
    env_vars = {}
    
    if node_config['auth_type'] == 'api_key':
        # Datagram uses LICENSE_KEY
        key = data.get('key')
        if not key or len(key) != 32:
            return jsonify({'error': 'Invalid key. Must be exactly 32 characters'}), 400
        if not re.match(r'^[0-9a-z]{32}$', key):
            return jsonify({'error': 'Invalid key. Must contain only numbers (0-9) and lowercase letters (a-z)'}), 400
        env_vars['LICENSE_KEY'] = key
        if not container_name:
            container_name = key
    else:
        # Email/password authentication
        email = data.get('email')
        password = data.get('password')
        node_name = data.get('node_name', f'{node_type}-node')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        env_vars['NODE_EMAIL'] = email
        env_vars['NODE_PASSWORD'] = password
        if 'NODE_NAME' in node_config['env_vars']:
            env_vars['NODE_NAME'] = node_name
        
        if not container_name:
            # Generate container name from email prefix and node type
            email_prefix = email.split('@')[0][:16]
            # Sanitize: only allow alphanumeric and hyphens
            email_prefix = re.sub(r'[^a-zA-Z0-9]', '-', email_prefix).lower()
            # Remove consecutive hyphens
            email_prefix = re.sub(r'-+', '-', email_prefix).strip('-')
            container_name = f'{node_type}-{email_prefix}'
    
    # Sanitize container name and remove consecutive hyphens
    container_name = re.sub(r'[^a-zA-Z0-9_.-]', '-', container_name)
    container_name = re.sub(r'-+', '-', container_name).strip('-')
    
    # Add expiration date if provided
    if expiration_date:
        try:
            datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
            env_vars['EXPIRATION_DATE'] = expiration_date
        except (ValueError, AttributeError):
            return jsonify({'error': 'Invalid expiration date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'}), 400
    
    # Store node type for identification
    env_vars['NODE_TYPE'] = node_type
    
    try:
        # For api_key nodes (datagram), check if container already exists (no duplicates allowed)
        # For email/password nodes, always add numbering to allow multiple instances
        if node_config['auth_type'] == 'api_key':
            try:
                existing = client.containers.get(container_name)
                return jsonify({'error': f'Container with name "{container_name}" already exists'}), 400
            except docker.errors.NotFound:
                pass
        else:
            # For non-datagram nodes, always add numbering (-1, -2, -3, etc.)
            container_name = find_unique_container_name(client, container_name)
        
        # Check if image exists
        image_name = node_config['image']
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            return jsonify({'error': f'Image "{image_name}" not found on host. Please build it first.'}), 400
        
        # Start the container
        container = client.containers.run(
            image_name,
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
            'container_name': container_name,
            'node_type': node_type
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


@app.route('/api/containers/<host_id>/<container_id>/update-expiration', methods=['POST'])
@login_required
def update_container_expiration(host_id, container_id):
    """Update container expiration date - requires edit permission
    
    This recreates the container with the updated expiration date environment variable.
    """
    if not current_user.can_edit():
        return jsonify({'error': 'Edit privileges required'}), 403
    
    data = request.json
    expiration_date = data.get('expiration_date')
    
    try:
        client = host_manager.get_client(int(host_id))
        if not client:
            return jsonify({'error': 'Could not connect to Docker host'}), 500
        
        container = client.containers.get(container_id)
        
        # Get current container configuration
        config = container.attrs.get('Config', {})
        env_vars = config.get('Env', [])
        # Safely get image name - check if tags list has items
        if container.image.tags and len(container.image.tags) > 0:
            image = container.image.tags[0]
        else:
            image = container.image.id
        container_name = container.name
        
        # Parse existing environment variables
        new_env = {}
        for env in env_vars:
            if '=' in env:
                key, value = env.split('=', 1)
                new_env[key] = value
        
        # Update or remove expiration date
        if expiration_date:
            try:
                # Validate the expiration date format
                datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
                new_env['EXPIRATION_DATE'] = expiration_date
            except (ValueError, AttributeError):
                return jsonify({'error': 'Invalid expiration date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        else:
            # Remove expiration date if empty (set to never expire)
            new_env.pop('EXPIRATION_DATE', None)
        
        # Get host config for restart policy
        host_config = container.attrs.get('HostConfig', {})
        restart_policy = host_config.get('RestartPolicy', {'Name': 'unless-stopped'})
        mem_limit = host_config.get('Memory', 104857600)  # 100MB default
        memswap_limit = host_config.get('MemorySwap', 209715200)  # 200MB default
        
        # Stop and remove the old container
        was_running = container.status == 'running'
        container.remove(force=True)
        
        # Create new container with updated expiration date
        new_container = client.containers.run(
            image,
            name=container_name,
            environment=new_env,
            platform='linux/amd64',
            detach=True,
            restart_policy=restart_policy,
            mem_limit=mem_limit,
            memswap_limit=memswap_limit
        )
        
        # If the original container was not running, stop the new one
        if not was_running:
            new_container.stop()
        
        return jsonify({
            'success': True,
            'container_id': new_container.id[:12],
            'expiration_date': expiration_date if expiration_date else None
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/export-keys', methods=['GET'])
@login_required
def export_keys():
    """Export all container credentials to CSV - requires view permission"""
    if not current_user.can_view():
        return jsonify({'error': 'View privileges required'}), 403
    
    try:
        # Collect all credentials from all hosts
        all_credentials = []
        
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
                    node_type = None
                    node_email = None
                    node_password = None
                    node_name = None
                    
                    for env in env_vars:
                        if env.startswith('LICENSE_KEY='):
                            license_key = env.split('=', 1)[1]
                        elif env.startswith('EXPIRATION_DATE='):
                            expiration_date = env.split('=', 1)[1]
                        elif env.startswith('NODE_TYPE='):
                            node_type = env.split('=', 1)[1]
                        elif env.startswith('NODE_EMAIL='):
                            node_email = env.split('=', 1)[1]
                        elif env.startswith('NODE_PASSWORD='):
                            node_password = env.split('=', 1)[1]
                        elif env.startswith('NODE_NAME='):
                            node_name = env.split('=', 1)[1]
                    
                    # Only export containers with credentials
                    if license_key or node_email:
                        all_credentials.append({
                            'host': host['name'],
                            'container': container.name,
                            'node_type': node_type or 'datagram',
                            'key': license_key or '',
                            'email': node_email or '',
                            'password': node_password or '',
                            'node_name': node_name or '',
                            'status': container.status,
                            'expiration': expiration_date or 'N/A'
                        })
            except Exception as e:
                print(f"Error getting credentials from host {host['name']}: {e}")
        
        # Create CSV with new format supporting all node types
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Host', 'Container', 'NodeType', 'Key', 'Email', 'Password', 'NodeName', 'Status', 'Expiration'])
        
        for item in all_credentials:
            writer.writerow([
                item['host'], 
                item['container'], 
                item['node_type'],
                item['key'], 
                item['email'],
                item['password'],
                item['node_name'],
                item['status'], 
                item['expiration']
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=container_credentials_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/import-keys', methods=['POST'])
@login_required
def import_keys():
    """Import container credentials from CSV - requires edit permission
    
    Supports two CSV formats:
    1. New format: Host, Container, NodeType, Key, Email, Password, NodeName, Status, Expiration
    2. Legacy format: Host, Container, Key, Status, Expiration (for datagram only)
    """
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
        
        # Detect format based on headers
        fieldnames = set(reader.fieldnames or [])
        new_format_headers = {'Host', 'NodeType', 'Key', 'Email', 'Password'}
        legacy_headers = {'Host', 'Container', 'Key', 'Status', 'Expiration'}
        
        is_new_format = 'NodeType' in fieldnames or 'Email' in fieldnames
        
        if is_new_format:
            # New format - check for required headers
            if 'Host' not in fieldnames:
                return jsonify({'error': 'CSV must have a "Host" column'}), 400
        else:
            # Legacy format - validate old headers
            if not legacy_headers.issubset(fieldnames):
                return jsonify({'error': f'Invalid CSV format. Expected headers: {", ".join(legacy_headers)} or new format with NodeType, Email, Password columns'}), 400
        
        # Process each row
        results = {
            'success': [],
            'skipped': [],
            'failed': []
        }
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            host_name = row.get('Host', '').strip()
            node_type = row.get('NodeType', 'datagram').strip() or 'datagram'
            key = row.get('Key', '').strip()
            email = row.get('Email', '').strip()
            password = row.get('Password', '').strip()
            node_name = row.get('NodeName', '').strip()
            expiration = row.get('Expiration', '').strip()
            container_name = row.get('Container', '').strip()
            
            # Validate node type
            if node_type not in NODE_TYPES:
                results['failed'].append({
                    'row': row_num,
                    'identifier': key or email or 'unknown',
                    'error': f'Invalid node type: {node_type}'
                })
                continue
            
            node_config = NODE_TYPES[node_type]
            
            # Validate credentials based on auth type
            if node_config['auth_type'] == 'api_key':
                if not key:
                    results['failed'].append({
                        'row': row_num,
                        'identifier': 'missing',
                        'error': 'Missing key for datagram node'
                    })
                    continue
                
                if len(key) != 32 or not re.match(r'^[0-9a-z]{32}$', key):
                    results['failed'].append({
                        'row': row_num,
                        'identifier': key,
                        'error': 'Invalid key format (must be 32 characters, 0-9 and a-z only)'
                    })
                    continue
            else:
                # Email/password auth
                if not email:
                    results['failed'].append({
                        'row': row_num,
                        'identifier': 'missing',
                        'error': f'Missing email for {node_type} node'
                    })
                    continue
                
                if not password:
                    results['failed'].append({
                        'row': row_num,
                        'identifier': email,
                        'error': f'Missing password for {node_type} node'
                    })
                    continue
                
                # Basic email validation
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                    results['failed'].append({
                        'row': row_num,
                        'identifier': email,
                        'error': 'Invalid email format'
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
                    'identifier': key or email,
                    'error': f'Host "{host_name}" not found'
                })
                continue
            
            # Get Docker client
            client = host_manager.get_client(host['id'])
            if not client:
                results['failed'].append({
                    'row': row_num,
                    'identifier': key or email,
                    'error': f'Could not connect to host "{host_name}"'
                })
                continue
            
            # Check if container with same credentials already exists
            # For datagram nodes (api_key type): skip if any container with same key exists
            # For non-datagram nodes: skip if a RUNNING container with same email+node_type exists
            exists = False
            existing_status = None
            if node_config['auth_type'] == 'api_key':
                try:
                    containers = client.containers.list(all=True)
                    for c in containers:
                        env_vars = c.attrs.get('Config', {}).get('Env', [])
                        for env in env_vars:
                            if env.startswith('LICENSE_KEY=') and env.split('=', 1)[1] == key:
                                exists = True
                                existing_status = c.status
                                break
                        if exists:
                            break
                except:
                    pass
            else:
                # For non-datagram nodes, check if a RUNNING container exists with same email and node_type
                try:
                    containers = client.containers.list(all=True)
                    for c in containers:
                        env_vars = c.attrs.get('Config', {}).get('Env', [])
                        container_email = None
                        container_node_type = None
                        for env in env_vars:
                            if env.startswith('NODE_EMAIL='):
                                container_email = env.split('=', 1)[1]
                            elif env.startswith('NODE_TYPE='):
                                container_node_type = env.split('=', 1)[1]
                        # Only skip if container is running with same email and node_type
                        if container_email == email and container_node_type == node_type and c.status == 'running':
                            exists = True
                            existing_status = c.status
                            break
                except:
                    pass
            
            if exists:
                results['skipped'].append({
                    'row': row_num,
                    'identifier': key or email,
                    'reason': f'Container with this {"key" if key else "email"} already {"exists" if node_config["auth_type"] == "api_key" else "running"} for {node_type}'
                })
                continue
            
            # Check if image exists
            image_name = node_config['image']
            try:
                client.images.get(image_name)
            except docker.errors.ImageNotFound:
                results['failed'].append({
                    'row': row_num,
                    'identifier': key or email,
                    'error': f'Image "{image_name}" not found on host "{host_name}"'
                })
                continue
            
            # Prepare environment variables
            env_vars = {'NODE_TYPE': node_type}
            
            if node_config['auth_type'] == 'api_key':
                env_vars['LICENSE_KEY'] = key
                if not container_name:
                    container_name = key
            else:
                env_vars['NODE_EMAIL'] = email
                env_vars['NODE_PASSWORD'] = password
                if 'NODE_NAME' in node_config['env_vars'] and node_name:
                    env_vars['NODE_NAME'] = node_name
                
                if not container_name:
                    # Generate container name from email prefix and node type
                    email_prefix = email.split('@')[0][:16]
                    email_prefix = re.sub(r'[^a-zA-Z0-9]', '-', email_prefix).lower()
                    email_prefix = re.sub(r'-+', '-', email_prefix).strip('-')
                    container_name = f'{node_type}-{email_prefix}'
            
            # Sanitize container name
            container_name = re.sub(r'[^a-zA-Z0-9_.-]', '-', container_name)
            container_name = re.sub(r'-+', '-', container_name).strip('-')
            
            # For non-datagram nodes (email/password auth), always add numbering (-1, -2, -3, etc.)
            if node_config['auth_type'] != 'api_key':
                container_name = find_unique_container_name(client, container_name)
            
            if expiration and expiration != 'N/A':
                try:
                    datetime.fromisoformat(expiration.replace('Z', '+00:00'))
                    env_vars['EXPIRATION_DATE'] = expiration
                except:
                    pass  # If parsing fails, skip expiration date
            
            # Start the container
            try:
                container = client.containers.run(
                    image_name,
                    name=container_name,
                    environment=env_vars,
                    platform='linux/amd64',
                    detach=True,
                    restart_policy={'Name': 'unless-stopped'},
                    mem_limit='100m',
                    memswap_limit='200m'
                )
                
                results['success'].append({
                    'row': row_num,
                    'identifier': key or email,
                    'host': host_name,
                    'node_type': node_type,
                    'container_id': container.id[:12]
                })
            except Exception as e:
                results['failed'].append({
                    'row': row_num,
                    'identifier': key or email,
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
        
        # Count only tagged images (what 'docker image ls' shows)
        # info.get('Images') includes intermediate layers, which inflates the count
        try:
            images_list = client.images.list()
            tagged_images_count = len(images_list)
        except Exception:
            # Fallback to info() count if listing fails
            tagged_images_count = info.get('Images', 0)
        
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
            'images': tagged_images_count,
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


# Background thread to monitor expired containers
# This must be defined at module level so it runs regardless of how the app is started
# (e.g., via `python app.py`, `flask run`, `gunicorn`, etc.)
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
                            # Stop container if expired and still running
                            if is_expired(expiration_date) and container.status == 'running':
                                print(f"[Expiration Monitor] Stopping expired container: {container.name} (expired at {expiration_date})")
                                container.stop()
                            
                            # Remove container if expired for more than 7 days
                            if is_past_removal_date(expiration_date, days=7):
                                print(f"[Expiration Monitor] Removing expired container (>7 days): {container.name}")
                                container.remove(force=True)
                except Exception as e:
                    print(f"[Expiration Monitor] Error monitoring containers on host {host['name']}: {e}")
        except Exception as e:
            print(f"[Expiration Monitor] Error in monitor thread: {e}")
        
        # Check every 60 seconds (1 minute) for more responsive expiration handling
        time.sleep(60)


# Thread safety: use a lock to prevent multiple threads from starting the monitor
_monitor_thread_lock = threading.Lock()
_monitor_thread_started = False

def _start_monitor_thread():
    """Start the expiration monitoring thread if not already started (thread-safe)"""
    global _monitor_thread_started
    with _monitor_thread_lock:
        if not _monitor_thread_started:
            monitor_thread = threading.Thread(target=monitor_expired_containers, daemon=True)
            monitor_thread.start()
            print("[*] Started container expiration monitor thread (checking every 60 seconds)")
            _monitor_thread_started = True

# Start the monitor thread when the module is loaded
_start_monitor_thread()


if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Add local host if no hosts exist
    if not host_manager.hosts:
        host_manager.add_host('Local Docker', 'local', 'Local Docker daemon via socket')
    
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('DEBUG', 'False').lower() == 'true')
