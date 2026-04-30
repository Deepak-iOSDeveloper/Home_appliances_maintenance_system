"""Dashboard Celery Tasks"""
from celery import shared_task


@shared_task(name='dashboard.calculate_health_score')
def calculate_health_score_task():
    """Periodic task to recalculate the Residential Health Score."""
    from .services import calculate_health_score
    snapshot = calculate_health_score()
    return {'score': snapshot.score, 'grade': snapshot.grade}
