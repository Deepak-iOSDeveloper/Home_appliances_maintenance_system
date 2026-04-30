"""Diagnostics Views — DRF with optimized queries."""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import MatterNode, DiagnosticLog
from .serializers import (
    MatterNodeSerializer,
    MatterNodeListSerializer,
    DiagnosticLogSerializer,
)


class MatterNodeViewSet(viewsets.ReadOnlyModelViewSet):
    """Matter Protocol node monitoring with anomaly scores."""

    def get_serializer_class(self):
        if self.action == 'list':
            return MatterNodeListSerializer
        return MatterNodeSerializer

    def get_queryset(self):
        qs = MatterNode.objects.select_related('device', 'device__room')

        if self.action == 'retrieve':
            qs = qs.prefetch_related('diagnostic_logs')

        # Filter by health status
        health = self.request.query_params.get('health')
        if health:
            qs = qs.filter(health_status=health)

        # Filter by cluster type
        cluster = self.request.query_params.get('cluster')
        if cluster:
            qs = qs.filter(cluster_type=cluster)
            
        # Filter by device_id
        device_id = self.request.query_params.get('device_id')
        if device_id:
            qs = qs.filter(device_id=device_id)

        return qs

    @action(detail=False, methods=['get'], url_path='anomalous')
    def anomalous(self, request):
        """List all nodes with anomaly score > 0.5."""
        nodes = (
            MatterNode.objects
            .select_related('device', 'device__room')
            .filter(anomaly_score__gte=0.5)
            .order_by('-anomaly_score')
        )
        serializer = MatterNodeListSerializer(nodes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='generate-mock')
    def generate_mock(self, request):
        """Generate mock diagnostic data for a specific device_id."""
        device_id = request.data.get('device_id')
        if not device_id:
            return Response({'error': 'device_id required'}, status=400)
            
        from apps.dashboard.models import Device
        import random
        
        try:
            device = Device.objects.get(id=device_id)
        except Device.DoesNotExist:
            return Response({'error': 'Device not found'}, status=404)
            
        # Create a few matter nodes if none exist
        if not MatterNode.objects.filter(device=device).exists():
            clusters = ['0x0006', '0x0008', '0x002f', '0x0402', '0x0406']
            selected_clusters = random.sample(clusters, random.randint(2, 4))
            
            nodes = []
            for ep, cluster in enumerate(selected_clusters, start=1):
                # Generate realistic anomaly based on device status
                score = random.uniform(0.0, 0.3)
                if device.status in ['warning', 'critical'] and random.random() > 0.5:
                    score = random.uniform(0.6, 0.95)
                    
                nodes.append(MatterNode(
                    device=device,
                    node_id=f"node-{str(device.id)[:8]}",
                    endpoint_id=ep,
                    cluster_type=cluster,
                    anomaly_score=score
                ))
            MatterNode.objects.bulk_create(nodes)
            
            # Fetch the generated nodes to trigger save() methods and cluster names
            # Bulk create doesn't trigger save() so we update them individually
            for n in MatterNode.objects.filter(device=device):
                n.save()
                
        nodes_qs = MatterNode.objects.filter(device=device)
        return Response(MatterNodeListSerializer(nodes_qs, many=True).data)


class DiagnosticLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Diagnostic logs for a specific node."""
    serializer_class = DiagnosticLogSerializer

    def get_queryset(self):
        node_id = self.kwargs.get('node_pk')
        qs = DiagnosticLog.objects.all()
        if node_id:
            qs = qs.filter(node_id=node_id)

        # Filter by metric type
        metric = self.request.query_params.get('metric')
        if metric:
            qs = qs.filter(metric_type=metric)

        # Only anomalous
        anomalous = self.request.query_params.get('anomalous')
        if anomalous == 'true':
            qs = qs.filter(is_anomalous=True)

        return qs[:100]  # Cap at 100 entries
