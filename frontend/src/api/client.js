const API_BASE = '/api';

async function fetchJSON(url) {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  return data.results !== undefined ? data.results : data;
}

export const api = {
  dashboard: {
    homes: () => fetchJSON('/dashboard/homes/'),
    createHome: (name) =>
      fetch(`${API_BASE}/dashboard/homes/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      }).then((r) => r.json()),
    updateHome: (id, name) =>
      fetch(`${API_BASE}/dashboard/homes/${id}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      }).then((r) => r.json()),
    deleteHome: (id) =>
      fetch(`${API_BASE}/dashboard/homes/${id}/`, { method: 'DELETE' }),
    rooms: (homeId) => fetchJSON(`/dashboard/rooms/${homeId ? `?home=${homeId}` : ''}`),
    createRoom: (payload) =>
      fetch(`${API_BASE}/dashboard/rooms/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then((r) => r.json()),
    updateRoom: (id, payload) =>
      fetch(`${API_BASE}/dashboard/rooms/${id}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then((r) => r.json()),
    deleteRoom: (id) =>
      fetch(`${API_BASE}/dashboard/rooms/${id}/`, { method: 'DELETE' }),
    devices: () => fetchJSON('/dashboard/devices/'),
    createDevice: (payload) =>
      fetch(`${API_BASE}/dashboard/devices/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then((r) => r.json()),
    updateDevice: (id, payload) =>
      fetch(`${API_BASE}/dashboard/devices/${id}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then((r) => r.json()),
    deleteDevice: (id) =>
      fetch(`${API_BASE}/dashboard/devices/${id}/`, { method: 'DELETE' }),
    scanNetwork: () => fetchJSON('/dashboard/devices/scan/'),
    healthScore: (homeId) => fetchJSON(`/dashboard/health-score/latest/${homeId ? '?home=' + homeId : ''}`),
  },
  diagnostics: {
    nodes: () => fetchJSON('/diagnostics/nodes/'),
    nodesByDevice: (deviceId) => fetchJSON(`/diagnostics/nodes/?device_id=${deviceId}`),
    generateMockNodes: (deviceId) =>
      fetch(`${API_BASE}/diagnostics/nodes/generate-mock/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: deviceId }),
      }).then((r) => r.json()),
    anomalous: () => fetchJSON('/diagnostics/nodes/anomalous/'),
    logs: (nodeId) => fetchJSON(`/diagnostics/logs/${nodeId}/`),
  },
  troubleshooter: {
    createSession: () =>
      fetch(`${API_BASE}/troubleshooter/sessions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Session' }),
      }).then((r) => r.json()),
    sessions: () => fetchJSON('/troubleshooter/sessions/'),
    renameSession: (id, title) =>
      fetch(`${API_BASE}/troubleshooter/sessions/${id}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      }).then((r) => r.json()),
    deleteSession: (id) =>
      fetch(`${API_BASE}/troubleshooter/sessions/${id}/`, { method: 'DELETE' }),
    uploadManual: (file) => {
      const formData = new FormData();
      formData.append('file', file);
      return fetch(`${API_BASE}/troubleshooter/manuals/upload/`, {
        method: 'POST',
        body: formData,
      }).then((r) => r.json());
    },
  },
  observability: {
    traces: (sessionId) => fetchJSON(`/observability/traces/?session=${sessionId}`),
    metrics: () => fetchJSON('/observability/metrics/'),
    summary: () => fetchJSON('/observability/metrics/summary/'),
  },
};

export function createChatSocket(sessionId, handlers) {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${protocol}://${window.location.host}/ws/chat/${sessionId}/`;
  const ws = new WebSocket(wsUrl);
  ws.onopen = () => handlers.onOpen?.();
  ws.onmessage = (e) => {
    try { handlers.onMessage?.(JSON.parse(e.data)); } catch {}
  };
  ws.onclose = () => handlers.onClose?.();
  ws.onerror = (e) => handlers.onError?.(e);
  return ws;
}
