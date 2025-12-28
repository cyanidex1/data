FROM alpine:3.19

# Install curl for downloading the binary, procps for health check
RUN apk add --no-cache curl procps

# Env for license key (pass at runtime)
ENV LICENSE_KEY=""

# Download binary from GitHub releases
RUN curl -fsSL \
  "https://github.com/Datagram-Group/datagram-cli-release/releases/latest/download/datagram-cli-x86_64-linux" \
  -o /usr/local/bin/datagram && \
  chmod +x /usr/local/bin/datagram

# Pre-download Conference CLI tools using test key (92bcf2ae4e326968f40f8670a3596b80)
# Note: VPN CLI requires privileged mode and will be downloaded on first run
# This pre-downloads the Conference CLI to save time on container startup
# The 90-second sleep allows time for the CLI download to complete before killing the process
RUN /usr/local/bin/datagram run -- -key 92bcf2ae4e326968f40f8670a3596b80 & \
  PID=$! && \
  sleep 90 && \
  kill $PID 2>/dev/null || true && \
  wait $PID 2>/dev/null || true

# Copy entrypoint script
COPY datagram-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /root

# Health check - verify datagram conference process is running
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD ps aux | grep -v grep | grep -q "datagram" && exit 0 || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
