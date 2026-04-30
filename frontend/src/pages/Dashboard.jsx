import React, { useState, useEffect } from 'react';
import { api } from '../api/client.js';

const DEVICE_ICONS = {
  thermostat: '🌡', smart_lock: '🔒', light: '💡', camera: '📷',
  sensor: '📡', appliance: '🏠', speaker: '🔊', hvac: '❄️',
  doorbell: '🔔', plug: '🔌',
};

export default function Dashboard() {
  const [homes, setHomes] = useState([]);
  const [selectedHomeId, setSelectedHomeId] = useState('');

  const [rooms, setRooms] = useState([]);
  const [health, setHealth] = useState(null);
  const [devices, setDevices] = useState([]);
  const [selectedRoom, setSelectedRoom] = useState(null);

  // --- Feature: Device Intelligence Modal ---
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [deviceDiagnostics, setDeviceDiagnostics] = useState(null);
  const [isDiagnosticsLoading, setIsDiagnosticsLoading] = useState(false);

  // Edit Mode State
  const [isEditMode, setIsEditMode] = useState(false);
  const [dragState, setDragState] = useState(null);

  const fetchDashboardData = async (homeId) => {
    try {
      const rm = await api.dashboard.rooms(homeId);
      setRooms(Array.isArray(rm) ? rm : []);
      // Fetch devices, then filter client-side to only show devices in current home's rooms
      const devs = await api.dashboard.devices();
      if (Array.isArray(devs) && Array.isArray(rm)) {
        const roomIds = new Set(rm.map(r => r.id));
        setDevices(devs.filter(d => roomIds.has(d.room)));
      } else {
        setDevices([]);
      }
      const hlth = await api.dashboard.healthScore(homeId);
      setHealth(hlth);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    api.dashboard.homes().then(h => {
      const data = Array.isArray(h) ? h : [];
      setHomes(data);
      if (data.length > 0 && !selectedHomeId) {
        setSelectedHomeId(data[0].id);
      }
    }).catch(() => { });
  }, []);

  useEffect(() => {
    if (selectedHomeId) {
      fetchDashboardData(selectedHomeId);
      setSelectedRoom(null);
    }
  }, [selectedHomeId]);

  // --- Fetch Diagnostics when Device is selected ---
  useEffect(() => {
    if (selectedDevice) {
      fetchDiagnostics(selectedDevice.id);
    } else {
      setDeviceDiagnostics(null);
    }
  }, [selectedDevice]);

  const fetchDiagnostics = async (deviceId) => {
    setIsDiagnosticsLoading(true);
    try {
      let nodes = await api.diagnostics.nodesByDevice(deviceId);
      if (nodes.length === 0) {
        // Generate mock data for new devices to demonstrate UI
        nodes = await api.diagnostics.generateMockNodes(deviceId);
      }
      setDeviceDiagnostics(nodes);
    } catch (e) {
      console.error("Failed to load device diagnostics", e);
    }
    setIsDiagnosticsLoading(false);
  };

  const filteredDevices = selectedRoom
    ? devices.filter((d) => d.room === selectedRoom)
    : devices;

  // --- Home Management ---
  const handleCreateHome = async () => {
    const name = window.prompt("Enter new Home name:");
    if (!name || !name.trim()) return;
    const newHome = await api.dashboard.createHome(name.trim());
    setHomes([...homes, newHome]);
    setSelectedHomeId(newHome.id);
  };

  const handleRenameHome = async () => {
    if (!selectedHomeId) return;
    const currentHome = homes.find(h => h.id === selectedHomeId);
    const newName = window.prompt("Enter new Home name:", currentHome?.name);
    if (!newName || !newName.trim() || newName.trim() === currentHome?.name) return;

    await api.dashboard.updateHome(selectedHomeId, newName.trim());
    setHomes(homes.map(h => h.id === selectedHomeId ? { ...h, name: newName.trim() } : h));
  };

  const handleDeleteHome = async () => {
    if (!selectedHomeId) return;
    const currentHome = homes.find(h => h.id === selectedHomeId);
    if (!window.confirm(`Are you sure you want to completely delete "${currentHome?.name}" and ALL its rooms and devices?`)) return;

    await api.dashboard.deleteHome(selectedHomeId);
    const remainingHomes = homes.filter(h => h.id !== selectedHomeId);
    setHomes(remainingHomes);
    setSelectedHomeId(remainingHomes.length > 0 ? remainingHomes[0].id : '');
  };

  // --- Room Management ---
  const handleAddRoom = async () => {
    if (!selectedHomeId) return alert("Select a home first.");
    const name = window.prompt("Enter new Room name:");
    if (!name || !name.trim()) return;
    const newRoom = await api.dashboard.createRoom({
      home: selectedHomeId,
      name: name.trim(),
      floor: 1,
      svg_coordinates: { x: 50, y: 50, width: 120, height: 100 }
    });
    setRooms([...rooms, newRoom]);
  };

  const handleDeleteRoom = async (e, roomId) => {
    e.stopPropagation();
    if (!window.confirm("Delete this room and all its devices?")) return;
    await api.dashboard.deleteRoom(roomId);
    setRooms(rooms.filter(r => r.id !== roomId));
    setDevices(devices.filter(d => d.room !== roomId));
    if (selectedRoom === roomId) setSelectedRoom(null);
  };

  // --- Device Management ---
  const [isScanning, setIsScanning] = useState(false);

  const handleAddDevice = async () => {
    if (rooms.length === 0) return alert("Please add a room first before adding a device.");

    setIsScanning(true);
    let detectedDevices = [];
    try {
      detectedDevices = await api.dashboard.scanNetwork();
    } catch (e) {
      console.error(e);
      alert("Network scan failed. Ensure backend is running.");
      setIsScanning(false);
      return;
    }
    setIsScanning(false);

    let deviceName = "Unknown Device";
    let deviceId = `mdns-${Math.random().toString(16).slice(2, 10)}`;

    if (detectedDevices && detectedDevices.length > 0) {
      const devList = detectedDevices.map((d, i) => `${i}: ${d.name} (${d.ip})`).join('\n');
      const idx = window.prompt(`📡 Network Scan Complete.\nFound ${detectedDevices.length} devices on your Wi-Fi.\n\nSelect a device by number, or type "manual" to enter one:\n${devList}`);

      if (!idx) return; // Cancelled
      if (idx.toLowerCase() === 'manual') {
        const manualName = window.prompt("Enter device name manually:");
        if (!manualName || !manualName.trim()) return;
        deviceName = manualName.trim();
      } else {
        const selected = detectedDevices[parseInt(idx)];
        if (!selected) return alert("Invalid device selection.");
        deviceName = selected.name;
        deviceId = selected.ip;
      }
    } else {
      const wantsManual = window.confirm("📡 Network Scan Complete.\n\nNo mDNS devices found on your local Wi-Fi.\nWould you like to enter a device manually?");
      if (!wantsManual) return;
      const manualName = window.prompt("Enter device name manually:");
      if (!manualName || !manualName.trim()) return;
      deviceName = manualName.trim();
    }

    // Auto-infer device type from the name
    let inferredType = 'sensor';
    const lowerName = deviceName.toLowerCase();
    if (lowerName.includes('tv') || lowerName.includes('bravia') || lowerName.includes('cast')) inferredType = 'appliance';
    else if (lowerName.includes('speaker') || lowerName.includes('audio') || lowerName.includes('homepod') || lowerName.includes('sonos') || lowerName.includes('spotify')) inferredType = 'speaker';
    else if (lowerName.includes('light') || lowerName.includes('bulb') || lowerName.includes('hue')) inferredType = 'light';
    else if (lowerName.includes('lock') || lowerName.includes('door')) inferredType = 'smart_lock';
    else if (lowerName.includes('thermostat') || lowerName.includes('nest') || lowerName.includes('temp')) inferredType = 'thermostat';
    else if (lowerName.includes('cam') || lowerName.includes('video')) inferredType = 'camera';
    else if (lowerName.includes('plug') || lowerName.includes('socket')) inferredType = 'plug';
    else if (lowerName.includes('printer')) inferredType = 'appliance';

    const roomNames = rooms.map((r, i) => `${i}: ${r.name}`).join('\n');
    const roomIdx = window.prompt(`Detected "${deviceName}" (${inferredType}).\nSelect room number to assign it to:\n${roomNames}`, "0");
    const room = rooms[parseInt(roomIdx)];
    if (!room) return alert("Invalid room selection. Device setup cancelled.");

    const newDev = await api.dashboard.createDevice({
      name: deviceName,
      device_type: inferredType,
      room: room.id,
      node_id: deviceId,
      status: 'online',
      power_consumption_watts: Math.floor(Math.random() * 20)
    });
    setDevices([...devices, newDev]);

    // Increment device count locally in the room
    setRooms(rooms.map(r => r.id === room.id ? { ...r, device_count: r.device_count + 1 } : r));
  };

  const handleDeleteDevice = async (deviceId, roomId) => {
    if (!window.confirm("Delete this device permanently?")) return;
    await api.dashboard.deleteDevice(deviceId);
    setDevices(devices.filter(d => d.id !== deviceId));
    // Decrement count
    setRooms(rooms.map(r => r.id === roomId ? { ...r, device_count: Math.max(0, r.device_count - 1) } : r));
  };

  // --- SVG Drag & Drop Logic ---
  const handlePointerDown = (e, roomId, type) => {
    if (!isEditMode) return;
    e.stopPropagation();
    e.target.setPointerCapture(e.pointerId);

    const svgRect = e.currentTarget.closest('svg').getBoundingClientRect();
    const scaleX = 500 / svgRect.width;
    const scaleY = 320 / svgRect.height;

    const room = rooms.find(r => r.id === roomId);
    const c = room.svg_coordinates || { x: 0, y: 0, width: 100, height: 80 };

    setDragState({
      type, roomId,
      startX: e.clientX, startY: e.clientY,
      origX: c.x, origY: c.y, origW: c.width, origH: c.height,
      scaleX, scaleY, pointerId: e.pointerId
    });
  };

  const handlePointerMove = (e) => {
    if (!dragState) return;
    const dx = (e.clientX - dragState.startX) * dragState.scaleX;
    const dy = (e.clientY - dragState.startY) * dragState.scaleY;

    setRooms(rooms.map(r => {
      if (r.id === dragState.roomId) {
        const c = { ...(r.svg_coordinates || { x: 0, y: 0, width: 100, height: 80 }) };
        if (dragState.type === 'move') {
          c.x = Math.round(Math.max(0, Math.min(500 - c.width, dragState.origX + dx)));
          c.y = Math.round(Math.max(0, Math.min(320 - c.height, dragState.origY + dy)));
        } else if (dragState.type === 'resize') {
          c.width = Math.round(Math.max(40, Math.min(500 - c.x, dragState.origW + dx)));
          c.height = Math.round(Math.max(40, Math.min(320 - c.y, dragState.origH + dy)));
        }
        return { ...r, svg_coordinates: c };
      }
      return r;
    }));
  };

  const handlePointerUp = (e) => {
    if (!dragState) return;
    e.target.releasePointerCapture(dragState.pointerId);
    setDragState(null);
  };

  const handleSaveLayout = async () => {
    try {
      await Promise.all(rooms.map(r => api.dashboard.updateRoom(r.id, { svg_coordinates: r.svg_coordinates })));
      setIsEditMode(false);
    } catch (e) {
      console.error("Failed to save layout", e);
      alert("Failed to save layout.");
    }
  };

  return (
    <div>
      {/* Home Switcher */}
      <div className="flex items-center gap-md mb-md" style={{ background: 'var(--bg-surface)', padding: '16px 24px', borderRadius: 12, border: '1px solid rgba(255,255,255,0.04)' }}>
        <div style={{ fontWeight: 600, color: 'var(--text-muted)' }}>Current Home:</div>
        <select
          value={selectedHomeId}
          onChange={(e) => setSelectedHomeId(e.target.value)}
          style={{ background: 'var(--bg-input)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)', padding: '8px 12px', borderRadius: 8, outline: 'none' }}
        >
          <option value="" disabled>Select Home...</option>
          {homes.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
        <div className="flex gap-sm">
          <button className="nav-btn" style={{ width: 'auto', padding: '0 16px', fontSize: 13, fontWeight: 600, height: 36 }} onClick={handleCreateHome}>
            + New Home
          </button>
          {selectedHomeId && (
            <>
              <button className="nav-btn" style={{ width: 'auto', padding: '0 16px', fontSize: 13, fontWeight: 600, height: 36 }} onClick={handleRenameHome}>
                ✎ Rename
              </button>
              <button className="nav-btn" style={{ width: 'auto', padding: '0 16px', fontSize: 13, fontWeight: 600, height: 36, color: 'var(--accent-red)' }} onClick={handleDeleteHome}>
                × Delete
              </button>
            </>
          )}
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Floorplan */}
        <div className="neu-card">
          <div className="flex items-center justify-between mb-md">
            <div className="section-title" style={{ margin: 0 }}>Interactive Floorplan</div>
            <div className="flex gap-sm">
              {isEditMode ? (
                <>
                  <button className="nav-btn active" style={{ width: 'auto', padding: '4px 12px', fontSize: 12, fontWeight: 600 }} onClick={handleAddRoom}>+ Add Room</button>
                  <button className="nav-btn active" style={{ width: 'auto', padding: '4px 12px', fontSize: 12, fontWeight: 600 }} onClick={() => { setIsEditMode(false); fetchDashboardData(selectedHomeId); }}>Cancel</button>
                  <button className="nav-btn" style={{ width: 'auto', padding: '4px 12px', fontSize: 12, fontWeight: 600, background: 'var(--accent-cyan)', color: '#000' }} onClick={handleSaveLayout}>Save Layout</button>
                </>
              ) : (
                <button className="nav-btn" style={{ width: 'auto', padding: '4px 12px', fontSize: 12, fontWeight: 600 }} onClick={() => setIsEditMode(true)}>✎ Edit Layout</button>
              )}
            </div>
          </div>

          <svg
            viewBox="0 0 500 320"
            className="floorplan-svg"
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
            style={{ touchAction: 'none' }} // Prevent scrolling while dragging on touch devices
          >
            <rect x="0" y="0" width="500" height="320" rx="12" fill="#151515" />

            {/* Grid background when editing */}
            {isEditMode && (
              <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
              </pattern>
            )}
            {isEditMode && <rect width="500" height="320" fill="url(#grid)" />}

            {rooms.map((room) => {
              const c = room.svg_coordinates || {};
              const x = c.x || 0, y = c.y || 0;
              const w = c.width || 100, h = c.height || 80;
              const isActive = selectedRoom === room.id;

              return (
                <g key={room.id}>
                  <rect
                    x={x} y={y} width={w} height={h} rx="6"
                    className={`floorplan-room ${isActive && !isEditMode ? 'active' : ''}`}
                    style={{ cursor: isEditMode ? 'move' : 'pointer' }}
                    onClick={() => !isEditMode && setSelectedRoom(isActive ? null : room.id)}
                    onPointerDown={(e) => handlePointerDown(e, room.id, 'move')}
                  />
                  <text x={x + w / 2} y={y + h / 2 - 4} textAnchor="middle" className="floorplan-label" style={{ pointerEvents: 'none' }}>
                    {room.name}
                  </text>
                  <text x={x + w / 2} y={y + h / 2 + 12} textAnchor="middle" className="floorplan-label" style={{ fontSize: 9, pointerEvents: 'none' }}>
                    {room.device_count || 0} device{(room.device_count || 0) !== 1 ? 's' : ''}
                  </text>

                  {/* Device Dots */}
                  {!isEditMode && devices.filter(d => d.room === room.id).map((dev, i) => (
                    <circle
                      key={dev.id}
                      cx={x + 14 + (i % Math.floor(w / 18)) * 18}
                      cy={y + h - 14 - Math.floor(i / Math.floor(w / 18)) * 18}
                      className={`floorplan-device-dot ${dev.status === 'warning' ? 'warning' : dev.status === 'critical' ? 'critical' : ''}`}
                      style={{ pointerEvents: 'none' }}
                    />
                  ))}

                  {/* Resize Handle */}
                  {isEditMode && (
                    <rect
                      x={x + w - 10} y={y + h - 10} width={10} height={10}
                      fill="var(--accent-cyan)"
                      style={{ cursor: 'nwse-resize' }}
                      onPointerDown={(e) => handlePointerDown(e, room.id, 'resize')}
                    />
                  )}
                  {/* Trash Icon */}
                  {isEditMode && (
                    <g transform={`translate(${x + 6}, ${y + 6})`} style={{ cursor: 'pointer' }} onPointerDown={(e) => handleDeleteRoom(e, room.id)}>
                      <rect width={16} height={16} rx={4} fill="var(--accent-red)" opacity={0.8} />
                      <text x={8} y={11} fontSize={10} fill="#fff" textAnchor="middle">×</text>
                    </g>
                  )}
                </g>
              );
            })}
            {rooms.length === 0 && !isEditMode && (
              <text x="250" y="160" fill="var(--text-muted)" fontSize="14" textAnchor="middle">
                No rooms added yet. Click "Edit Layout" to add rooms.
              </text>
            )}
          </svg>
        </div>

        {/* Health Score */}
        <div className="neu-card health-gauge">
          <div className="section-title" style={{ alignSelf: 'flex-start' }}>Residential Health Score</div>
          {health ? (
            <>
              <div className="health-score-value">{health.score != null ? Math.round(health.score) : 0}</div>
              <div className="health-grade">Grade {health.grade || 'N/A'}</div>
              <p className="text-sm text-muted" style={{ marginTop: 12, textAlign: 'center' }}>
                {health.summary || `${health.online_count || 0}/${health.device_count || 0} devices online`}
              </p>
            </>
          ) : (
            <p className="text-muted">Loading health data...</p>
          )}
        </div>
      </div>

      {/* Devices Grid */}
      <div style={{ marginTop: 28 }}>
        <div className="flex items-center justify-between mb-md">
          <div className="section-title" style={{ margin: 0 }}>
            {selectedRoom ? `Devices in Selected Room` : `All Devices`} ({filteredDevices.length})
          </div>
          <button className="nav-btn active" style={{ width: 'auto', padding: '4px 16px', fontSize: 12, fontWeight: 600 }} onClick={handleAddDevice} disabled={isScanning}>
            {isScanning ? "📡 Scanning..." : "+ Add Device"}
          </button>
        </div>

        {filteredDevices.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            No devices found. Click "+ Add Device" to commission a new Matter node.
          </div>
        ) : (
          <div className="device-grid">
            {filteredDevices.map((dev) => (
              <div
                className="neu-card device-card cursor-pointer"
                key={dev.id}
                style={{ position: 'relative' }}
                onClick={() => setSelectedDevice(dev)}
              >
                <div className="device-card-header">
                  <div className="device-card-icon">{DEVICE_ICONS[dev.device_type] || '📟'}</div>
                  <span className={`status-dot ${dev.status}`} />
                </div>

                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteDevice(dev.id, dev.room); }}
                  style={{ position: 'absolute', top: 20, right: 20, background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16 }}
                  title="Remove Device"
                >
                  ×
                </button>

                <div className="device-card-name">{dev.name}</div>
                <div className="device-card-room">{dev.room_name} • {dev.type_display}</div>
                <div className="device-card-stats">
                  <div className="device-stat"><span>{dev.power_consumption_watts}W</span>Power</div>
                  {dev.battery_level !== null && (
                    <div className="device-stat"><span>{dev.battery_level}%</span>Battery</div>
                  )}
                  <div className="device-stat">
                    <span style={{ color: dev.is_reachable ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                      {dev.is_reachable ? 'Yes' : 'No'}
                    </span>
                    Reachable
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Device Intelligence Modal */}
      {selectedDevice && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'flex-end'
        }} onClick={() => setSelectedDevice(null)}>
          <div style={{
            width: '450px', height: '100%', background: 'var(--bg-surface)',
            borderLeft: '1px solid rgba(255,255,255,0.05)', padding: '32px',
            boxShadow: '-10px 0 40px rgba(0,0,0,0.5)', overflowY: 'auto'
          }} onClick={e => e.stopPropagation()}>

            <div className="flex justify-between items-start mb-xl">
              <div className="flex items-center gap-md">
                <div style={{ fontSize: 40, background: 'var(--bg-hover)', padding: '16px', borderRadius: '16px' }}>
                  {DEVICE_ICONS[selectedDevice.device_type] || '📦'}
                </div>
                <div>
                  <h2 style={{ margin: '0 0 4px 0', fontSize: 24, fontWeight: 700 }}>{selectedDevice.name}</h2>
                  <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>
                    {selectedDevice.room_name || 'Unassigned'} • {selectedDevice.type_display || selectedDevice.device_type.toUpperCase()}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedDevice(null)}
                style={{
                  background: 'var(--bg-input)', border: '1px solid rgba(255,255,255,0.1)',
                  color: '#fff', fontSize: 24, cursor: 'pointer', padding: '4px 12px',
                  borderRadius: '8px', zIndex: 10, display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}
                title="Close"
              >
                &times;
              </button>
            </div>

            {/* Live Telemetry */}
            <div style={{ background: 'var(--bg-base)', padding: 20, borderRadius: 16, marginBottom: 24 }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: 13, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: 1 }}>Live Telemetry</h3>
              <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 4 }}>Status</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600 }}>
                    <div className={`status-dot ${selectedDevice.status}`} style={{ position: 'static' }} />
                    {selectedDevice.status.toUpperCase()}
                  </div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 4 }}>Power Draw</div>
                  <div style={{ fontWeight: 600 }}>{selectedDevice.power_consumption_watts}W</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 4 }}>Battery</div>
                  <div style={{ fontWeight: 600 }}>{selectedDevice.battery_level !== null ? `${selectedDevice.battery_level}%` : 'AC Power'}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 4 }}>Node ID</div>
                  <div style={{ fontWeight: 600, fontSize: 12, fontFamily: 'monospace' }}>{selectedDevice.node_id}</div>
                </div>
              </div>
            </div>

            {/* Matter Diagnostics */}
            <div style={{ marginBottom: 24 }}>
              <div className="flex justify-between items-center mb-md">
                <h3 style={{ margin: 0, fontSize: 13, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: 1 }}>Diagnostic Clusters (Matter)</h3>
                {isDiagnosticsLoading && <span style={{ fontSize: 12, color: 'var(--accent-blue)' }}>Loading...</span>}
              </div>

              {!isDiagnosticsLoading && deviceDiagnostics && deviceDiagnostics.map(node => (
                <div key={node.id} style={{
                  background: 'var(--bg-base)', padding: 16, borderRadius: 12, marginBottom: 12,
                  borderLeft: `3px solid ${node.health_status === 'critical' ? 'var(--accent-red)' : node.health_status === 'degraded' ? 'var(--accent-orange)' : 'var(--accent-blue)'}`
                }}>
                  <div className="flex justify-between items-center mb-sm">
                    <div style={{ fontWeight: 600 }}>{node.cluster_name || `Cluster ${node.cluster_type}`}</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: node.health_status === 'critical' ? 'var(--accent-red)' : node.health_status === 'degraded' ? 'var(--accent-orange)' : 'var(--accent-blue)' }}>
                      {node.health_status.toUpperCase()}
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>EP: {node.endpoint_id} • Type: {node.cluster_type}</div>
                    <div style={{ fontSize: 12, background: 'rgba(255,255,255,0.05)', padding: '4px 8px', borderRadius: 6 }}>
                      AI Anomaly Score: <span style={{ fontWeight: 700, color: node.anomaly_score > 0.5 ? 'var(--accent-red)' : '#fff' }}>{node.anomaly_score.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              ))}

              {!isDiagnosticsLoading && (!deviceDiagnostics || deviceDiagnostics.length === 0) && (
                <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)', background: 'var(--bg-base)', borderRadius: 12 }}>
                  No diagnostic telemetry available.
                </div>
              )}
            </div>

            {/* Maintenance Action */}
            {(selectedDevice.status === 'critical' || selectedDevice.status === 'warning' || (deviceDiagnostics && deviceDiagnostics.some(n => n.anomaly_score > 0.5))) && (
              <div style={{ background: 'rgba(255, 60, 60, 0.1)', border: '1px solid var(--accent-red)', borderRadius: 16, padding: 20 }}>
                <h3 style={{ margin: '0 0 8px 0', color: 'var(--accent-red)', fontSize: 16 }}>⚠️ Maintenance Required</h3>
                <p style={{ margin: '0 0 16px 0', fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  The AI diagnostics engine has detected high anomaly scores in the device's operational clusters. Hardware failure or network desync is likely.
                </p>
                <button className="nav-btn active" style={{ width: '100%', background: 'var(--accent-red)', borderColor: 'var(--accent-red)', fontWeight: 700 }}>
                  Run Troubleshooter Agent
                </button>
              </div>
            )}

            <div style={{ marginTop: 32, display: 'flex', gap: 12 }}>
              <button
                className="nav-btn"
                style={{ flex: 1, borderColor: 'var(--accent-red)', color: 'var(--accent-red)', background: 'transparent' }}
                onClick={() => {
                  handleDeleteDevice(selectedDevice.id, selectedDevice.room);
                  setSelectedDevice(null);
                }}
              >
                Delete Device
              </button>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
