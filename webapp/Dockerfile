FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application files
COPY app.py .
COPY templates/ templates/

# Create data directory for persistent storage
RUN mkdir -p /data

# Add user to docker group for socket access (GID will be mapped from host)
# This allows the container to communicate with Docker daemon
RUN groupadd -g 999 docker || true

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
