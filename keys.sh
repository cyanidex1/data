#!/bin/bash

# Temporary file to collect keys
tmpfile=$(mktemp)

for cid in $(docker ps -q); do
  cname=$(docker inspect --format '{{.Name}}' "$cid" | sed 's#^/##')
  docker logs "$cid" 2>&1 | grep -oP 'key: \K[a-f0-9]{32}' | while read -r key; do
    echo "$cname: $key"
    echo "$key" >> "$tmpfile"
  done
done | sort | uniq

# Only unique keys are saved to keys.txt
sort "$tmpfile" | uniq > keys.txt
rm "$tmpfile"

echo "Unique keys saved to keys.txt"
