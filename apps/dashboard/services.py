"""
Dashboard Services — Residential Health Score Calculator.

Calculates a composite health score based on:
  - Device uptime (40%)
  - Anomaly count (30%)
  - Power efficiency (20%)
  - Error rate (10%)
"""
from django.utils import timezone
from .models import Device, ResidentialHealthSnapshot
import time
import socket
try:
    from zeroconf import Zeroconf, ServiceBrowser
except ImportError:
    pass

def scan_local_network_mdns(timeout_seconds=3):
    """
    Scans the local network for mDNS (Zeroconf) broadcasting devices.
    Looks for common IoT services.
    """
    devices_found = []
    
    try:
        zeroconf = Zeroconf()
    except Exception as e:
        print(f"Zeroconf init failed: {e}")
        return []
        
    class MyListener:
        def remove_service(self, zeroconf, type, name):
            pass

        def add_service(self, zeroconf, type, name):
            info = zeroconf.get_service_info(type, name)
            if info:
                # Clean up name
                clean_name = name.split('.')[0]
                ip_str = "Unknown"
                if info.addresses:
                    try:
                        ip_str = socket.inet_ntoa(info.addresses[0])
                    except:
                        pass
                devices_found.append({
                    "name": clean_name,
                    "type_service": type,
                    "ip": ip_str,
                    "server": info.server
                })

    listener = MyListener()
    
    # Common IoT / Smart Home mDNS services
    services_to_browse = [
        "_http._tcp.local.",
        "_googlecast._tcp.local.",     # Chromecasts, Android TVs
        "_airplay._tcp.local.",        # Apple TVs, HomePods
        "_homekit._tcp.local.",        # HomeKit accessories
        "_hap._tcp.local.",            # HomeKit accessories
        "_spotify-connect._tcp.local.",# Speakers
        "_printer._tcp.local.",        # Printers
        "_matter._tcp.local.",         # Matter protocol devices
        "_smb._tcp.local.",            # NAS
    ]
    
    browsers = []
    for s in services_to_browse:
        browsers.append(ServiceBrowser(zeroconf, s, listener))
        
    # Wait for discovery
    time.sleep(timeout_seconds)
    
    zeroconf.close()
    
    # Deduplicate by name
    seen = set()
    unique_devices = []
    for d in devices_found:
        if d['name'] not in seen:
            seen.add(d['name'])
            unique_devices.append(d)
            
    return unique_devices


def calculate_health_score(home_id=None) -> ResidentialHealthSnapshot:
    """Calculate and store a new Residential Health Score snapshot for a home."""
    if home_id:
        devices = Device.objects.filter(room__home_id=home_id)
    else:
        devices = Device.objects.all()
        
    total = devices.count()

    if total == 0:
        return ResidentialHealthSnapshot.objects.create(
            score=100, grade='A+', device_count=0, online_count=0,
            breakdown={'uptime': 100, 'anomalies': 100, 'power': 100, 'errors': 100},
            summary='No devices registered. System baseline is healthy.'
        )

    online = devices.filter(status='online').count()
    warning = devices.filter(status='warning').count()
    critical = devices.filter(status='critical').count()

    # 1. Uptime score (40%)
    uptime_pct = (online / total) * 100 if total > 0 else 100
    uptime_score = uptime_pct

    # 2. Anomaly score (30%) — from diagnostics
    from apps.diagnostics.models import MatterNode
    if home_id:
        nodes = MatterNode.objects.filter(device__room__home_id=home_id)
    else:
        nodes = MatterNode.objects.all()
        
    node_count = nodes.count()
    if node_count > 0:
        anomalous = nodes.filter(anomaly_score__gte=0.5).count()
        anomaly_score = max(0, 100 - (anomalous / node_count * 100))
    else:
        anomaly_score = 100

    # 3. Power efficiency (20%)
    avg_power = 0
    powered = devices.filter(power_consumption_watts__gt=0)
    if powered.exists():
        total_power = sum(d.power_consumption_watts for d in powered)
        expected_power = powered.count() * 50  # Assume 50W baseline per device
        efficiency = min(100, (1 - abs(total_power - expected_power) / max(expected_power, 1)) * 100)
        power_score = max(0, efficiency)
    else:
        power_score = 100

    # 4. Error rate (10%)
    error_score = max(0, 100 - (critical * 20) - (warning * 5))

    # Weighted composite
    composite = (
        uptime_score * 0.40 +
        anomaly_score * 0.30 +
        power_score * 0.20 +
        error_score * 0.10
    )
    composite = round(max(0, min(100, composite)), 1)

    # Grade
    if composite >= 95: grade = 'A+'
    elif composite >= 90: grade = 'A'
    elif composite >= 80: grade = 'B'
    elif composite >= 70: grade = 'C'
    elif composite >= 60: grade = 'D'
    else: grade = 'F'

    breakdown = {
        'uptime': round(uptime_score, 1),
        'anomalies': round(anomaly_score, 1),
        'power': round(power_score, 1),
        'errors': round(error_score, 1),
    }

    summary = (
        f"Residential Health Score: {composite}/100 ({grade}). "
        f"{online}/{total} devices online. "
        f"{warning} warning(s), {critical} critical alert(s)."
    )

    return ResidentialHealthSnapshot.objects.create(
        home_id=home_id,
        score=composite, grade=grade,
        device_count=total, online_count=online,
        breakdown=breakdown, summary=summary,
    )
