"""
Initialize Celery app when Django starts.

This ensures the Celery app is loaded before any tasks are imported,
so the @shared_task decorator can use it.
"""

# Import Celery app so Django knows about it
from .celery import app as celery_app

__all__ = ('celery_app',)
