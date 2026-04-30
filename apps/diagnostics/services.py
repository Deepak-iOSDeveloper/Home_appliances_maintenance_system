"""
Diagnostics Services — Matter Protocol Monitor & LSTM Anomaly Detection.

Uses simulated LSTM-based anomaly scoring with z-score analysis
on power/vibration/temperature time-series data.
"""
import random
import math
from django.utils import timezone
from .models import MatterNode, DiagnosticLog


def run_anomaly_detection():
    """
    Run anomaly detection across all Matter nodes.
    Generates simulated telemetry, computes z-scores, and flags anomalies.
    """
    nodes = MatterNode.objects.select_related('device').all()

    for node in nodes:
        # Generate metric types based on cluster
        metrics = _get_metrics_for_cluster(node.cluster_type)

        for metric_type, unit, baseline, std_dev in metrics:
            # Simulate a reading (mostly normal, occasionally anomalous)
            is_spike = random.random() < 0.15  # 15% chance of anomaly
            if is_spike:
                value = baseline + std_dev * random.uniform(2.5, 5.0) * random.choice([1, -1])
            else:
                value = baseline + random.gauss(0, std_dev * 0.5)

            z_score = abs(value - baseline) / std_dev if std_dev > 0 else 0
            is_anomalous = z_score > 2.5

            DiagnosticLog.objects.create(
                node=node,
                metric_type=metric_type,
                value=round(value, 2),
                unit=unit,
                is_anomalous=is_anomalous,
                z_score=round(z_score, 2),
            )

        # Update node anomaly score based on recent logs
        _update_node_anomaly_score(node)


def _get_metrics_for_cluster(cluster_type: str):
    """Return (metric_type, unit, baseline, std_dev) tuples for a cluster type."""
    cluster_metrics = {
        '0x002f': [  # Power Source
            ('power', 'W', 45.0, 10.0),
            ('voltage', 'V', 120.0, 5.0),
            ('current', 'A', 0.375, 0.1),
        ],
        '0x0101': [  # Door Lock
            ('power', 'W', 2.5, 0.5),
            ('signal_strength', 'dBm', -45.0, 10.0),
            ('error_count', '', 0.0, 1.0),
        ],
        '0x0201': [  # Thermostat
            ('temperature', '°C', 22.0, 2.0),
            ('power', 'W', 15.0, 5.0),
        ],
        '0x0006': [  # On/Off
            ('power', 'W', 8.0, 3.0),
        ],
        '0x0008': [  # Level Control
            ('power', 'W', 12.0, 4.0),
        ],
        '0x0402': [  # Temperature
            ('temperature', '°C', 22.0, 3.0),
        ],
        '0x0405': [  # Humidity
            ('vibration', 'm/s²', 0.1, 0.05),
        ],
    }
    return cluster_metrics.get(cluster_type, [('power', 'W', 10.0, 3.0)])


def _update_node_anomaly_score(node: MatterNode):
    """Compute LSTM-simulated anomaly score from recent diagnostic logs."""
    recent_logs = (
        DiagnosticLog.objects
        .filter(node=node)
        .order_by('-recorded_at')[:20]
    )

    if not recent_logs:
        return

    anomalous_count = sum(1 for l in recent_logs if l.is_anomalous)
    total = len(recent_logs)
    avg_z = sum(l.z_score for l in recent_logs) / total if total > 0 else 0

    # LSTM-simulated score: combines anomaly frequency + z-score severity
    frequency_factor = anomalous_count / total if total > 0 else 0
    severity_factor = min(1.0, avg_z / 4.0)  # Normalize z-score to 0-1

    # Weighted combination (simulates LSTM temporal pattern detection)
    anomaly_score = (frequency_factor * 0.6) + (severity_factor * 0.4)
    anomaly_score = round(min(1.0, max(0.0, anomaly_score)), 3)

    node.anomaly_score = anomaly_score
    node.save()
