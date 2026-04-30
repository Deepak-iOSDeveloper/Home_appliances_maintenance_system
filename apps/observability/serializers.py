"""Observability Serializers"""
from rest_framework import serializers
from .models import ThoughtTrace, SessionMetric


class ThoughtTraceSerializer(serializers.ModelSerializer):
    step_type_display = serializers.CharField(
        source='get_step_type_display', read_only=True
    )

    class Meta:
        model = ThoughtTrace
        fields = [
            'id', 'session', 'message', 'step_order',
            'step_type', 'step_type_display', 'agent_name',
            'input_summary', 'output_summary',
            'duration_ms', 'token_count', 'tools_used',
            'raw_output', 'created_at',
        ]


class SessionMetricSerializer(serializers.ModelSerializer):
    session_title = serializers.CharField(
        source='session.title', read_only=True
    )
    session_id = serializers.CharField(
        source='session.session_id', read_only=True
    )

    class Meta:
        model = SessionMetric
        fields = [
            'id', 'session', 'session_id', 'session_title',
            'total_latency_ms', 'p95_latency_ms',
            'total_tokens', 'prompt_tokens', 'completion_tokens',
            'estimated_cost_usd', 'steps_count',
            'retrieval_count', 'tools_invoked',
            'created_at', 'updated_at',
        ]
