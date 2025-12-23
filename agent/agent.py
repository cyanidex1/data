#!/usr/bin/env python3
"""
Datagram Agent - Lightweight agent for managing Docker containers
Connects to control plane via WebSocket and executes container operations
"""

import docker
import json
import os
import sys
import time
import threading
import logging
from datetime import datetime
import websocket
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DatagramAgent:
    """
    Lightweight agent for managing Docker containers on a host.
    Connects to control plane via WebSocket and executes commands.
    """
    
    def __init__(self, control_plane_url, api_key, host_id):
        """
        Initialize the Datagram Agent.
        
        Args:
            control_plane_url: URL of the control plane (e.g., http://localhost:5000)
            api_key: Authentication key for the agent
            host_id: Unique identifier for this host
        """
        self.control_plane_url = control_plane_url.rstrip('/')
        self.api_key = api_key
        self.host_id = host_id
        self.ws = None
        self.running = True
        self.reconnect_delay = 5  # Initial reconnect delay in seconds
        self.max_reconnect_delay = 300  # Max 5 minutes
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            logger.info(f"Connected to Docker daemon")
        except Exception as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            sys.exit(1)
    
    def connect_websocket(self):
        """
        Establish WebSocket connection to control plane.
        Returns True if successful, False otherwise.
        """
        try:
            # Construct WebSocket URL
            ws_url = self.control_plane_url.replace('http://', 'ws://').replace('https://', 'wss://')
            ws_url = f"{ws_url}/api/agent/ws"
            
            logger.info(f"Connecting to control plane: {ws_url}")
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open,
                header={
                    'X-Agent-API-Key': self.api_key,
                    'X-Host-ID': self.host_id
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to create WebSocket connection: {e}")
            return False
    
    def on_open(self, ws):
        """Called when WebSocket connection is opened."""
        logger.info("WebSocket connected to control plane")
        self.reconnect_delay = 5  # Reset reconnect delay on successful connection
        
        # Send connection message with authentication
        connect_msg = {
            'event': 'agent_connect',
            'data': {
                'host_id': self.host_id,
                'api_key': self.api_key,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        ws.send(json.dumps(connect_msg))
    
    def on_message(self, ws, message):
        """
        Handle incoming messages from control plane.
        
        Args:
            ws: WebSocket instance
            message: JSON message from control plane
        """
        try:
            data = json.loads(message)
            command = data.get('command')
            params = data.get('params', {})
            request_id = data.get('request_id')
            
            logger.info(f"Received command: {command} (request_id: {request_id})")
            
            # Execute command and get response
            response = self.execute_command(command, params)
            
            # Send response back to control plane
            response_msg = {
                'event': 'response',
                'data': {
                    'request_id': request_id,
                    'host_id': self.host_id,
                    'success': response.get('success', False),
                    'result': response.get('result'),
                    'error': response.get('error'),
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            ws.send(json.dumps(response_msg))
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def on_error(self, ws, error):
        """Called when WebSocket encounters an error."""
        logger.error(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Called when WebSocket connection is closed."""
        logger.warning(f"WebSocket connection closed (code: {close_status_code}, msg: {close_msg})")
    
    def execute_command(self, command, params):
        """
        Execute a command received from control plane.
        
        Args:
            command: Command name (e.g., 'start_container', 'stop_container')
            params: Command parameters
            
        Returns:
            dict: Response with success status and result/error
        """
        try:
            if command == 'start_container':
                return self.start_container(**params)
            elif command == 'stop_container':
                return self.stop_container(params.get('container_id'))
            elif command == 'remove_container':
                return self.remove_container(params.get('container_id'))
            elif command == 'restart_container':
                return self.restart_container(params.get('container_id'))
            elif command == 'kill_container':
                return self.kill_container(params.get('container_id'))
            elif command == 'get_logs':
                return self.get_logs(params.get('container_id'), params.get('tail', 100))
            elif command == 'get_stats':
                return self.get_host_stats()
            elif command == 'list_containers':
                return self.list_containers()
            else:
                return {
                    'success': False,
                    'error': f'Unknown command: {command}'
                }
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def start_container(self, node_type, key=None, email=None, password=None, 
                       container_name=None, expiration_date=None, **kwargs):
        """
        Create and start a Docker container.
        
        Args:
            node_type: Type of node (datagram, element, etc.)
            key: API key for datagram nodes
            email: Email for other node types
            password: Password for other node types
            container_name: Optional container name
            expiration_date: Optional expiration date
            **kwargs: Additional parameters
            
        Returns:
            dict: Response with container information
        """
        try:
            # Prepare environment variables
            env_vars = {'NODE_TYPE': node_type}
            
            # Add authentication based on node type
            if key:
                env_vars['LICENSE_KEY'] = key
            if email:
                env_vars['NODE_EMAIL'] = email
            if password:
                env_vars['NODE_PASSWORD'] = password
            if expiration_date:
                env_vars['EXPIRATION_DATE'] = expiration_date
            
            # Add any additional env vars from kwargs
            for k, v in kwargs.items():
                if k.startswith('env_'):
                    env_vars[k[4:].upper()] = v
            
            # Determine image name based on node type
            image_map = {
                'datagram': 'datagram',
                'element': 'element-node',
                'elevate': 'elevate-node',
                'grow': 'grow-node',
                'revo': 'revo-node',
                'rlink': 'rlink-node',
                'switch': 'switch-node',
                'win': 'win-node'
            }
            image_name = image_map.get(node_type, 'datagram')
            
            # Check if image exists
            try:
                self.docker_client.images.get(image_name)
            except docker.errors.ImageNotFound:
                return {
                    'success': False,
                    'error': f'Image "{image_name}" not found. Please build it first.'
                }
            
            # Generate container name if not provided
            if not container_name:
                if key:
                    container_name = key
                elif email:
                    email_prefix = email.split('@')[0][:16]
                    container_name = f'{node_type}-{email_prefix}'
                else:
                    container_name = f'{node_type}-{int(time.time())}'
            
            # Start container
            container = self.docker_client.containers.run(
                image=image_name,
                name=container_name,
                environment=env_vars,
                platform='linux/amd64',
                detach=True,
                restart_policy={'Name': 'on-failure', 'MaximumRetryCount': 3}
            )
            
            logger.info(f"Started container: {container_name} ({container.id[:12]})")
            
            return {
                'success': True,
                'result': {
                    'container_id': container.id[:12],
                    'container_name': container_name,
                    'node_type': node_type
                }
            }
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            return {
                'success': False,
                'error': f'Docker API error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error starting container: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def stop_container(self, container_id):
        """Stop a running container."""
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop()
            logger.info(f"Stopped container: {container_id}")
            return {
                'success': True,
                'result': {'container_id': container_id}
            }
        except docker.errors.NotFound:
            return {
                'success': False,
                'error': f'Container not found: {container_id}'
            }
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def restart_container(self, container_id):
        """Restart a container."""
        try:
            container = self.docker_client.containers.get(container_id)
            container.restart()
            logger.info(f"Restarted container: {container_id}")
            return {
                'success': True,
                'result': {'container_id': container_id}
            }
        except docker.errors.NotFound:
            return {
                'success': False,
                'error': f'Container not found: {container_id}'
            }
        except Exception as e:
            logger.error(f"Error restarting container: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def kill_container(self, container_id):
        """Kill a running container."""
        try:
            container = self.docker_client.containers.get(container_id)
            container.kill()
            logger.info(f"Killed container: {container_id}")
            return {
                'success': True,
                'result': {'container_id': container_id}
            }
        except docker.errors.NotFound:
            return {
                'success': False,
                'error': f'Container not found: {container_id}'
            }
        except Exception as e:
            logger.error(f"Error killing container: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def remove_container(self, container_id):
        """Remove a container."""
        try:
            container = self.docker_client.containers.get(container_id)
            container.remove(force=True)
            logger.info(f"Removed container: {container_id}")
            return {
                'success': True,
                'result': {'container_id': container_id}
            }
        except docker.errors.NotFound:
            return {
                'success': False,
                'error': f'Container not found: {container_id}'
            }
        except Exception as e:
            logger.error(f"Error removing container: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_logs(self, container_id, tail=100):
        """Get container logs."""
        try:
            container = self.docker_client.containers.get(container_id)
            logs = container.logs(tail=tail).decode('utf-8')
            return {
                'success': True,
                'result': {'logs': logs}
            }
        except docker.errors.NotFound:
            return {
                'success': False,
                'error': f'Container not found: {container_id}'
            }
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_containers(self):
        """List all containers on this host."""
        try:
            containers = self.docker_client.containers.list(all=True)
            container_list = []
            
            for container in containers:
                # Skip the webapp container itself
                if container.name == 'datagram-control-panel':
                    continue
                
                attrs = container.attrs
                config = attrs.get('Config', {})
                env_vars = config.get('Env', [])
                
                # Parse environment variables
                env_dict = {}
                for env in env_vars:
                    if '=' in env:
                        key, value = env.split('=', 1)
                        env_dict[key] = value
                
                container_list.append({
                    'id': container.id[:12],
                    'name': container.name,
                    'status': container.status,
                    'image': config.get('Image', 'unknown'),
                    'created': attrs.get('Created', ''),
                    'key': env_dict.get('LICENSE_KEY'),
                    'email': env_dict.get('NODE_EMAIL'),
                    'node_type': env_dict.get('NODE_TYPE'),
                    'expiration_date': env_dict.get('EXPIRATION_DATE')
                })
            
            return {
                'success': True,
                'result': {'containers': container_list}
            }
        except Exception as e:
            logger.error(f"Error listing containers: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_host_stats(self):
        """Collect host statistics."""
        try:
            info = self.docker_client.info()
            df = self.docker_client.df()
            
            # Count tagged images
            try:
                images_list = self.docker_client.images.list()
                tagged_images_count = len(images_list)
            except Exception:
                tagged_images_count = info.get('Images', 0)
            
            stats = {
                'cpu': {
                    'cores': info.get('NCPU', 0),
                },
                'memory': {
                    'total': info.get('MemTotal', 0),
                    'total_gb': round(info.get('MemTotal', 0) / (1024**3), 2),
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
            
            # Add disk usage
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
            
            return {
                'success': True,
                'result': {'stats': stats}
            }
        except Exception as e:
            logger.error(f"Error getting host stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def report_health(self):
        """
        Report health metrics to control plane via HTTP POST.
        This runs in a separate thread every 30 seconds.
        """
        while self.running:
            try:
                # Get host stats
                stats_response = self.get_host_stats()
                
                if stats_response.get('success'):
                    # Send health data to control plane
                    health_data = {
                        'host_id': self.host_id,
                        'timestamp': datetime.utcnow().isoformat(),
                        'stats': stats_response.get('result', {}).get('stats', {})
                    }
                    
                    headers = {
                        'Content-Type': 'application/json',
                        'X-Agent-API-Key': self.api_key
                    }
                    
                    url = f"{self.control_plane_url}/api/agent/health"
                    response = requests.post(url, json=health_data, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        logger.debug("Health metrics reported successfully")
                    else:
                        logger.warning(f"Failed to report health: {response.status_code}")
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to send health report: {e}")
            except Exception as e:
                logger.error(f"Error in health reporting: {e}")
            
            # Wait 30 seconds before next report
            time.sleep(30)
    
    def run(self):
        """
        Main loop - connect to WebSocket and handle reconnection.
        """
        # Start health reporting thread
        health_thread = threading.Thread(target=self.report_health, daemon=True)
        health_thread.start()
        logger.info("Started health reporting thread (reporting every 30 seconds)")
        
        # Main WebSocket connection loop with auto-reconnection
        while self.running:
            try:
                if self.connect_websocket():
                    # Run WebSocket connection (blocking)
                    self.ws.run_forever()
                
                # Connection closed, try to reconnect after delay
                if self.running:
                    logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
                    time.sleep(self.reconnect_delay)
                    
                    # Exponential backoff for reconnection delay
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                    
            except KeyboardInterrupt:
                logger.info("Shutting down agent...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                if self.running:
                    time.sleep(self.reconnect_delay)


def main():
    """Main entry point for the agent."""
    # Get configuration from environment variables
    control_plane_url = os.environ.get('CONTROL_PLANE_URL')
    api_key = os.environ.get('AGENT_API_KEY')
    host_id = os.environ.get('HOST_ID')
    
    # Validate configuration
    if not control_plane_url:
        logger.error("CONTROL_PLANE_URL environment variable is required")
        sys.exit(1)
    
    if not api_key:
        logger.error("AGENT_API_KEY environment variable is required")
        sys.exit(1)
    
    if not host_id:
        logger.error("HOST_ID environment variable is required")
        sys.exit(1)
    
    logger.info(f"Starting Datagram Agent")
    logger.info(f"Control Plane: {control_plane_url}")
    logger.info(f"Host ID: {host_id}")
    
    # Create and run agent
    agent = DatagramAgent(control_plane_url, api_key, host_id)
    agent.run()


if __name__ == '__main__':
    main()
