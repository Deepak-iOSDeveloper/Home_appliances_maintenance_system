"""
Dashboard Models — Digital Twin
Represents the physical home layout with rooms, devices, and health snapshots.
"""
import uuid
from django.db import models


class Home(models.Model):
    """A residential home or floorplan container."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, default="Demo Home")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.name


class Room(models.Model):
    """A physical room in the residence."""

    FLOOR_CHOICES = [
        (0, 'Basement'),
        (1, 'Ground Floor'),
        (2, 'First Floor'),
        (3, 'Second Floor'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    home = models.ForeignKey(
        Home, on_delete=models.CASCADE, related_name='rooms',
        null=True, blank=True # Allow null for seamless initial migration
    )
    name = models.CharField(max_length=100) # Removed unique=True to allow same room names across homes
    floor = models.IntegerField(choices=FLOOR_CHOICES, default=1)
    svg_path_id = models.CharField(
        max_length=50, blank=True,
        help_text='SVG element ID for floorplan interactivity'
    )
    svg_coordinates = models.JSONField(
        default=dict, blank=True,
        help_text='{"x": 0, "y": 0, "width": 100, "height": 80}'
    )
    icon = models.CharField(max_length=50, default='room', help_text='Icon identifier')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['floor', 'name']

    def __str__(self):
        return f"{self.name} (Floor {self.floor})"


class Device(models.Model):
    """An IoT device in the residence, linked to a room."""

    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    DEVICE_TYPE_CHOICES = [
        ('thermostat', 'Thermostat'),
        ('smart_lock', 'Smart Lock'),
        ('light', 'Smart Light'),
        ('camera', 'Security Camera'),
        ('sensor', 'Sensor'),
        ('appliance', 'Smart Appliance'),
        ('speaker', 'Smart Speaker'),
        ('hvac', 'HVAC System'),
        ('doorbell', 'Smart Doorbell'),
        ('plug', 'Smart Plug'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='devices'
    )
    name = models.CharField(max_length=150)
    device_type = models.CharField(max_length=30, choices=DEVICE_TYPE_CHOICES)
    node_id = models.CharField(
        max_length=20, unique=True,
        help_text='Matter/HA Node ID (e.g., node-0x01)'
    )
    manufacturer = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    firmware_version = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='online')
    power_consumption_watts = models.FloatField(default=0.0)
    battery_level = models.IntegerField(null=True, blank=True, help_text='Battery % (null if AC-powered)')
    last_seen = models.DateTimeField(auto_now=True)
    is_reachable = models.BooleanField(default=True)
    metadata = models.JSONField(
        default=dict, blank=True,
        help_text='Device-specific attributes (e.g., temperature setpoint, lock state)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['room', 'name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['device_type']),
            models.Index(fields=['node_id']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_device_type_display()}) — {self.room.name}"


class ResidentialHealthSnapshot(models.Model):
    """
    Periodic snapshot of the overall home health score.
    Calculated by the background health scoring service.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    home = models.ForeignKey(
        Home, on_delete=models.CASCADE, related_name='health_snapshots',
        null=True, blank=True # Allow null for initial migration
    )
    score = models.FloatField(help_text='Residential Health Score (0–100)')
    grade = models.CharField(
        max_length=2, default='A',
        help_text='Letter grade (A+, A, B, C, D, F)'
    )
    calculated_at = models.DateTimeField(auto_now_add=True)
    breakdown = models.JSONField(
        default=dict,
        help_text='{"uptime": 95, "anomalies": 88, "power": 92, "errors": 97}'
    )
    summary = models.TextField(
        blank=True,
        help_text='AI-generated natural language summary'
    )
    device_count = models.IntegerField(default=0)
    online_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-calculated_at']
        get_latest_by = 'calculated_at'

    def __str__(self):
        return f"Health Score: {self.score:.1f} ({self.grade}) @ {self.calculated_at}"
