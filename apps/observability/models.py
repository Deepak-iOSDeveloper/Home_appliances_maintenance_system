"""
Observability Models — MLOps Proof
Tracks AI thought traces and session-level performance metrics.
"""
import uuid
from django.db import models


class ThoughtTrace(models.Model):
    """
    Records each step in the agentic reasoning pipeline.
    Captures the full Intent → Diagnostic → Retrieval → Response flow.
    """

    STEP_TYPES = [
        ('intent', 'Intent Classification'),
        ('diagnostic', 'Hardware Diagnostics'),
        ('retrieval', 'Knowledge Retrieval'),
        ('response', 'Response Synthesis'),
        ('tool_call', 'Tool Invocation'),
        ('error', 'Error Recovery'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        'troubleshooter.ChatSession', on_delete=models.CASCADE,
        related_name='thought_traces'
    )
    message = models.ForeignKey(
        'troubleshooter.Message', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='traces'
    )
    step_order = models.IntegerField(help_text='Execution order within the pipeline')
    step_type = models.CharField(max_length=20, choices=STEP_TYPES)
    agent_name = models.CharField(max_length=100, blank=True, help_text='Which agent handled this step')
    input_summary = models.TextField(blank=True, help_text='Summarized input to this step')
    output_summary = models.TextField(blank=True, help_text='Summarized output from this step')
    duration_ms = models.IntegerField(default=0, help_text='Step execution time in milliseconds')
    token_count = models.IntegerField(default=0, help_text='Tokens consumed in this step')
    tools_used = models.JSONField(
        default=list, blank=True,
        help_text='List of tools invoked during this step'
    )
    raw_output = models.JSONField(
        default=dict, blank=True,
        help_text='Full raw output for debugging'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['session', 'step_order']
        indexes = [
            models.Index(fields=['step_type']),
            models.Index(fields=['session', 'step_order']),
        ]

    def __str__(self):
        return (
            f"Trace #{self.step_order} [{self.get_step_type_display()}] "
            f"— {self.duration_ms}ms, {self.token_count} tokens"
        )


class SessionMetric(models.Model):
    """
    Aggregated performance metrics per troubleshooting session.
    Powers the observability dashboard charts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(
        'troubleshooter.ChatSession', on_delete=models.CASCADE,
        related_name='metrics'
    )
    total_latency_ms = models.IntegerField(default=0, help_text='End-to-end response time')
    p95_latency_ms = models.IntegerField(default=0, help_text='P95 latency across steps')
    total_tokens = models.IntegerField(default=0)
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    estimated_cost_usd = models.FloatField(default=0.0)
    steps_count = models.IntegerField(default=0)
    retrieval_count = models.IntegerField(default=0, help_text='Number of RAG retrievals')
    tools_invoked = models.IntegerField(default=0, help_text='Total tool calls')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Metrics for {self.session.session_id[:8]}: "
            f"{self.total_latency_ms}ms, {self.total_tokens} tokens, "
            f"${self.estimated_cost_usd:.4f}"
        )
