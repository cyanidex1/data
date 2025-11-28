#!/bin/bash

# Hard-coded image name
IMAGE_NAME="datagram:latest"

# Restart unhealthy containers for this image
unhealthy=$(docker ps \
  --filter "health=unhealthy" \
  --filter "ancestor=datagram:latest" \
  --format "{{.ID}}")

if [ -n "$unhealthy" ]; then
  for id in $unhealthy; do
    echo "Restarting unhealthy container $id (image: ${IMAGE_NAME})..."
    docker restart "$id"
  done
else
  echo "No unhealthy containers found for image ${IMAGE_NAME}."
fi

# Start exited containers for this image
exited=$(docker ps -a \
  --filter "status=exited" \
  --filter "ancestor=datagram:latest" \
  --format "{{.ID}}")

if [ -n "$exited" ]; then
  for id in $exited; do
    echo "Starting exited container $id (image: ${IMAGE_NAME})..."
    docker start "$id"
  done
else
  echo "No exited containers found for image ${IMAGE_NAME}."
fi
