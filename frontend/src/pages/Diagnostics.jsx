import React, { useState, useEffect } from 'react';
import { api } from '../api/client.js';

export default function Diagnostics() {
  const [nodes, setNodes] = useState([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    api.diagnostics.nodes().then(setNodes).catch(() => {});
  }, []);

  const filtered = filter === 'all' ? nodes
    : filter === 'anomalous' ? nodes.filter((n) => n.anomaly_score >= 0.5)
    : nodes.filter((n) => n.health_status === filter);

  return (
    <div>
      {/* Filter bar */}
      <div className="flex items-center justify-between mb-md">
        <div className="section-title" style={{ margin: 0 }}>Matter Protocol Nodes ({filtered.length})</div>
        <div className="flex gap-sm">
          {['all', 'healthy', 'degraded', 'critical'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`nav-btn ${filter === f ? 'active' : ''}`}
              style={{ width: 'auto', padding: '6px 14px', fontSize: 12, fontWeight: 600, textTransform: 'capitalize' }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Predictive Maintenance Summary */}
      {nodes.filter((n) => n.anomaly_score >= 0.5).length > 0 && (
        <div className="neu-card" style={{ marginBottom: 20, borderLeft: '3px solid var(--accent-amber)' }}>
          <div className="flex items-center gap-md">
            <span style={{ fontSize: 24 }}>⚠️</span>
            <div>
              <strong style={{ color: 'var(--accent-amber)' }}>Predictive Maintenance Alert</strong>
              <p className="text-sm text-muted" style={{ marginTop: 4 }}>
                {nodes.filter((n) => n.anomaly_score >= 0.5).length} device cluster(s) showing anomalous
                behavior patterns. LSTM-based scoring flagged elevated power/vibration signatures.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Nodes Table */}
      <div className="neu-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="diag-table">
          <thead>
            <tr>
              <th>Device</th>
              <th>Room</th>
              <th>Cluster</th>
              <th>Node / EP</th>
              <th>Health</th>
              <th>Anomaly Score</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((node) => (
              <tr key={node.id}>
                <td style={{ fontWeight: 600 }}>{node.device_name}</td>
                <td className="text-muted">{node.room_name}</td>
                <td>
                  <span className="font-mono" style={{ fontSize: 11, color: 'var(--accent-cyan)' }}>
                    {node.cluster_type}
                  </span>{' '}
                  <span className="text-sm">{node.cluster_name}</span>
                </td>
                <td className="font-mono text-sm">{node.node_id} / EP{node.endpoint_id}</td>
                <td>
                  <span className={`anomaly-badge ${node.health_status}`}>
                    {node.health_status}
                  </span>
                </td>
                <td>
                  <span className="font-mono" style={{
                    color: node.anomaly_score >= 0.8 ? 'var(--accent-red)'
                      : node.anomaly_score >= 0.5 ? 'var(--accent-amber)'
                      : 'var(--accent-green)',
                    fontWeight: 600,
                  }}>
                    {(node.anomaly_score * 100).toFixed(1)}%
                  </span>
                  <div className="anomaly-bar">
                    <div
                      className="anomaly-bar-fill"
                      style={{
                        width: `${node.anomaly_score * 100}%`,
                        background: node.anomaly_score >= 0.8 ? 'var(--accent-red)'
                          : node.anomaly_score >= 0.5 ? 'var(--accent-amber)'
                          : 'var(--accent-green)',
                      }}
                    />
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: '#555' }}>No nodes match the current filter.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
