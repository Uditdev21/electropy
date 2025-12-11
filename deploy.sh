#!/bin/bash

SERVICE="battery_monitor"

echo "🔹 Stopping running container..."
docker compose stop $SERVICE

echo "🔹 Removing old container..."
docker compose rm -f $SERVICE

echo "🔹 Rebuilding Docker image..."
docker compose build $SERVICE

echo "🔹 Starting new container..."
docker compose up -d $SERVICE

echo "🔹 Deployment complete."
echo "🔹 Showing latest logs..."

sleep 2
docker compose logs -f $SERVICE
