# ARHIS — Autonomous Residential Health and Intelligence System
from .celery_app import app as celery_app

__all__ = ('celery_app',)
