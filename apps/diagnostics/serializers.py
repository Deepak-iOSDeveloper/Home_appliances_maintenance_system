"""Diagnostics Serializers"""
from rest_framework import serializers
from .models import MatterNode, DiagnosticLog


class DiagnosticLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticLog
        fields = [
            'id', 'metric_type', 'value', 'unit',
            'recorded_at', 'is_anomalous', 'z_score',
        ]


class MatterNodeSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_type = serializers.CharField(source='device.device_type', read_only=True)
    room_name = serializers.CharField(source='device.room.name', read_only=True)
    cluster_display = serializers.CharField(source='get_cluster_type_display', read_only=True)
    health_display = serializers.CharField(source='get_health_status_display', read_only=True)
    recent_logs = DiagnosticLogSerializer(
        source='diagnostic_logs', many=True, read_only=True
    )

    class Meta:
        model = MatterNode
        fields = [
            'id', 'device', 'device_name', 'device_type', 'room_name',
            'node_id', 'endpoint_id', 'cluster_type', 'cluster_display',
            'cluster_name', 'health_status', 'health_display',
            'anomaly_score', 'last_diagnostic', 'attributes',
            'recent_logs', 'created_at',
        ]


class MatterNodeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (no nested logs)."""
    device_name = serializers.CharField(source='device.name', read_only=True)
    room_name = serializers.CharField(source='device.room.name', read_only=True)

    class Meta:
        model = MatterNode
        fields = [
            'id', 'device_name', 'room_name', 'node_id',
            'endpoint_id', 'cluster_type', 'cluster_name',
            'health_status', 'anomaly_score', 'last_diagnostic',
        ]
