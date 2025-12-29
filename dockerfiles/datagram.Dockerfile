FROM alpine:3.19

# Install curl for downloading the binary, procps for health check
# Install wireguard-tools for wg command and interface management
# Install iptables for network routing
RUN apk add --no-cache curl procps wireguard-tools iptables ip6tables

# Env for license key (pass at runtime)
ENV LICENSE_KEY=""

# Download binary from GitHub releases
RUN curl -fsSL \
  "https://github.com/Datagram-Group/datagram-cli-release/releases/latest/download/datagram-cli-x86_64-linux" \
  -o /usr/local/bin/datagram && \
  chmod +x /usr/local/bin/datagram

# Copy pre-downloaded VPN and Conference CLI binaries
# These binaries are extracted from a privileged container run by download-binaries.sh
# Run ./download-binaries.sh before building this image to populate the binaries directory
COPY binaries/.datagram /root/.datagram

# Copy entrypoint script
COPY datagram-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /root

# Health check - verify datagram conference process is running
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD ps aux | grep -v grep | grep -q "datagram" && exit 0 || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
