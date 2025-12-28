# Building the Datagram Docker Image

This directory contains the Dockerfile and scripts for building the Datagram node image with pre-downloaded CLI binaries.

## Quick Start

### Step 1: Download Binaries

Before building the Docker image, you need to download the VPN and Conference CLI binaries:

```bash
./download-binaries.sh
```

This script will:
1. Create a temporary Docker image with the datagram CLI
2. Start a privileged container to trigger both VPN and Conference CLI downloads
3. Extract the binaries to the `binaries/.datagram/` directory
4. Clean up the temporary container

**Note:** This step requires Docker with privileged container support.

### Step 2: Build the Image

Once the binaries are downloaded, build the Docker image:

```bash
docker build --platform linux/amd64 -t datagram .
```

## Why This Approach?

Previously, the Dockerfile attempted to download CLI binaries during the image build using `RUN` commands. However:

- **Conference CLI** could be downloaded during build (no privileged mode required)
- **VPN CLI** requires privileged mode, which is not available during Docker build

By using a helper script that runs a privileged container first, we can extract **both** binaries and include them in the final image. This means:

✅ No downloads at container startup (both Conference and VPN CLI pre-installed)
✅ Faster container startup times
✅ Works with any license key
✅ No repeated downloads when creating multiple containers

## Directory Structure

```
datagram/
├── Dockerfile                 # Main Dockerfile that copies pre-downloaded binaries
├── download-binaries.sh       # Script to download binaries from privileged container
├── binaries/                  # Auto-generated directory (gitignored)
│   └── .datagram/
│       ├── conference/        # Conference CLI and dependencies
│       └── vpn/              # VPN CLI and dependencies
├── entrypoint.sh             # Container entrypoint
└── BUILD.md                  # This file
```

## Troubleshooting

### Binaries directory not found

If you see an error like:
```
COPY failed: file not found in build context
```

Make sure you've run `./download-binaries.sh` before building the image.

### Download script fails

The download script requires:
- Docker with privileged container support
- Network access to download the datagram CLI
- At least 200MB of free disk space

### Binaries are outdated

To refresh the binaries:
```bash
rm -rf binaries/
./download-binaries.sh
docker build --platform linux/amd64 -t datagram .
```

## Automated Build

For CI/CD pipelines, you can combine both steps:

```bash
#!/bin/bash
set -e

# Download binaries if not already present
if [ ! -d "binaries/.datagram" ]; then
  ./download-binaries.sh
fi

# Build the image
docker build --platform linux/amd64 -t datagram .
```
