#!/bin/sh

# Exit on error
set -e

# Run migrations if enabled (Standard for Cloud Run "one-click" setup)
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🔄 Running database migrations..."
    alembic upgrade head
fi

# Start uvicorn
echo "🚀 Starting BarberSync API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
