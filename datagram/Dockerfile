FROM alpine:3.19

# Install curl for downloading the binary, procps for health check, and sudo for VPN services
RUN apk add --no-cache curl procps sudo

# Env for license key (pass at runtime)
ENV LICENSE_KEY=""

# Download binary from GitHub releases
RUN curl -fsSL \
  "https://github.com/Datagram-Group/datagram-cli-release/releases/latest/download/datagram-cli-x86_64-linux" \
  -o /usr/local/bin/datagram && \
  chmod +x /usr/local/bin/datagram

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Create non-root user and configure sudo
# Note: Granting ALL sudo access for VPN services. In production, consider
# restricting to specific commands if you know which ones are needed:
# datagram ALL=(ALL) NOPASSWD: /sbin/ip, /usr/bin/openvpn, /usr/bin/wireguard
# This provides full sudo inside the container only (not on the host).
RUN adduser -D datagram && \
    echo "datagram ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/datagram && \
    chmod 0440 /etc/sudoers.d/datagram

USER datagram

WORKDIR /home/datagram

# Health check - verify datagram conference process is running
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD ps aux | grep -v grep | grep -q "datagram-conference-cli" && exit 0 || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
