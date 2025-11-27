FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI for building images
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY webapp/requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application files
COPY webapp/app.py .
COPY webapp/templates/ templates/

# Copy dockerfiles for node types
COPY dockerfiles/ /app/dockerfiles/

# Create data directory for persistent storage
RUN mkdir -p /data

# Copy and set up the startup script
COPY webapp/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Add user to docker group for socket access (GID will be mapped from host)
# This allows the container to communicate with Docker daemon
RUN groupadd -g 999 docker || true

# Expose port
EXPOSE 5000

# Run the startup script which builds images and starts the app
CMD ["/app/startup.sh"]
