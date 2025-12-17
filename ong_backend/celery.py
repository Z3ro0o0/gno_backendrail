"""
Celery configuration for background task processing
"""
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ong_backend.settings')

app = Celery('ong_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Configure broker transport options for better connection resilience
app.conf.broker_transport_options = {
    'visibility_timeout': 3600,  # 1 hour
    'socket_timeout': 30,
    'socket_connect_timeout': 30,
    'retry_on_timeout': True,
    'health_check_interval': 25,  # Check connection health every 25 seconds
}

# Configure result backend transport options
app.conf.result_backend_transport_options = {
    'retry_policy': {
        'timeout': 30.0,
    },
}

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

