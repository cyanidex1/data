#!/bin/bash
# fix-container-limits-max. sh - Apply maximum possible system limits for containers

echo "🔧 Applying MAXIMUM system-wide limits for large-scale container deployments..."

# Backup existing configs
echo "📦 Creating backups..."
sudo cp /etc/security/limits. conf /etc/security/limits. conf.backup. $(date +%Y%m%d_%H%M%S) 2>/dev/null || true
sudo cp /etc/sysctl.conf /etc/sysctl.conf.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# 1. System-wide file limits (MAXIMUM)
echo "📁 Setting maximum file descriptor limits..."
sudo tee -a /etc/security/limits.conf > /dev/null <<EOF

# Maximum limits for container operations (added $(date))
* soft nofile 1048576
* hard nofile 1048576
root soft nofile 1048576
root hard nofile 1048576
* soft nproc 1048576
* hard nproc 1048576
root soft nproc 1048576
root hard nproc 1048576
EOF

# 2. Kernel parameters (MAXIMUM VALUES)
echo "⚙️  Setting maximum kernel parameters..."
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF

# Maximum kernel limits for containers (added $(date))
# File system limits
fs.file-max = 9223372036854775807
fs.nr_open = 1048576
fs.inotify.max_user_instances = 8192
fs.inotify.max_user_watches = 524288
fs.inotify.max_queued_events = 32768

# Process limits
kernel.pid_max = 4194304
kernel.threads-max = 4194304

# Network connection tracking (for VPN/WireGuard)
net.netfilter.nf_conntrack_max = 2097152
net.nf_conntrack_max = 2097152
net.netfilter.nf_conntrack_buckets = 524288
net.netfilter. nf_conntrack_tcp_timeout_established = 86400

# Network performance
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65536
net.ipv4.tcp_max_syn_backlog = 65536
net.ipv4.ip_local_port_range = 1024 65535
net. ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30

# Memory and swap
vm.max_map_count = 262144
vm.overcommit_memory = 1
vm.swappiness = 10

# ARP cache (for many network interfaces)
net.ipv4.neigh.default.gc_thresh1 = 80000
net.ipv4.neigh.default.gc_thresh2 = 90000
net.ipv4.neigh.default.gc_thresh3 = 100000
EOF

# Apply sysctl changes immediately
echo "🔄 Applying kernel parameters..."
sudo sysctl -p

# 3. Docker daemon limits (MAXIMUM)
echo "🐳 Setting maximum Docker daemon limits..."
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service. d/override.conf > /dev/null <<EOF
[Service]
LimitNOFILE=1048576
LimitNPROC=1048576
LimitCORE=infinity
LimitNOFILE=infinity
LimitMEMLOCK=infinity
TasksMax=infinity
EOF

# 4. Docker daemon. json configuration
echo "⚙️  Configuring Docker daemon.json..."
sudo mkdir -p /etc/docker

# Backup existing daemon.json
if [ -f /etc/docker/daemon.json ]; then
    sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
fi

# Merge with existing config or create new one
if [ -f /etc/docker/daemon.json ]; then
    echo "⚠️  Existing daemon.json found.  Please manually merge these settings:"
    cat <<EOF
{
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 1048576,
      "Soft": 1048576
    },
    "nproc": {
      "Name": "nproc",
      "Hard": 1048576,
      "Soft": 1048576
    }
  },
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 10,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
else
    sudo tee /etc/docker/daemon. json > /dev/null <<EOF
{
  "default-ulimits": {
    "nofile": {
      "Name":  "nofile",
      "Hard": 1048576,
      "Soft": 1048576
    },
    "nproc": {
      "Name":  "nproc",
      "Hard": 1048576,
      "Soft": 1048576
    }
  },
  "max-concurrent-downloads":  10,
  "max-concurrent-uploads": 10,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
fi

# 5. Set conntrack modules to load on boot
echo "🔌 Configuring conntrack modules..."
sudo tee /etc/modules-load.d/conntrack. conf > /dev/null <<EOF
nf_conntrack
EOF

# Load conntrack module now
sudo modprobe nf_conntrack 2>/dev/null || true

# 6. Increase conntrack buckets (if module is loaded)
if [ -f /sys/module/nf_conntrack/parameters/hashsize ]; then
    echo "📊 Setting conntrack hashsize..."
    echo 524288 | sudo tee /sys/module/nf_conntrack/parameters/hashsize > /dev/null
    
    # Make it permanent
    sudo tee /etc/modprobe.d/nf_conntrack.conf > /dev/null <<EOF
options nf_conntrack hashsize=524288
EOF
fi

# 7. Reload and restart Docker
echo "🔄 Reloading systemd and restarting Docker..."
sudo systemctl daemon-reload
sudo systemctl restart docker

# 8. Wait for Docker to be ready
echo "⏳ Waiting for Docker to be ready..."
sleep 5

# Verify Docker is running
if sudo systemctl is-active --quiet docker; then
    echo "✅ Docker is running"
else
    echo "❌ Docker failed to start!  Check logs with: sudo journalctl -u docker -n 50"
    exit 1
fi

# Display current limits
echo ""
echo "✅ Maximum limits applied successfully!"
echo ""
echo "📊 Current System Limits:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "File descriptors (user):    $(ulimit -n)"
echo "File descriptors (hard):    $(ulimit -Hn)"
echo "Max open files (system):    $(cat /proc/sys/fs/file-max)"
echo "Max PIDs:                    $(cat /proc/sys/kernel/pid_max)"
echo "Inotify watches:            $(cat /proc/sys/fs/inotify/max_user_watches)"
echo "Inotify instances:          $(cat /proc/sys/fs/inotify/max_user_instances)"

if [ -f /proc/sys/net/netfilter/nf_conntrack_max ]; then
    echo "Conntrack max:              $(cat /proc/sys/net/netfilter/nf_conntrack_max)"
fi

if sudo docker info &>/dev/null; then
    echo ""
    echo "🐳 Docker Status:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    sudo docker info 2>/dev/null | grep -E "Containers:|Running:|Stopped:"
fi

echo ""
echo "⚠️  IMPORTANT: For user-level limits to take full effect:"
echo "   1. Log out and log back in (or reboot recommended)"
echo "   2. Verify with: ulimit -n"
echo ""
echo "🔍 Check Docker logs if issues persist:"
echo "   sudo journalctl -u docker -n 100 --no-pager"
echo ""
echo "📝 Backups created with . backup. <timestamp> extension"
echo ""
echo "🎯 System is now configured for maximum container capacity!"
