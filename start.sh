#!/bin/bash
# Start script that runs both Django web server and Celery worker in the same service

# Exit on error
set -e

# Start Celery worker in the background
echo "Starting Celery worker..."
celery -A ong_backend worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Shutting down..."
    kill $CELERY_PID 2>/dev/null || true
    exit
}

# Trap signals to cleanup
trap cleanup SIGTERM SIGINT

# Start Django web server in the foreground (Railway expects this to keep running)
echo "Starting Django web server..."
gunicorn ong_backend.wsgi:application --bind 0.0.0.0:${PORT:-8080}
