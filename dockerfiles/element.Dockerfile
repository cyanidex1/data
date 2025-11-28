FROM alpine:3.19

# Install required packages
RUN apk add --no-cache wget expect curl ca-certificates bash procps

# Environment variables for credentials (passed at runtime)
ENV NODE_EMAIL=""
ENV NODE_PASSWORD=""
ENV NODE_NAME="element-node"

# Node configuration
ENV BRAND="element"
ENV CHAIN="element"
ENV DOMAIN="elementunited.com"
ENV VERSION="v2.6.1-b"

# Copy entrypoint script
COPY element-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Create non-root user
RUN adduser -D nodeuser
USER nodeuser

WORKDIR /home/nodeuser

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD ps aux | grep -v grep | grep -q "$CHAIN" && exit 0 || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
