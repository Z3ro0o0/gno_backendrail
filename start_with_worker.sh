#!/bin/bash
# Start script that runs both Django web server and Celery worker in the same service

# Create temp_uploads directory if it doesn't exist
mkdir -p /app/temp_uploads

# Start Celery worker in the background
celery -A ong_backend worker --loglevel=info --concurrency=2 &

# Start Django web server in the foreground
gunicorn ong_backend.wsgi:application --bind 0.0.0.0:${PORT:-8080}

