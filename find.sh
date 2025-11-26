#!/bin/bash

for cid in $(docker ps -q); do
  cname=$(docker inspect --format '{{.Name}}' "$cid" | sed 's#^/##')
  docker logs "$cid" 2>&1 | grep -oP 'key: \K[a-f0-9]{32}' | while read -r key; do
    echo "$cname: $key"
  done
done | sort | uniq
