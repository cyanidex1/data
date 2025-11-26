FROM ubuntu:20.04 AS base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
  apt-get install -y wget ca-certificates && \
  apt-get clean

# Install Datagram CLI
COPY datagram-cli-x86_64-linux /usr/bin/datagram
RUN chmod +x /usr/bin/datagram

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 CMD ps aux | grep -v grep | grep -q "/root/.datagram/conference/binaries/datagram-conference-cli-x86_64-linux" && exit 0 || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
