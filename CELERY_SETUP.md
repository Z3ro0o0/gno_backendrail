# Celery Setup Guide for Large File Uploads

This guide explains how to set up Celery for handling large Excel file uploads (10,000+ rows) with progress tracking.

## Prerequisites

1. Redis server (for Celery message broker)
2. Python packages: `celery` and `redis`

## Installation

### 1. Install Redis

**Windows:**
- Download from https://redis.io/download
- Or use WSL: `wsl sudo apt-get install redis-server`

**Linux/Mac:**
```bash
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis  # Mac
```

### 2. Install Python Packages

The packages are already in `requirements.txt`. Install them:
```bash
pip install celery>=5.3.0 redis>=5.0.0
```

## Configuration

### 1. Start Redis Server

**Windows (WSL):**
```bash
wsl redis-server
```

**Linux/Mac:**
```bash
redis-server
```

### 2. Update Environment Variables (Optional)

If Redis is not running on `localhost:6379`, set these in your environment:
```bash
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 3. Start Celery Worker

In a separate terminal, navigate to your Django project directory and run:

**Windows:**
```bash
cd backend/ong_backend
celery -A ong_backend worker --loglevel=info --pool=solo
```

**Linux/Mac:**
```bash
cd backend/ong_backend
celery -A ong_backend worker --loglevel=info
```

**Note:** On Windows, you MUST use `--pool=solo` because the default `prefork` pool doesn't work on Windows due to multiprocessing limitations.

For production, you may want to use a process manager like `supervisor` or `systemd`.

## How It Works

1. **File Size Detection**: When uploading, the system checks the number of rows
   - Files with **500+ rows**: Uses Celery for background processing
   - Files with **<500 rows**: Uses synchronous processing (faster for small files)

2. **Progress Tracking**: 
   - Large uploads return a `task_id` immediately
   - Frontend polls `/api/v1/trucking/upload-progress/<task_id>/` to get progress
   - Progress updates every 10 rows processed

3. **Benefits**:
   - No connection timeouts for large files
   - Real-time progress updates
   - Non-blocking - users can continue using the app
   - Handles 10,000+ row files efficiently

## Testing

1. Start Redis: `redis-server`
2. Start Celery worker: `celery -A ong_backend worker --loglevel=info`
3. Start Django server: `python manage.py runserver`
4. Upload a large Excel file (500+ rows)
5. Check the response - it should include `task_id` and `use_celery: true`
6. Poll the progress endpoint to see updates

## Troubleshooting

**Redis connection error:**
- Make sure Redis is running: `redis-cli ping` (should return `PONG`)
- Check Redis URL in settings matches your Redis instance

**Celery worker not processing tasks:**
- Make sure worker is running: `celery -A ong_backend worker --loglevel=info`
- Check logs for errors
- Verify Redis is accessible

**Progress not updating:**
- Check Redis is running and accessible
- Verify cache backend is working
- Check Celery worker logs for errors

## Production Deployment

For Railway or other cloud platforms:

1. **Add Redis service** to your Railway project
2. **Set environment variables**:
   ```
   CELERY_BROKER_URL=redis://your-redis-url:6379/0
   CELERY_RESULT_BACKEND=redis://your-redis-url:6379/0
   ```
3. **Start Celery worker** as a separate service/process in Railway
4. **Monitor** using Railway's logs

## Notes

- Progress data is stored in Redis cache and expires after 1 hour
- Temporary uploaded files are automatically deleted after processing
- The system falls back to synchronous processing if Celery is unavailable

