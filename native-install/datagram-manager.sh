#!/bin/bash

# Datagram Native Instance Manager
# Manages multiple datagram instances running natively on the host with sudo privileges

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/datagram/instances"
DATA_DIR="/var/lib/datagram"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_TEMPLATE="datagram@.service"

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

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Install datagram binary if not present
install_datagram() {
    print_info "Checking for datagram binary..."
    
    if [ -f "$INSTALL_DIR/datagram" ]; then
        print_success "Datagram binary already installed at $INSTALL_DIR/datagram"
        return 0
    fi
    
    print_info "Downloading datagram binary..."
    curl -fsSL \
        "https://github.com/Datagram-Group/datagram-cli-release/releases/latest/download/datagram-cli-x86_64-linux" \
        -o "$INSTALL_DIR/datagram"
    
    chmod +x "$INSTALL_DIR/datagram"
    print_success "Datagram binary installed to $INSTALL_DIR/datagram"
}

# Install systemd service template
install_service() {
    print_info "Installing systemd service template..."
    
    if [ ! -f "$SCRIPT_DIR/$SERVICE_TEMPLATE" ]; then
        print_error "Service template not found: $SCRIPT_DIR/$SERVICE_TEMPLATE"
        exit 1
    fi
    
    cp "$SCRIPT_DIR/$SERVICE_TEMPLATE" "$SYSTEMD_DIR/"
    systemctl daemon-reload
    
    print_success "Systemd service template installed"
}

# Setup directories
setup_directories() {
    print_info "Setting up directories..."
    
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$DATA_DIR"
    
    # Set proper permissions
    chmod 700 "$CONFIG_DIR"
    chmod 755 "$DATA_DIR"
    
    print_success "Directories created: $CONFIG_DIR, $DATA_DIR"
}

# Initialize setup
init() {
    print_info "Initializing datagram native installation..."
    
    check_root
    setup_directories
    install_datagram
    install_service
    
    print_success "Installation complete!"
    echo ""
    print_info "Next steps:"
    echo "  1. Add instances: sudo $0 add <instance-name> <license-key>"
    echo "  2. Start instance: sudo $0 start <instance-name>"
    echo "  3. List instances: sudo $0 list"
}

# Get next available instance number
get_next_instance_number() {
    local prefix="${1:-node}"
    local index=0
    
    while [ -f "$CONFIG_DIR/${prefix}${index}.conf" ] || systemctl is-active --quiet "datagram@${prefix}${index}.service" 2>/dev/null; do
        index=$((index + 1))
    done
    
    echo "$index"
}

