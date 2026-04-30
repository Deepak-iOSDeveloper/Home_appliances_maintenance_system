"""Diagnostics Celery Tasks"""
from celery import shared_task


@shared_task(name='diagnostics.run_anomaly_detection')
def run_anomaly_detection_task():
    """Periodic task to run anomaly detection across all Matter nodes."""
    from .services import run_anomaly_detection
    run_anomaly_detection()
    return {'status': 'complete'}
