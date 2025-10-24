#!/bin/sh
set -e

  ln -sf /app/app/data/logos /app/frontend/static/images

# Starte das eigentliche CMD
exec "$@"
