"""
Agent Manager - WebSocket server for managing agent connections
Handles agent authentication, command dispatch, and health monitoring
"""

import os
import json
import time
import threading
from datetime import datetime
from flask import request
from flask_socketio import SocketIO, emit, disconnect
import logging

logger = logging.getLogger(__name__)

# Store connected agents (host_id -> socket_id)
connected_agents = {}
agent_lock = threading.Lock()

# Store command responses (request_id -> response)
command_responses = {}
response_lock = threading.Lock()

# Store agent health metrics (host_id -> health_data)
agent_health = {}
health_lock = threading.Lock()

# Timeout for command responses (seconds)
COMMAND_TIMEOUT = 30


def init_socketio(app):
    """
    Initialize Flask-SocketIO with the Flask app.
    
    Args:
        app: Flask application instance
        
    Returns:
        SocketIO instance
    """
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',
        logger=False,
        engineio_logger=False
    )
    
    # Register WebSocket event handlers
    register_handlers(socketio)
    
    # Start cleanup thread
    start_cleanup_thread()
    
    logger.info("Flask-SocketIO initialized")
    return socketio


def register_handlers(socketio):
    """
    Register WebSocket event handlers.
    
    Args:
        socketio: SocketIO instance
    """
    
    @socketio.on('connect', namespace='/api/agent/ws')
    def handle_agent_connect():
        """Handle agent connection to WebSocket."""
        try:
            # Get authentication headers
            api_key = request.headers.get('X-Agent-API-Key')
            host_id = request.headers.get('X-Host-ID')
            
            if not api_key or not host_id:
                logger.warning(f"Agent connection rejected: missing credentials")
                disconnect()
                return
            
            # Validate API key
            if not validate_agent_api_key(api_key):
                logger.warning(f"Agent connection rejected: invalid API key for host {host_id}")
                disconnect()
                return
            
            # Store agent connection
            with agent_lock:
                connected_agents[host_id] = request.sid
            
            logger.info(f"Agent connected: {host_id} (socket: {request.sid})")
            
            # Send acknowledgment
            emit('connected', {'status': 'success', 'host_id': host_id})
            
        except Exception as e:
            logger.error(f"Error handling agent connection: {e}")
            disconnect()
    
    @socketio.on('disconnect', namespace='/api/agent/ws')
    def handle_agent_disconnect():
        """Handle agent disconnection."""
        try:
            # Find and remove agent by socket ID
            host_id = None
            with agent_lock:
                for hid, sid in list(connected_agents.items()):
                    if sid == request.sid:
                        host_id = hid
                        del connected_agents[hid]
                        break
            
            if host_id:
                logger.info(f"Agent disconnected: {host_id}")
            else:
                logger.warning(f"Unknown agent disconnected: {request.sid}")
                
        except Exception as e:
            logger.error(f"Error handling agent disconnect: {e}")
    
    @socketio.on('agent_connect', namespace='/api/agent/ws')
    def handle_agent_connect_event(data):
        """Handle agent connect event with authentication."""
        try:
            host_id = data.get('host_id')
            api_key = data.get('api_key')
            
            if not validate_agent_api_key(api_key):
                logger.warning(f"Invalid API key from agent {host_id}")
                emit('error', {'message': 'Invalid API key'})
                disconnect()
                return
            
            # Update agent connection
            with agent_lock:
                connected_agents[host_id] = request.sid
            
            logger.info(f"Agent authenticated: {host_id}")
            emit('authenticated', {'status': 'success'})
            
        except Exception as e:
            logger.error(f"Error in agent_connect event: {e}")
    
    @socketio.on('response', namespace='/api/agent/ws')
    def handle_agent_response(data):
        """Handle response from agent."""
        try:
            request_id = data.get('request_id')
            if request_id:
                # Store response for retrieval
                with response_lock:
                    command_responses[request_id] = {
                        'data': data,
                        'timestamp': time.time()
                    }
                logger.debug(f"Received response for request {request_id}")
            else:
                logger.warning("Received response without request_id")
        except Exception as e:
            logger.error(f"Error handling agent response: {e}")


