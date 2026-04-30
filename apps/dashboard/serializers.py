"""Dashboard Serializers — DRF API Layer"""
from rest_framework import serializers
from .models import Home, Room, Device, ResidentialHealthSnapshot


class DeviceSerializer(serializers.ModelSerializer):
    """Device serializer with room name for display."""
    room_name = serializers.CharField(source='room.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_device_type_display', read_only=True)
    room_id = serializers.PrimaryKeyRelatedField(
        source='room', queryset=Room.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = Device
        fields = [
            'id', 'name', 'device_type', 'type_display', 'node_id',
            'manufacturer', 'model_number', 'firmware_version',
            'status', 'status_display', 'power_consumption_watts',
            'battery_level', 'last_seen', 'is_reachable',
            'metadata', 'room', 'room_name', 'room_id', 'created_at',
        ]


class RoomSerializer(serializers.ModelSerializer):
    """Room serializer with nested devices."""
    devices = DeviceSerializer(many=True, read_only=True)
    device_count = serializers.IntegerField(source='devices.count', read_only=True)
    floor_display = serializers.CharField(source='get_floor_display', read_only=True)

    class Meta:
        model = Room
        fields = [
            'id', 'home', 'name', 'floor', 'floor_display', 'svg_path_id',
            'svg_coordinates', 'icon', 'devices', 'device_count', 'created_at',
        ]

class HomeSerializer(serializers.ModelSerializer):
    """Home serializer."""
    rooms = RoomSerializer(many=True, read_only=True)
    
    class Meta:
        model = Home
        fields = ['id', 'name', 'rooms', 'created_at']


class HealthSnapshotSerializer(serializers.ModelSerializer):
    """Residential Health Score snapshot."""
    class Meta:
        model = ResidentialHealthSnapshot
        fields = [
            'id', 'score', 'grade', 'calculated_at', 'breakdown',
            'summary', 'device_count', 'online_count',
        ]