# Add a new instance
add_instance() {
    local instance_name="$1"
    local license_key="$2"
    
    check_root
    
    # Validate instance name
    if [[ ! "$instance_name" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        print_error "Invalid instance name. Use only alphanumeric characters, underscores, and hyphens."
        exit 1
    fi
    
    # Check if instance already exists
    if [ -f "$CONFIG_DIR/${instance_name}.conf" ]; then
        print_error "Instance '$instance_name' already exists"
        exit 1
    fi
    
    # Validate license key (should be 32 characters hex)
    if [[ ! "$license_key" =~ ^[a-fA-F0-9]{32}$ ]]; then
        print_warning "License key should be 32 hexadecimal characters"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Create config file
    cat > "$CONFIG_DIR/${instance_name}.conf" <<EOF
LICENSE_KEY=$license_key
EOF
    
    chmod 600 "$CONFIG_DIR/${instance_name}.conf"
    
    print_success "Instance '$instance_name' added"
    print_info "Start it with: sudo $0 start $instance_name"
}

# Remove an instance
remove_instance() {
    local instance_name="$1"
    
    check_root
    
    if [ ! -f "$CONFIG_DIR/${instance_name}.conf" ]; then
        print_error "Instance '$instance_name' does not exist"
        exit 1
    fi
    
    # Stop service if running
    if systemctl is-active --quiet "datagram@${instance_name}.service"; then
        print_info "Stopping instance '$instance_name'..."
        systemctl stop "datagram@${instance_name}.service"
    fi
    
    # Disable service if enabled
    if systemctl is-enabled --quiet "datagram@${instance_name}.service" 2>/dev/null; then
        systemctl disable "datagram@${instance_name}.service"
    fi
    
    # Remove config file
    rm -f "$CONFIG_DIR/${instance_name}.conf"
    
    print_success "Instance '$instance_name' removed"
}

# Start an instance
start_instance() {
    local instance_name="$1"
    
    check_root
    
    if [ ! -f "$CONFIG_DIR/${instance_name}.conf" ]; then
        print_error "Instance '$instance_name' does not exist"
        print_info "Add it first with: sudo $0 add $instance_name <license-key>"
        exit 1
    fi
    
    print_info "Starting instance '$instance_name'..."
    systemctl start "datagram@${instance_name}.service"
    
    # Wait a moment for service to start
    sleep 2
    
    if systemctl is-active --quiet "datagram@${instance_name}.service"; then
        print_success "Instance '$instance_name' started successfully"
        
        # Enable on boot
        if ! systemctl is-enabled --quiet "datagram@${instance_name}.service" 2>/dev/null; then
            systemctl enable "datagram@${instance_name}.service"
            print_info "Instance '$instance_name' enabled on boot"
        fi
    else
        print_error "Failed to start instance '$instance_name'"
        print_info "Check logs with: sudo journalctl -u datagram@${instance_name}.service -n 50"
        exit 1
    fi
}

# Stop an instance
stop_instance() {
    local instance_name="$1"
    
    check_root
    
    print_info "Stopping instance '$instance_name'..."
    systemctl stop "datagram@${instance_name}.service"
    
    if ! systemctl is-active --quiet "datagram@${instance_name}.service"; then
        print_success "Instance '$instance_name' stopped"
    else
        print_error "Failed to stop instance '$instance_name'"
        exit 1
    fi
}

# Restart an instance
restart_instance() {
    local instance_name="$1"
    
    check_root
    
    print_info "Restarting instance '$instance_name'..."
    systemctl restart "datagram@${instance_name}.service"
    
    sleep 2
    
    if systemctl is-active --quiet "datagram@${instance_name}.service"; then
        print_success "Instance '$instance_name' restarted successfully"
    else
        print_error "Failed to restart instance '$instance_name'"
        exit 1
    fi
}

# Show status of an instance
status_instance() {
    local instance_name="$1"
    
    if [ ! -f "$CONFIG_DIR/${instance_name}.conf" ]; then
        print_error "Instance '$instance_name' does not exist"
        exit 1
    fi
    
    systemctl status "datagram@${instance_name}.service"
}

# Show logs for an instance
logs_instance() {
    local instance_name="$1"
    local lines="${2:-50}"
    
    if [ ! -f "$CONFIG_DIR/${instance_name}.conf" ]; then
        print_error "Instance '$instance_name' does not exist"
        exit 1
    fi
    
    journalctl -u "datagram@${instance_name}.service" -n "$lines" --no-pager
}

# List all instances
list_instances() {
    print_info "Datagram Instances:"
    echo ""
    
    if [ ! -d "$CONFIG_DIR" ] || [ -z "$(ls -A "$CONFIG_DIR" 2>/dev/null)" ]; then
        print_warning "No instances configured"
        return
    fi
    
    printf "%-20s %-10s %-15s\n" "INSTANCE" "STATUS" "BOOT"
    printf "%-20s %-10s %-15s\n" "--------" "------" "----"
    
    for config_file in "$CONFIG_DIR"/*.conf; do
        if [ -f "$config_file" ]; then
            instance_name=$(basename "$config_file" .conf)
            
            # Check if service is active
            if systemctl is-active --quiet "datagram@${instance_name}.service" 2>/dev/null; then
                status="${GREEN}running${NC}"
            else
                status="${RED}stopped${NC}"
            fi
            
            # Check if enabled on boot
            if systemctl is-enabled --quiet "datagram@${instance_name}.service" 2>/dev/null; then
                boot="${GREEN}enabled${NC}"
            else
                boot="${YELLOW}disabled${NC}"
            fi
            
            printf "%-20s %-20s %-25s\n" "$instance_name" "$(echo -e "$status")" "$(echo -e "$boot")"
        fi
    done
}

# Enable an instance on boot
enable_instance() {
    local instance_name="$1"
    
    check_root
    
    if [ ! -f "$CONFIG_DIR/${instance_name}.conf" ]; then
        print_error "Instance '$instance_name' does not exist"
        exit 1
    fi
    
    systemctl enable "datagram@${instance_name}.service"
    print_success "Instance '$instance_name' enabled on boot"
}

# Disable an instance on boot
disable_instance() {
    local instance_name="$1"
    
    check_root
    
    if [ ! -f "$CONFIG_DIR/${instance_name}.conf" ]; then
        print_error "Instance '$instance_name' does not exist"
        exit 1
    fi
    
    systemctl disable "datagram@${instance_name}.service"
    print_success "Instance '$instance_name' disabled on boot"
}

# Quick add with auto-increment
quick_add() {
    local license_key="$1"
    local prefix="${2:-node}"
    
    check_root
    
    local index=$(get_next_instance_number "$prefix")
    local instance_name="${prefix}${index}"
    
    add_instance "$instance_name" "$license_key"
    start_instance "$instance_name"
    
    print_success "Instance '$instance_name' created and started"
}

# Show usage
usage() {
    cat <<EOF
Datagram Native Instance Manager

Usage: $0 <command> [arguments]

Commands:
  init                          Initialize datagram native installation
  add <name> <key>              Add a new instance
  quick-add <key> [prefix]      Add and start instance with auto-increment name
  remove <name>                 Remove an instance
  start <name>                  Start an instance
  stop <name>                   Stop an instance
  restart <name>                Restart an instance
  status <name>                 Show instance status
  logs <name> [lines]           Show instance logs (default: 50 lines)
  list                          List all instances
  enable <name>                 Enable instance on boot
  disable <name>                Disable instance on boot

Examples:
  # Initialize (run once)
  sudo $0 init

  # Add instances manually
  sudo $0 add node0 92bcf2ae4e326968f40f8670a3596b80
  sudo $0 start node0

  # Quick add (auto-increment name)
  sudo $0 quick-add 92bcf2ae4e326968f40f8670a3596b80
  sudo $0 quick-add a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6 mynode

  # Manage instances
  sudo $0 list
  sudo $0 status node0
  sudo $0 logs node0
  sudo $0 restart node0
  sudo $0 stop node0
  sudo $0 remove node0

Notes:
  - Each instance creates its own WireGuard interface (wg0, wg1, wg2, etc.)
  - Instances run with NET_ADMIN, NET_RAW, and SYS_MODULE capabilities
  - All instances start automatically on boot when started via this script
  - License keys should be 32 hexadecimal characters
EOF
}

# Main command dispatcher
main() {
    if [ $# -eq 0 ]; then
        usage
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        init)
            init
            ;;
        add)
            if [ $# -lt 2 ]; then
                print_error "Usage: $0 add <instance-name> <license-key>"
                exit 1
            fi
            add_instance "$1" "$2"
            ;;
        quick-add)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 quick-add <license-key> [prefix]"
                exit 1
            fi
            quick_add "$@"
            ;;
        remove)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 remove <instance-name>"
                exit 1
            fi
            remove_instance "$1"
            ;;
        start)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 start <instance-name>"
                exit 1
            fi
            start_instance "$1"
            ;;
        stop)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 stop <instance-name>"
                exit 1
            fi
            stop_instance "$1"
            ;;
        restart)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 restart <instance-name>"
                exit 1
            fi
            restart_instance "$1"
            ;;
        status)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 status <instance-name>"
                exit 1
            fi
            status_instance "$1"
            ;;
        logs)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 logs <instance-name> [lines]"
                exit 1
            fi
            logs_instance "$@"
            ;;
        list)
            list_instances
            ;;
        enable)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 enable <instance-name>"
                exit 1
            fi
            enable_instance "$1"
            ;;
        disable)
            if [ $# -lt 1 ]; then
                print_error "Usage: $0 disable <instance-name>"
                exit 1
            fi
            disable_instance "$1"
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
