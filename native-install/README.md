# Datagram Native Installation

This directory contains files for installing and running Datagram natively on your Linux host system (not in Docker containers).

## Quick Start

```bash
# 1. Initialize (run once)
sudo ./datagram-manager.sh init

# 2. Add and start an instance
sudo ./datagram-manager.sh quick-add 92bcf2ae4e326968f40f8670a3596b80

# 3. List instances
sudo ./datagram-manager.sh list

# 4. View logs
sudo ./datagram-manager.sh logs node0
```

## Files

- **datagram-manager.sh** - Management script for datagram instances
- **datagram@.service** - Systemd service template
- **NATIVE_INSTALL.md** - Complete installation and usage guide

## Documentation

See [NATIVE_INSTALL.md](NATIVE_INSTALL.md) for:
- Complete installation guide
- Usage examples
- Troubleshooting
- Advanced configuration
- Security considerations

## What This Does

When you run `sudo datagram run -- -key <your-key>`, it creates network interfaces like:
- wg0 (first instance)
- wg1 (second instance)  
- wg2 (third instance)
- etc.

This native installation provides:
- ✅ Systemd service management
- ✅ Auto-start on boot
- ✅ Multiple instances with unique interface names
- ✅ Easy management via command-line interface
- ✅ Automatic capability and permission handling

## When to Use Native vs Docker

**Use Native Installation when:**
- You want direct host access without container overhead
- You prefer systemd service management
- You need simpler networking (interfaces directly on host)
- You're comfortable with Linux system administration

**Use Docker Installation when:**
- You want full isolation between instances
- You prefer web UI management (see main README)
- You need cross-platform deployment
- You want easier setup and teardown

## Support

For detailed help, see [NATIVE_INSTALL.md](NATIVE_INSTALL.md) or the main [README.md](../README.md).
