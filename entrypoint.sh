#!/bin/sh
set -e

echo "Checking logos directory..."
if [ -d /app/app/data/logos ]; then
    echo "Copying logos to static/images..."
    mkdir -p /app/frontend/static/images
    cp -r /app/app/data/logos/* /app/frontend/static/images/ 2>/dev/null || true
    chown -R appuser:appuser /app/frontend/static/images
else
    echo "No logos found in /app/app/data/logos"
fi

echo "Starting application..."
exec "$@"
