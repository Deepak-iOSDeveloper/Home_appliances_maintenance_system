"""
Management Command: seed_demo — Populate ARHIS with realistic demo data.

Creates rooms, devices, Matter nodes, diagnostic logs, technical manuals,
and an initial health score snapshot.
"""
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.dashboard.models import Room, Device, ResidentialHealthSnapshot
from apps.diagnostics.models import MatterNode, DiagnosticLog
from apps.troubleshooter.models import TechnicalManual
from apps.dashboard.services import calculate_health_score
from apps.diagnostics.services import run_anomaly_detection


class Command(BaseCommand):
    help = 'Seed the database with demo data for ARHIS'

    def handle(self, *args, **options):
        self.stdout.write('🏠 Seeding ARHIS demo data...\n')

        self._create_rooms()
        self._create_devices()
        self._create_matter_nodes()
        self._create_manuals()

        # Run background services once
        self.stdout.write('  Running anomaly detection...')
        run_anomaly_detection()

        self.stdout.write('  Calculating health score...')
        calculate_health_score()

        self.stdout.write(self.style.SUCCESS('\n✅ ARHIS demo data seeded successfully!'))

    def _create_rooms(self):
        self.stdout.write('  Creating rooms...')
        rooms_data = [
            {'name': 'Living Room', 'floor': 1, 'icon': 'sofa', 'svg_coordinates': {'x': 20, 'y': 30, 'width': 200, 'height': 150}},
            {'name': 'Kitchen', 'floor': 1, 'icon': 'utensils', 'svg_coordinates': {'x': 240, 'y': 30, 'width': 180, 'height': 150}},
            {'name': 'Master Bedroom', 'floor': 2, 'icon': 'bed', 'svg_coordinates': {'x': 20, 'y': 30, 'width': 180, 'height': 130}},
            {'name': 'Front Entrance', 'floor': 1, 'icon': 'door-open', 'svg_coordinates': {'x': 20, 'y': 200, 'width': 120, 'height': 80}},
            {'name': 'Garage', 'floor': 0, 'icon': 'warehouse', 'svg_coordinates': {'x': 240, 'y': 200, 'width': 180, 'height': 80}},
        ]
        for data in rooms_data:
            Room.objects.get_or_create(name=data['name'], defaults=data)

    def _create_devices(self):
        self.stdout.write('  Creating devices...')
        rooms = {r.name: r for r in Room.objects.all()}
        devices_data = [
            {'room': 'Living Room', 'name': 'Nest Thermostat', 'device_type': 'thermostat', 'node_id': 'node-0x01', 'manufacturer': 'Google', 'model_number': 'T3007ES', 'status': 'online', 'power_consumption_watts': 12.5, 'metadata': {'setpoint': 72, 'mode': 'auto', 'humidity': 45}},
            {'room': 'Living Room', 'name': 'Philips Hue Bridge', 'device_type': 'light', 'node_id': 'node-0x02', 'manufacturer': 'Philips', 'model_number': 'BSB002', 'status': 'online', 'power_consumption_watts': 3.2, 'metadata': {'connected_bulbs': 8, 'brightness': 75}},
            {'room': 'Front Entrance', 'name': 'Yale Smart Lock', 'device_type': 'smart_lock', 'node_id': 'node-0x03', 'manufacturer': 'Yale', 'model_number': 'YRD256', 'status': 'warning', 'power_consumption_watts': 2.1, 'battery_level': 15, 'metadata': {'locked': True, 'auto_lock': True, 'last_code_used': '****1234'}},
            {'room': 'Front Entrance', 'name': 'Ring Doorbell Pro', 'device_type': 'doorbell', 'node_id': 'node-0x04', 'manufacturer': 'Ring', 'model_number': 'B08JNR77QY', 'status': 'online', 'power_consumption_watts': 16.0, 'metadata': {'motion_zones': 3, 'night_vision': True}},
            {'room': 'Kitchen', 'name': 'Samsung Smart Fridge', 'device_type': 'appliance', 'node_id': 'node-0x05', 'manufacturer': 'Samsung', 'model_number': 'RF28T5001SR', 'status': 'online', 'power_consumption_watts': 150.0, 'metadata': {'temp_fridge': 37, 'temp_freezer': 0, 'door_open': False}},
            {'room': 'Kitchen', 'name': 'Smart Plug - Coffee Maker', 'device_type': 'plug', 'node_id': 'node-0x06', 'manufacturer': 'TP-Link', 'model_number': 'HS110', 'status': 'online', 'power_consumption_watts': 900.0, 'metadata': {'schedule': '6:30 AM daily'}},
            {'room': 'Master Bedroom', 'name': 'Ecobee Sensor', 'device_type': 'sensor', 'node_id': 'node-0x07', 'manufacturer': 'Ecobee', 'model_number': 'EB-RSe3PK2-01', 'status': 'online', 'power_consumption_watts': 0.5, 'battery_level': 78, 'metadata': {'temperature': 70, 'occupancy': True}},
            {'room': 'Master Bedroom', 'name': 'Dyson Pure Cool', 'device_type': 'hvac', 'node_id': 'node-0x08', 'manufacturer': 'Dyson', 'model_number': 'TP04', 'status': 'online', 'power_consumption_watts': 40.0, 'metadata': {'fan_speed': 5, 'filter_life': 62, 'air_quality': 'good'}},
            {'room': 'Garage', 'name': 'Chamberlain MyQ Opener', 'device_type': 'appliance', 'node_id': 'node-0x09', 'manufacturer': 'Chamberlain', 'model_number': 'B6765T', 'status': 'critical', 'power_consumption_watts': 500.0, 'is_reachable': False, 'metadata': {'door_state': 'unknown', 'obstruction': True}},
            {'room': 'Garage', 'name': 'Arlo Security Camera', 'device_type': 'camera', 'node_id': 'node-0x0A', 'manufacturer': 'Arlo', 'model_number': 'VMC4060P', 'status': 'online', 'power_consumption_watts': 8.0, 'battery_level': 92, 'metadata': {'recording': True, 'night_vision': True}},
        ]
        for data in devices_data:
            room = rooms.get(data.pop('room'))
            if room:
                Device.objects.get_or_create(node_id=data['node_id'], defaults={**data, 'room': room})

    def _create_matter_nodes(self):
        self.stdout.write('  Creating Matter Protocol nodes...')
        devices = {d.node_id: d for d in Device.objects.all()}
        nodes_data = [
            {'device_node': 'node-0x01', 'node_id': 'M-0x01', 'endpoint_id': 0, 'cluster_type': '0x0201', 'attributes': {'occupied_heating_setpoint': 2200, 'system_mode': 1}},
            {'device_node': 'node-0x01', 'node_id': 'M-0x01', 'endpoint_id': 1, 'cluster_type': '0x002f', 'attributes': {'bat_charge_level': 100, 'wired_power': True}},
            {'device_node': 'node-0x02', 'node_id': 'M-0x02', 'endpoint_id': 0, 'cluster_type': '0x0006', 'attributes': {'on_off': True}},
            {'device_node': 'node-0x02', 'node_id': 'M-0x02', 'endpoint_id': 1, 'cluster_type': '0x0008', 'attributes': {'current_level': 190}},
            {'device_node': 'node-0x03', 'node_id': 'M-0x03', 'endpoint_id': 0, 'cluster_type': '0x0101', 'attributes': {'lock_state': 1, 'lock_type': 0}},
            {'device_node': 'node-0x03', 'node_id': 'M-0x03', 'endpoint_id': 1, 'cluster_type': '0x002f', 'attributes': {'bat_charge_level': 15, 'bat_replacement_needed': True}},
            {'device_node': 'node-0x05', 'node_id': 'M-0x05', 'endpoint_id': 0, 'cluster_type': '0x0402', 'attributes': {'measured_value': 370}},
            {'device_node': 'node-0x05', 'node_id': 'M-0x05', 'endpoint_id': 1, 'cluster_type': '0x002f', 'attributes': {'wired_power': True}},
            {'device_node': 'node-0x07', 'node_id': 'M-0x07', 'endpoint_id': 0, 'cluster_type': '0x0402', 'attributes': {'measured_value': 2100}},
            {'device_node': 'node-0x07', 'node_id': 'M-0x07', 'endpoint_id': 1, 'cluster_type': '0x0406', 'attributes': {'occupancy': 1}},
            {'device_node': 'node-0x09', 'node_id': 'M-0x09', 'endpoint_id': 0, 'cluster_type': '0x0006', 'attributes': {'on_off': False}},
            {'device_node': 'node-0x09', 'node_id': 'M-0x09', 'endpoint_id': 1, 'cluster_type': '0x002f', 'attributes': {'wired_power': True, 'fault': 'obstruction_detected'}},
        ]
        for data in nodes_data:
            device = devices.get(data.pop('device_node'))
            if device:
                MatterNode.objects.get_or_create(
                    device=device, endpoint_id=data['endpoint_id'], cluster_type=data['cluster_type'],
                    defaults={**data, 'device': device}
                )

    def _create_manuals(self):
        self.stdout.write('  Creating technical manuals...')
        manuals = [
            {'device_type': 'smart_lock', 'brand': 'Yale', 'model_number': 'YRD256', 'title': 'Yale YRD256 — Battery Replacement Guide', 'chunk_index': 0,
             'content': 'Section 4.2: Battery Replacement\n\n1. Remove the interior cover by sliding it upward.\n2. Disconnect the battery connector carefully.\n3. Remove the four AA batteries from the battery pack.\n4. Insert four new AA alkaline batteries (do NOT use rechargeable).\n5. Reconnect the battery connector.\n6. Replace the interior cover.\n7. Test the lock by entering your access code.\n\nNote: Replace batteries when the low-battery indicator appears or battery level drops below 20%. Expected battery life is 12-24 months with normal use.'},
            {'device_type': 'smart_lock', 'brand': 'Yale', 'model_number': 'YRD256', 'title': 'Yale YRD256 — Connectivity Troubleshooting', 'chunk_index': 1,
             'content': 'Section 6.1: Network Connectivity Issues\n\n1. Verify your Z-Wave/Zigbee hub is powered and within range (max 30ft).\n2. Perform a network exclusion: Press the gear icon > Network > Exclude.\n3. Re-include the lock: Hub settings > Add device > Follow prompts.\n4. If the lock is unresponsive, perform a factory reset: Hold the reset button (inside the battery compartment) for 10 seconds until you hear 3 beeps.\n5. After reset, re-program your master code and re-add to your hub.\n\nWarning: Factory reset erases all programmed codes.'},
            {'device_type': 'thermostat', 'brand': 'Google', 'model_number': 'T3007ES', 'title': 'Nest Thermostat — HVAC Not Responding', 'chunk_index': 0,
             'content': 'Section 3.4: HVAC System Not Responding\n\n1. Check the Nest display — if blank, charge via USB-C for 30 minutes.\n2. Verify wiring: Pull the Nest off the base and check that R, W, Y, G wires are firmly seated.\n3. Check the HVAC breaker in your electrical panel.\n4. Test the system: Settings > Equipment > Test.\n5. If the Nest shows an E73 error, the system has detected a wiring issue — refer to Section 3.5.\n\nNote: The Nest requires a C-wire or compatible system for reliable power.'},
            {'device_type': 'appliance', 'brand': 'Chamberlain', 'model_number': 'B6765T', 'title': 'Chamberlain MyQ — Obstruction Detected Error', 'chunk_index': 0,
             'content': 'Section 5.1: Resolving Obstruction Errors\n\n1. SAFETY FIRST: Disconnect the opener from power before inspection.\n2. Check the door path: Remove any objects blocking the door track.\n3. Clean the safety sensors: Wipe both sensors (located 6 inches from floor on each side) with a dry cloth.\n4. Align the sensors: Both LEDs should be solid (green sending, amber receiving). Adjust until steady.\n5. Inspect the door track: Look for bent rails, loose bolts, or debris.\n6. Test manually: Pull the emergency release cord and open/close the door by hand.\n7. Reconnect power and test via the wall button first, then the app.\n\nIf the error persists, the sensor wiring may be damaged — contact a certified technician.'},
            {'device_type': 'hvac', 'brand': 'Dyson', 'model_number': 'TP04', 'title': 'Dyson Pure Cool — Filter Maintenance', 'chunk_index': 0,
             'content': 'Section 2.3: Filter Replacement\n\n1. Turn off and unplug the purifier.\n2. Press the filter release buttons on both sides of the base.\n3. Pull the old filter(s) downward to remove.\n4. Remove the new filter from its sealed bag.\n5. Push the new filter up into the base until it clicks.\n6. Plug in the unit and reset the filter life counter: Hold the night mode button for 5 seconds.\n\nFilter life: Replace every 12 months or when the app indicates filter life is below 10%.'},
        ]
        for data in manuals:
            TechnicalManual.objects.get_or_create(
                brand=data['brand'], model_number=data['model_number'], chunk_index=data['chunk_index'],
                defaults=data
            )
