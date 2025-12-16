# Railway Single Service Deployment (Django + Celery)

This guide shows how to run both Django web server and Celery worker in the **same Railway service**.

## ✅ Advantages of Single Service

- **Simpler setup**: Only one service to manage
- **Lower cost**: One service instead of two
- **Easier environment variables**: Set once, works for both
- **Good for small/medium workloads**: Perfect for most use cases

## ⚠️ Considerations

- **Scaling**: Both processes scale together (can't scale web and worker independently)
- **Resource sharing**: Both processes share the same CPU/memory
- **Restarts**: Both restart together if one crashes

## Setup Steps

### 1. Add Redis Service

1. In Railway dashboard, click **"+ New"** → **"Database"** → **"Add Redis"**
2. Railway will automatically create Redis and provide `REDIS_URL` environment variable

### 2. Configure Environment Variables

In your Railway service, add these variables:

```bash
# Redis Configuration (Railway automatically provides these)
# Use REDIS_URL (internal) for services in same Railway project - faster and more secure
# REDIS_URL is automatically set by Railway when you add Redis service
# REDIS_PUBLIC_URL is also available if you need external access

# Celery Configuration (uses same Redis, different database numbers)
# Settings will automatically use REDIS_URL if available
CELERY_BROKER_URL=${REDIS_URL}/0
CELERY_RESULT_BACKEND=${REDIS_URL}/0
REDIS_CACHE_URL=${REDIS_URL}/1

# Note: Railway automatically sets REDIS_URL, so you might not need to set these manually
# But you can set them explicitly if needed

# Your existing Django variables
DATABASE_URL=postgresql://...
SECRET_KEY=...
# ... etc
```

**Note**: Railway supports variable interpolation, so `${REDIS_URL}/0` will work!

### 3. Update Procfile

Your `Procfile` should have:

```
web: bash start.sh
```

The `start.sh` script will run both processes.

### 4. Make start.sh Executable

Railway should handle this automatically, but if needed, add to your `build.sh`:

```bash
chmod +x start.sh
```

### 5. Deploy

1. Commit and push your changes
2. Railway will automatically deploy
3. Check logs - you should see:
   - "Starting Celery worker..."
   - "Starting Django web server..."
   - Both processes running

## How It Works

The `start.sh` script:
1. Starts Celery worker in the **background** (`&`)
2. Starts Django web server in the **foreground** (keeps service alive)
3. Handles cleanup on shutdown (kills Celery when Django stops)

## Monitoring

### Check Logs

In Railway dashboard, check your service logs. You should see:
- Celery worker logs (with `celery@hostname ready`)
- Django/Gunicorn logs (with HTTP requests)

### Verify Celery is Running

1. Upload a file with 100+ rows
2. Check logs for Celery task execution
3. Progress bar should update in frontend

## Troubleshooting

### Celery not starting?

1. Check logs for Celery errors
2. Verify `CELERY_BROKER_URL` is set correctly
3. Ensure Redis is accessible

### Both processes not running?

1. Check `start.sh` is executable
2. Verify Procfile has `web: bash start.sh`
3. Check Railway logs for startup errors

### Memory issues?

If you run out of memory:
- Reduce Celery concurrency: `--concurrency=1` (in start.sh)
- Or split into separate services (see RAILWAY_DEPLOYMENT.md)

## Resource Recommendations

For single service with both processes:
- **Minimum**: 512MB RAM
- **Recommended**: 1GB RAM
- **For heavy workloads**: 2GB+ RAM or split services

## When to Split Services

Consider separate services if:
- You need to scale web and worker independently
- You have high traffic (1000+ concurrent users)
- You need different resource allocations
- You want better isolation

Otherwise, **single service is perfect** for most use cases! 🚀

