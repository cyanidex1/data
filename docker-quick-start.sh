#!/bin/bash

# Quick Start Script for Running Multiple Datagram Instances in Docker
# Each container runs with sudo-like privileges and creates WireGuard interfaces

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATAGRAM_DIR="$SCRIPT_DIR/datagram"
IMAGE_NAME="datagram"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
}

# Build datagram image if needed
build_image() {
    print_info "Checking datagram image..."
    
    if docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
        print_success "Datagram image already exists"
        return 0
    fi
    
    print_info "Building datagram image (this may take a few minutes)..."
    
    if [ ! -d "$DATAGRAM_DIR" ]; then
        print_error "Datagram directory not found: $DATAGRAM_DIR"
        exit 1
    fi
    
    cd "$DATAGRAM_DIR"
    
    # Download binaries if not present
    if [ ! -d "binaries/.datagram" ]; then
        print_info "Downloading datagram binaries..."
        if [ -f "download-binaries.sh" ]; then
            ./download-binaries.sh
        else
            print_error "download-binaries.sh not found"
            exit 1
        fi
    fi
    
    # Build image
    docker build --platform linux/amd64 -t "$IMAGE_NAME" .
    
    cd "$SCRIPT_DIR"
    print_success "Datagram image built successfully"
}

# Quick add containers
quick_start() {
    local count="${1:-1}"
    
    if [ "$count" -lt 1 ]; then
        print_error "Count must be at least 1"
        exit 1
    fi
    
    print_info "Starting $count datagram container(s)..."
    echo ""
    
    for i in $(seq 1 "$count"); do
        # Generate a random key for demo purposes
        # In production, use your actual license keys
        local key=$(openssl rand -hex 16)
        
        print_info "[$i/$count] Starting container with auto-generated key..."
        
        cd "$DATAGRAM_DIR"
        ./start.sh "$key"
        cd "$SCRIPT_DIR"
        
        echo ""
    done
    
    print_success "All containers started!"
    echo ""
    print_info "List containers: docker ps --filter ancestor=$IMAGE_NAME"
    print_info "View logs: docker logs <container-name>"
    print_info "Stop all: docker stop \$(docker ps -q --filter ancestor=$IMAGE_NAME)"
}

# Start with specific keys
start_with_keys() {
    print_info "Starting containers with provided keys..."
    echo ""
    
    local index=1
    for key in "$@"; do
        print_info "[$index/$#] Starting container with key: $key"
        
        cd "$DATAGRAM_DIR"
        ./start.sh "$key"
        cd "$SCRIPT_DIR"
        
        echo ""
        index=$((index + 1))
    done
    
    print_success "All containers started!"
}

# List all datagram containers
list_containers() {
    print_info "Datagram Containers:"
    echo ""
    
    docker ps -a --filter ancestor="$IMAGE_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# Show container details
show_details() {
    local container_name="$1"
    
    print_info "Details for container: $container_name"
    echo ""
    
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        print_error "Container '$container_name' not found"
        exit 1
    fi
    
    print_info "Status:"
    docker ps -a --filter name="^${container_name}$" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    print_info "Network interfaces inside container:"
    docker exec "$container_name" ip addr show || print_warning "Container may not be running"
    
    echo ""
    print_info "Network namespace:"
    docker exec "$container_name" readlink /proc/self/ns/net || print_warning "Container may not be running"
}

# Show logs
show_logs() {
    local container_name="$1"
    local lines="${2:-50}"
    
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        print_error "Container '$container_name' not found"
        exit 1
    fi
    
    print_info "Last $lines lines of logs for $container_name:"
    echo ""
    docker logs --tail "$lines" "$container_name"
}

# Stop all datagram containers
stop_all() {
    print_info "Stopping all datagram containers..."
    
    local containers=$(docker ps -q --filter ancestor="$IMAGE_NAME")
    
    if [ -z "$containers" ]; then
        print_warning "No running datagram containers found"
        return 0
    fi
    
    docker stop $containers
    print_success "All datagram containers stopped"
}

# Remove all datagram containers
remove_all() {
    print_warning "This will remove all datagram containers (both running and stopped)"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cancelled"
        exit 0
    fi
    
    print_info "Stopping and removing all datagram containers..."
    
    local containers=$(docker ps -aq --filter ancestor="$IMAGE_NAME")
    
    if [ -z "$containers" ]; then
        print_warning "No datagram containers found"
        return 0
    fi
    
    docker stop $containers 2>/dev/null || true
    docker rm $containers
    print_success "All datagram containers removed"
}

# Show usage
usage() {
    cat <<EOF
Datagram Docker Quick Start

Usage: $0 <command> [arguments]

Commands:
  build                         Build the datagram Docker image
  quick-start [count]           Start multiple containers with random keys (default: 1)
  start <key1> [key2] ...       Start containers with specific keys
  list                          List all datagram containers
  details <name>                Show detailed info for a container
  logs <name> [lines]           Show logs for a container (default: 50 lines)
  stop-all                      Stop all datagram containers
  remove-all                    Remove all datagram containers (prompts for confirmation)

Examples:
  # Build the image (run once)
  $0 build

  # Start 3 containers with random keys (for testing)
  $0 quick-start 3

  # Start containers with specific keys
  $0 start 92bcf2ae4e326968f40f8670a3596b80 a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

  # List all containers
  $0 list

  # Show details including WireGuard interfaces
  $0 details node1

  # View logs
  $0 logs node1

  # Stop all containers
  $0 stop-all

  # Remove all containers
  $0 remove-all

Notes:
  - Each container runs 'datagram run' with sudo-like privileges
  - Each container creates WireGuard interfaces (wg0, wg1, etc.) in its own network namespace
  - Containers are isolated from each other and the host
  - See DOCKER_WITH_SUDO.md for detailed documentation

Direct Docker Commands:
  docker ps --filter ancestor=datagram       # List containers
  docker logs <container-name>                # View logs
  docker exec -it <container-name> sh         # Enter container shell
  docker exec <container-name> ip addr show   # Check interfaces
EOF
}

# Main command dispatcher
main() {
    check_docker
    
    if [ $# -eq 0 ]; then
        usage
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        build)
            build_image
            ;;
        quick-start)
            build_image
            quick_start "${1:-1}"
            ;;
        start)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 start <key1> [key2] ..."
                exit 1
            fi
            build_image
            start_with_keys "$@"
            ;;
        list)
            list_containers
            ;;
        details)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 details <container-name>"
                exit 1
            fi
            show_details "$1"
            ;;
        logs)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 logs <container-name> [lines]"
                exit 1
            fi
            show_logs "$@"
            ;;
        stop-all)
            stop_all
            ;;
        remove-all)
            remove_all
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            usage
            exit 1
            ;;
    esac
}

main "$@"
