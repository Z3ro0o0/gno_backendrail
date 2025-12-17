#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Create temp_uploads directory for file uploads
mkdir -p temp_uploads

# Make start.sh executable
chmod +x start.sh



