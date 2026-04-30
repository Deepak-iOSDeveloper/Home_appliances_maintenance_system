"""Observability Views — MLOps Dashboard API"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Max, Sum

from .models import ThoughtTrace, SessionMetric
from .serializers import ThoughtTraceSerializer, SessionMetricSerializer


class ThoughtTraceViewSet(viewsets.ReadOnlyModelViewSet):
    """View thought traces for agentic pipeline visualization."""
    serializer_class = ThoughtTraceSerializer

    def get_queryset(self):
        qs = ThoughtTrace.objects.select_related('session', 'message')
        session_id = self.request.query_params.get('session')
        if session_id:
            qs = qs.filter(session_id=session_id)
        return qs


class SessionMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """View session-level performance metrics."""
    serializer_class = SessionMetricSerializer

    def get_queryset(self):
        return SessionMetric.objects.select_related('session').all()

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """Aggregated metrics across all sessions."""
        metrics = SessionMetric.objects.aggregate(
            avg_latency=Avg('total_latency_ms'),
            max_latency=Max('total_latency_ms'),
            avg_p95=Avg('p95_latency_ms'),
            total_tokens=Sum('total_tokens'),
            total_cost=Sum('estimated_cost_usd'),
            avg_steps=Avg('steps_count'),
        )
        metrics['session_count'] = SessionMetric.objects.count()
        return Response(metrics)
