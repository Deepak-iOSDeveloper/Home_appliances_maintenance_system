"""Dashboard Views — DRF ViewSets with optimized queries."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Home, Room, Device, ResidentialHealthSnapshot
from .serializers import HomeSerializer, RoomSerializer, DeviceSerializer, HealthSnapshotSerializer

class HomeViewSet(viewsets.ModelViewSet):
    """List and manage homes."""
    serializer_class = HomeSerializer
    queryset = Home.objects.all()

class RoomViewSet(viewsets.ModelViewSet):
    """List rooms with nested devices (uses prefetch_related)."""
    serializer_class = RoomSerializer

    def get_queryset(self):
        qs = Room.objects.prefetch_related('devices').all()
        home_id = self.request.query_params.get('home')
        if home_id:
            qs = qs.filter(home_id=home_id)
        return qs


class DeviceViewSet(viewsets.ModelViewSet):
    """List all devices with room info (uses select_related)."""
    serializer_class = DeviceSerializer

    @action(detail=False, methods=['get'], url_path='scan')
    def scan(self, request):
        """Scan the local mDNS network for devices."""
        from .services import scan_local_network_mdns
        devices = scan_local_network_mdns(timeout_seconds=3)
        return Response(devices)

    def get_queryset(self):
        qs = Device.objects.select_related('room').all()
        # Optional filtering
        device_type = self.request.query_params.get('type')
        device_status = self.request.query_params.get('status')
        room_id = self.request.query_params.get('room')

        if device_type:
            qs = qs.filter(device_type=device_type)
        if device_status:
            qs = qs.filter(status=device_status)
        if room_id:
            qs = qs.filter(room_id=room_id)
        return qs

    @action(detail=True, methods=['get'], url_path='status')
    def device_status(self, request, pk=None):
        """Get detailed status for a specific device."""
        device = self.get_object()
        return Response({
            'id': str(device.id),
            'name': device.name,
            'status': device.status,
            'power_consumption_watts': device.power_consumption_watts,
            'battery_level': device.battery_level,
            'is_reachable': device.is_reachable,
            'last_seen': device.last_seen,
            'metadata': device.metadata,
        })


class HealthScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """Health score snapshots."""
    serializer_class = HealthSnapshotSerializer
    queryset = ResidentialHealthSnapshot.objects.all()

    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        """Get the most recent health score for a specific home."""
        home_id = request.query_params.get('home')
        if not home_id:
            return Response(
                {'score': None, 'grade': 'N/A', 'summary': 'Select a home to view health.'},
                status=status.HTTP_200_OK
            )
            
        try:
            snapshot = ResidentialHealthSnapshot.objects.filter(home_id=home_id).latest()
            serializer = self.get_serializer(snapshot)
            return Response(serializer.data)
        except ResidentialHealthSnapshot.DoesNotExist:
            # Trigger calculation on-the-fly for new homes
            from .services import calculate_health_score
            snapshot = calculate_health_score(home_id=home_id)
            serializer = self.get_serializer(snapshot)
            return Response(serializer.data)
