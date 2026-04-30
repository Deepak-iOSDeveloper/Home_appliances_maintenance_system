"""
Diagnostics Models — Hardware Intelligence
Tracks Matter Protocol clusters and diagnostic telemetry with anomaly scoring.
"""
import uuid
from django.db import models


class MatterNode(models.Model):
    """
    Represents a Matter Protocol endpoint/cluster on a device.
    Maps to real Matter clusters (e.g., Power Source 0x002f, Door Lock 0x0101).
    """

    HEALTH_CHOICES = [
        ('healthy', 'Healthy'),
        ('degraded', 'Degraded'),
        ('critical', 'Critical'),
    ]

    CLUSTER_TYPES = [
        ('0x0006', 'On/Off'),
        ('0x0008', 'Level Control'),
        ('0x0028', 'Basic Information'),
        ('0x002f', 'Power Source'),
        ('0x0101', 'Door Lock'),
        ('0x0201', 'Thermostat'),
        ('0x0300', 'Color Control'),
        ('0x0400', 'Illuminance Measurement'),
        ('0x0402', 'Temperature Measurement'),
        ('0x0405', 'Relative Humidity'),
        ('0x0406', 'Occupancy Sensing'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        'dashboard.Device', on_delete=models.CASCADE,
        related_name='matter_nodes'
    )
    node_id = models.CharField(max_length=20, help_text='Matter Node ID')
    endpoint_id = models.IntegerField(default=0, help_text='Matter Endpoint (0 = root)')
    cluster_type = models.CharField(
        max_length=10, choices=CLUSTER_TYPES,
        help_text='Matter Cluster ID (hex)'
    )
    cluster_name = models.CharField(max_length=100, blank=True)
    health_status = models.CharField(
        max_length=20, choices=HEALTH_CHOICES, default='healthy'
    )
    anomaly_score = models.FloatField(
        default=0.0,
        help_text='LSTM-based anomaly score (0.0 = normal, 1.0 = critical)'
    )
    last_diagnostic = models.DateTimeField(auto_now=True)
    attributes = models.JSONField(
        default=dict, blank=True,
        help_text='Cluster-specific attribute values'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-anomaly_score']
        unique_together = ['device', 'endpoint_id', 'cluster_type']
        indexes = [
            models.Index(fields=['health_status']),
            models.Index(fields=['anomaly_score']),
        ]

    def save(self, *args, **kwargs):
        # Auto-populate cluster_name from choices
        if not self.cluster_name:
            for code, name in self.CLUSTER_TYPES:
                if code == self.cluster_type:
                    self.cluster_name = name
                    break
        # Auto-calculate health status from anomaly score
        if self.anomaly_score >= 0.8:
            self.health_status = 'critical'
        elif self.anomaly_score >= 0.5:
            self.health_status = 'degraded'
        else:
            self.health_status = 'healthy'
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Node {self.node_id} EP{self.endpoint_id} "
            f"[{self.cluster_type} {self.cluster_name}] — {self.health_status}"
        )


class DiagnosticLog(models.Model):
    """
    Time-series telemetry log for a Matter node.
    Stores power, vibration, temperature readings with anomaly flags.
    """

    METRIC_TYPES = [
        ('power', 'Power (W)'),
        ('vibration', 'Vibration (m/s²)'),
        ('temperature', 'Temperature (°C)'),
        ('voltage', 'Voltage (V)'),
        ('current', 'Current (A)'),
        ('signal_strength', 'Signal Strength (dBm)'),
        ('error_count', 'Error Count'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    node = models.ForeignKey(
        MatterNode, on_delete=models.CASCADE,
        related_name='diagnostic_logs'
    )
    metric_type = models.CharField(max_length=30, choices=METRIC_TYPES)
    value = models.FloatField()
    unit = models.CharField(max_length=20)
    recorded_at = models.DateTimeField(auto_now_add=True)
    is_anomalous = models.BooleanField(default=False)
    z_score = models.FloatField(
        default=0.0,
        help_text='Statistical z-score from baseline'
    )

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['metric_type', 'recorded_at']),
            models.Index(fields=['is_anomalous']),
        ]

    def __str__(self):
        flag = " ⚠️" if self.is_anomalous else ""
        return f"{self.node.node_id} {self.metric_type}: {self.value}{self.unit}{flag}"
