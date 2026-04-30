"""
Agent Tools — Functions that agents can invoke to gather data.
Bridges the AI layer with the Django data layer.
"""
import json
from django.db.models import Q
from asgiref.sync import sync_to_async


async def fetch_device_status(device_name: str) -> dict:
    """Fetch device status from the Dashboard by name (case-insensitive)."""
    from apps.dashboard.models import Device

    @sync_to_async
    def _query():
        devices = (
            Device.objects.select_related('room')
            .filter(Q(name__icontains=device_name) | Q(device_type__icontains=device_name))
        )
        if not devices.exists():
            return {'found': False, 'error': f'No device matching "{device_name}" found.'}
        device = devices.first()
        return {
            'found': True, 'id': str(device.id), 'name': device.name,
            'device_type': device.device_type, 'manufacturer': device.manufacturer,
            'model_number': device.model_number, 'firmware_version': device.firmware_version,
            'room': device.room.name, 'status': device.status,
            'power_consumption_watts': device.power_consumption_watts,
            'battery_level': device.battery_level, 'is_reachable': device.is_reachable,
            'last_seen': str(device.last_seen), 'metadata': device.metadata,
        }
    return await _query()


async def fetch_diagnostic_data(device_name: str) -> dict:
    """Fetch Matter Protocol diagnostic data including anomaly scores and logs."""
    from apps.dashboard.models import Device
    from apps.diagnostics.models import MatterNode, DiagnosticLog

    @sync_to_async
    def _query():
        devices = Device.objects.filter(
            Q(name__icontains=device_name) | Q(device_type__icontains=device_name)
        )
        if not devices.exists():
            return {'found': False, 'error': f'No diagnostic data for "{device_name}".'}
        device = devices.first()
        nodes = MatterNode.objects.filter(device=device).order_by('-anomaly_score')
        if not nodes.exists():
            return {'found': True, 'device_name': device.name, 'nodes': [], 'summary': 'No Matter nodes registered.'}
        node_data = []
        for node in nodes:
            logs = DiagnosticLog.objects.filter(node=node).order_by('-recorded_at')[:10]
            node_data.append({
                'node_id': node.node_id, 'endpoint': node.endpoint_id,
                'cluster': f"{node.cluster_type} ({node.cluster_name})",
                'health_status': node.health_status,
                'anomaly_score': round(node.anomaly_score, 3),
                'recent_logs': [
                    {'metric': l.metric_type, 'value': l.value, 'unit': l.unit,
                     'anomalous': l.is_anomalous, 'z_score': round(l.z_score, 2)}
                    for l in logs
                ]
            })
        critical = sum(1 for n in node_data if n['health_status'] == 'critical')
        degraded = sum(1 for n in node_data if n['health_status'] == 'degraded')
        summary = f"Clusters: {critical} critical, {degraded} degraded, {len(node_data) - critical - degraded} healthy."
        return {'found': True, 'device_name': device.name, 'nodes': node_data, 'summary': summary}
    return await _query()


async def search_manuals(query: str, top_k: int = 3) -> list:
    """Semantic search across TechnicalManual chunks (keyword fallback)."""
    from apps.troubleshooter.models import TechnicalManual

    @sync_to_async
    def _search():
        keywords = query.lower().split()
        q_filter = Q()
        for kw in keywords:
            if len(kw) > 2:
                q_filter |= Q(content__icontains=kw) | Q(title__icontains=kw)
        manuals = TechnicalManual.objects.filter(q_filter)[:top_k]
        results = [
            {'id': str(m.id), 'title': m.title, 'brand': m.brand, 'device_type': m.device_type,
             'content': m.content, 'chunk_index': m.chunk_index, 'relevance_score': 0.85}
            for m in manuals
        ]
        if not results:
            return [{'title': 'No Documentation Found',
                     'content': 'No technical manual found. Cannot provide grounded instructions.',
                     'relevance_score': 0.0}]
        return results
    return await _search()


async def fetch_error_logs(device_name: str, limit: int = 5) -> list:
    """Fetch recent anomalous diagnostic logs for a device."""
    from apps.dashboard.models import Device
    from apps.diagnostics.models import DiagnosticLog

    @sync_to_async
    def _query():
        devices = Device.objects.filter(
            Q(name__icontains=device_name) | Q(device_type__icontains=device_name)
        )
        if not devices.exists():
            return []
        device = devices.first()
        logs = (DiagnosticLog.objects.filter(node__device=device, is_anomalous=True)
                .select_related('node').order_by('-recorded_at')[:limit])
        return [
            {'cluster': f"{l.node.cluster_type} ({l.node.cluster_name})",
             'metric': l.metric_type, 'value': l.value, 'unit': l.unit,
             'z_score': round(l.z_score, 2), 'time': str(l.recorded_at)}
            for l in logs
        ]
    return await _query()
