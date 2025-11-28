FROM alpine:3.19

# Install curl for downloading the binary and procps for health check
RUN apk add --no-cache curl procps

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

# Create non-root user
RUN adduser -D datagram
USER datagram

WORKDIR /home/datagram

# Health check - verify datagram conference process is running
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD ps aux | grep -v grep | grep -q "datagram-conference-cli" && exit 0 || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