def validate_agent_api_key(api_key):
    """
    Validate agent API key.
    
    Args:
        api_key: API key to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Get API keys from environment variable (comma-separated)
    valid_keys = os.environ.get('AGENT_API_KEYS', '').split(',')
    valid_keys = [key.strip() for key in valid_keys if key.strip()]
    
    # If no keys configured, reject all connections
    if not valid_keys:
        logger.warning("No AGENT_API_KEYS configured")
        return False
    
    return api_key in valid_keys


def send_command_to_agent(socketio, host_id, command, params):
    """
    Send a command to an agent via WebSocket.
    
    Args:
        socketio: SocketIO instance
        host_id: Target host ID
        command: Command name
        params: Command parameters
        
    Returns:
        dict: Response from agent or error
    """
    try:
        # Check if agent is connected
        with agent_lock:
            socket_id = connected_agents.get(host_id)
        
        if not socket_id:
            return {
                'success': False,
                'error': f'Agent {host_id} is not connected'
            }
        
        # Generate unique request ID
        request_id = f"{host_id}_{int(time.time() * 1000)}"
        
        # Send command to agent
        message = {
            'command': command,
            'params': params,
            'request_id': request_id
        }
        
        socketio.emit(
            'command',
            message,
            room=socket_id,
            namespace='/api/agent/ws'
        )
        
        logger.info(f"Sent command {command} to agent {host_id} (request: {request_id})")
        
        # Wait for response with timeout
        start_time = time.time()
        while time.time() - start_time < COMMAND_TIMEOUT:
            with response_lock:
                if request_id in command_responses:
                    response_data = command_responses.pop(request_id)
                    return response_data['data']
            
            # Sleep briefly to avoid busy-waiting
            time.sleep(0.1)
        
        # Timeout
        logger.warning(f"Command {command} to agent {host_id} timed out")
        return {
            'success': False,
            'error': 'Command timed out (no response from agent)'
        }
        
    except Exception as e:
        logger.error(f"Error sending command to agent: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def is_agent_connected(host_id):
    """
    Check if an agent is currently connected.
    
    Args:
        host_id: Host ID to check
        
    Returns:
        bool: True if connected, False otherwise
    """
    with agent_lock:
        return host_id in connected_agents


def get_connected_agents():
    """
    Get list of connected agent host IDs.
    
    Returns:
        list: Connected host IDs
    """
    with agent_lock:
        return list(connected_agents.keys())


def store_health_data(host_id, health_data):
    """
    Store health metrics from an agent.
    
    Args:
        host_id: Host ID
        health_data: Health metrics data
    """
    with health_lock:
        agent_health[host_id] = {
            'data': health_data,
            'timestamp': datetime.utcnow().isoformat(),
            'last_seen': time.time()
        }


def get_health_data(host_id):
    """
    Get health metrics for an agent.
    
    Args:
        host_id: Host ID
        
    Returns:
        dict: Health data or None if not available
    """
    with health_lock:
        return agent_health.get(host_id)


def get_all_health_data():
    """
    Get health metrics for all agents.
    
    Returns:
        dict: Health data for all agents
    """
    with health_lock:
        return dict(agent_health)


def cleanup_old_responses():
    """
    Background task to clean up old command responses.
    Runs every 60 seconds and removes responses older than 5 minutes.
    """
    while True:
        try:
            current_time = time.time()
            with response_lock:
                expired = [
                    req_id for req_id, resp in command_responses.items()
                    if current_time - resp['timestamp'] > 300  # 5 minutes
                ]
                for req_id in expired:
                    del command_responses[req_id]
                
                if expired:
                    logger.debug(f"Cleaned up {len(expired)} old command responses")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
        
        time.sleep(60)


# Cleanup thread management
_cleanup_thread = None
_cleanup_lock = threading.Lock()

def start_cleanup_thread():
    """Start the cleanup thread if not already started (thread-safe)"""
    global _cleanup_thread
    with _cleanup_lock:
        if _cleanup_thread is None:
            _cleanup_thread = threading.Thread(target=cleanup_old_responses, daemon=True)
            _cleanup_thread.start()
            logger.info("Started command response cleanup thread")
