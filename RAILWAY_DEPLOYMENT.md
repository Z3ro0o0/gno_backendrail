# Railway Deployment Guide for Django + Celery + Redis

This guide explains how to deploy your Django backend with Celery worker and Redis on Railway.

## Overview

Railway allows you to run multiple services from the same repository. You'll need:
1. **Web Service**: Your Django application (already deployed)
2. **Worker Service**: Celery worker for background tasks
3. **Redis Service**: For Celery broker and cache (Railway's Redis or Upstash)

## Step 1: Add Redis Service to Railway

### Option A: Use Railway's Redis Plugin (Recommended)

1. Go to your Railway project dashboard
2. Click **"+ New"** → **"Database"** → **"Add Redis"**
3. Railway will automatically create a Redis instance
4. Note the connection URL (will be available as `REDIS_URL` environment variable)

### Option B: Use Upstash Redis (Free tier available)

1. Go to [Upstash Console](https://console.upstash.com/)
2. Create a new Redis database
3. Copy the connection URL (format: `redis://default:password@host:port`)

## Step 2: Configure Environment Variables

In your Railway project, add these environment variables:

### Required Variables:

```bash
# Redis Configuration (from Railway Redis or Upstash)
REDIS_URL=redis://default:password@host:port

# Celery Configuration (use same Redis, different database numbers)
CELERY_BROKER_URL=redis://default:password@host:port/0
CELERY_RESULT_BACKEND=redis://default:password@host:port/0
REDIS_CACHE_URL=redis://default:password@host:port/1

# Django Settings (your existing variables)
DATABASE_URL=postgresql://...
SECRET_KEY=...
# ... other Django settings
```

### How to Set Environment Variables:

1. Go to your Railway project
2. Click on your **Web Service**
3. Go to **"Variables"** tab
4. Add all the variables above
5. **Important**: Also add them to your **Worker Service** (created in Step 3)

## Step 3: Add Celery Worker Service

### Method 1: Using Railway Dashboard (Easiest)

1. In your Railway project, click **"+ New"** → **"Empty Service"**
2. Name it: `celery-worker` or `worker`
3. Connect it to the same GitHub repository
4. Set the **Root Directory** to: `backend/ong_backend`
5. Set the **Start Command** to: `celery -A ong_backend worker --loglevel=info --concurrency=2`
6. Add all the same environment variables from your Web Service
7. Deploy

### Method 2: Using railway.json (Advanced)

Create `railway.json` in your project root:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn ong_backend.wsgi:application --bind 0.0.0.0:$PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Then in Railway dashboard:
1. Add a new service
2. Railway will automatically detect the Procfile
3. The `worker` process will be available as a separate service

## Step 4: Verify Procfile

Your `Procfile` should have:

```
web: gunicorn ong_backend.wsgi:application --bind 0.0.0.0:8080
worker: celery -A ong_backend worker --loglevel=info --concurrency=2
```

## Step 5: Update Settings for Production

Make sure your `settings.py` handles Railway's environment:

```python
# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
REDIS_CACHE_URL = os.environ.get('REDIS_CACHE_URL', os.environ.get('REDIS_URL', 'redis://localhost:6379/1'))
```

## Step 6: Deploy and Test

1. **Commit and push** your changes to GitHub
2. Railway will automatically deploy both services
3. Check logs:
   - Web service logs: Should show Django starting
   - Worker service logs: Should show `celery@hostname ready`
4. Test by uploading a file with 100+ rows

## Troubleshooting

### Worker not starting?

1. Check worker service logs in Railway dashboard
2. Verify environment variables are set in **both** web and worker services
3. Ensure `CELERY_BROKER_URL` is correct
4. Check that Redis is accessible

### Connection errors?

1. Verify Redis URL is correct
2. Check Redis is running (Railway dashboard)
3. Ensure database numbers are different:
   - Database 0: Celery broker/backend
   - Database 1: Django cache

### Tasks not executing?

1. Check worker logs for errors
2. Verify `CELERY_BROKER_URL` matches in both services
3. Check Redis connection
4. Ensure worker service is running (not paused)

## Railway Service Structure

```
Your Project
├── Web Service (Django)
│   ├── Port: 8080 (or $PORT)
│   ├── Command: gunicorn ong_backend.wsgi:application
│   └── Env: All Django + Celery variables
│
├── Worker Service (Celery)
│   ├── Command: celery -A ong_backend worker
│   └── Env: All Django + Celery variables (same as web)
│
└── Redis Service
    ├── Type: Railway Redis or Upstash
    └── URL: Available as REDIS_URL
```

## Cost Considerations

- **Railway Redis**: ~$5-10/month (depending on usage)
- **Upstash Redis**: Free tier available (10K commands/day)
- **Worker Service**: Uses same pricing as web service

## Monitoring

1. **Web Service**: Check Railway dashboard for logs
2. **Worker Service**: Check Railway dashboard for logs
3. **Redis**: Check Railway/Upstash dashboard for metrics
4. **Celery Tasks**: Check progress via `/api/v1/trucking/upload-progress/<task_id>/`

## Quick Checklist

- [ ] Redis service added (Railway or Upstash)
- [ ] Environment variables set in Web Service
- [ ] Environment variables set in Worker Service
- [ ] Procfile updated with worker command
- [ ] Worker service created in Railway
- [ ] Both services deployed successfully
- [ ] Test upload with 100+ rows
- [ ] Verify progress bar works

## Support

If you encounter issues:
1. Check Railway service logs
2. Verify all environment variables are set
3. Ensure Redis is accessible from both services
4. Check Celery worker is running (logs should show "ready")

