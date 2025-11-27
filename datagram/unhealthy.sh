#!/bin/bash

# Restart unhealthy containers
unhealthy=$(docker ps --filter "health=unhealthy" --format "{{.ID}}")
if [ -n "$unhealthy" ]; then
    for id in $unhealthy; do
        echo "Restarting unhealthy container $id..."
        docker restart "$id"
    done
else
    echo "No unhealthy containers found."
fi

# Start exited containers
exited=$(docker ps -a --filter "status=exited" --format "{{.ID}}")
if [ -n "$exited" ]; then
    for id in $exited; do
        echo "Starting exited container $id..."
        docker start "$id"
    done
else
    echo "No exited containers found."
fi
