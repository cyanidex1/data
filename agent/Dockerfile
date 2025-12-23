# Lightweight agent for managing Docker containers
# Target size: ~50MB

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent script
COPY agent.py .

# Create non-root user for security
RUN useradd -m -u 1000 agent && \
    chown -R agent:agent /app

# Switch to non-root user
USER agent

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the agent
ENTRYPOINT ["python", "agent.py"]
