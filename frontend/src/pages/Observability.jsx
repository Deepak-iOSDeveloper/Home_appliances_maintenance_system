import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client.js';

export default function Observability() {
  const [metrics, setMetrics] = useState([]);
  const [summary, setSummary] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState('');
  const [traces, setTraces] = useState([]);

  useEffect(() => {
    api.observability.metrics().then((data) => {
      setMetrics(Array.isArray(data) ? [...data].reverse() : []); // Chronological for chart
    }).catch(() => {});
    
    api.observability.summary().then(setSummary).catch(() => {});
    api.troubleshooter.sessions().then(setSessions).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedSession) {
      api.observability.traces(selectedSession).then(setTraces).catch(() => {});
    } else {
      setTraces([]);
    }
  }, [selectedSession]);

  return (
    <div>
      {/* Top Metrics Cards */}
      <div className="metrics-grid">
        <div className="neu-card metric-card">
          <div className="metric-value">{summary && summary.avg_latency != null ? Math.round(summary.avg_latency) : 0}ms</div>
          <div className="metric-label">Avg E2E Latency</div>
        </div>
        <div className="neu-card metric-card">
          <div className="metric-value">{summary && summary.avg_p95 != null ? Math.round(summary.avg_p95) : 0}ms</div>
          <div className="metric-label">P95 Latency</div>
        </div>
        <div className="neu-card metric-card">
          <div className="metric-value" style={{ color: 'var(--accent-amber)' }}>
            {summary && summary.total_tokens != null ? (summary.total_tokens / 1000).toFixed(1) : 0}k
          </div>
          <div className="metric-label">Total Tokens</div>
        </div>
        <div className="neu-card metric-card">
          <div className="metric-value" style={{ color: 'var(--accent-green)' }}>
            ${summary && summary.total_cost != null ? summary.total_cost.toFixed(4) : '0.0000'}
          </div>
          <div className="metric-label">Estimated Cost</div>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Latency Chart */}
        <div className="neu-card">
          <div className="section-title">Session Latency Trend (ms)</div>
          <div style={{ height: 250 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-cyan)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--accent-cyan)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="session_title" hide />
                <YAxis stroke="rgba(255,255,255,0.2)" fontSize={11} tickFormatter={(val) => `${val}ms`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                  itemStyle={{ color: 'var(--accent-cyan)' }}
                />
                <Area type="monotone" dataKey="total_latency_ms" name="Latency" stroke="var(--accent-cyan)" strokeWidth={2} fillOpacity={1} fill="url(#colorLatency)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Trace Inspector */}
        <div className="neu-card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="flex items-center justify-between mb-md">
            <div className="section-title" style={{ margin: 0 }}>Agent Thought Traces</div>
            <select 
              value={selectedSession} 
              onChange={(e) => setSelectedSession(e.target.value)}
              style={{
                background: 'var(--bg-input)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)',
                padding: '6px 12px', borderRadius: 8, outline: 'none'
              }}
            >
              <option value="">Select a session to inspect...</option>
              {sessions.map(s => (
                <option key={s.id} value={s.session_id}>{s.title}</option>
              ))}
            </select>
          </div>
          
          <div style={{ flex: 1, overflowY: 'auto', maxHeight: 400 }}>
            {!selectedSession ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: 40 }}>
                Select a session from the dropdown to view its execution trace.
              </div>
            ) : traces.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: 40 }}>
                No traces recorded for this session.
              </div>
            ) : (
              <div className="trace-timeline">
                {traces.map((trace) => (
                  <div key={trace.id} className={`trace-step ${trace.step_type}`}>
                    <div className="trace-step-header">
                      <span className={`trace-step-type ${trace.step_type}`}>
                        {trace.step_type_display || trace.step_type}
                      </span>
                      <span className="trace-step-meta">{trace.duration_ms}ms • {trace.token_count} tokens</span>
                    </div>
                    {trace.tools_used && trace.tools_used.length > 0 && (
                      <div className="trace-step-meta" style={{ marginBottom: 4 }}>
                        Tools invoked: <span className="font-mono text-cyan">{trace.tools_used.join(', ')}</span>
                      </div>
                    )}
                    <div className="trace-step-summary">
                      <strong style={{ color: 'var(--text-primary)' }}>Input:</strong> {trace.input_summary}
                    </div>
                    <div className="trace-step-summary" style={{ marginTop: 6 }}>
                      <strong style={{ color: 'var(--text-primary)' }}>Output:</strong> {trace.output_summary}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
