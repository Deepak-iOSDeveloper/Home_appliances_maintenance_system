import React, { useState, useEffect, useRef } from 'react';
import { api, createChatSocket } from '../api/client.js';

export default function Troubleshooter() {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [socket, setSocket] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setIsUploading(true);
    // Add a local feedback message
    const uploadId = Date.now();
    setMessages(prev => [...prev, { role: 'system', content: `📡 Processing Manual: **${file.name}**...`, id: uploadId }]);
    
    try {
      const res = await api.troubleshooter.uploadManual(file);
      if (res.error) {
        setMessages(prev => [
          ...prev, 
          { role: 'assistant', content: `❌ **Upload Failed**: ${res.error}` }
        ]);
      } else {
        setMessages(prev => [
          ...prev, 
          { role: 'assistant', content: `✅ **Manual Indexed**: I have analyzed **${file.name}** (${res.chunks_created} sections). Your Troubleshooter is now smarter!` }
        ]);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev, 
        { role: 'assistant', content: `❌ **Upload Failed**: Could not process PDF. Please ensure it's a valid text-based PDF.` }
      ]);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  useEffect(() => {
    api.troubleshooter.sessions().then(data => {
      setSessions(Array.isArray(data) ? data : []);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleCreateSession = async () => {
    try {
      const session = await api.troubleshooter.createSession();
      setSessions([session, ...sessions]);
      selectSession(session.id, session.session_id);
    } catch(e) {
      console.error(e);
    }
  };

  const selectSession = async (internalId, socketId) => {
    if (socket) socket.close();
    setActiveSession(socketId);
    
    // Fetch history
    try {
      const res = await fetch(`/api/troubleshooter/sessions/${internalId}/messages/`);
      if (!res.ok) throw new Error('API failed');
      const history = await res.json();
      setMessages(Array.isArray(history.results) ? history.results : Array.isArray(history) ? history : []);
    } catch(e) {
      setMessages([]);
    }
    
    // Connect WebSocket
    const ws = createChatSocket(socketId, {
      onOpen: () => console.log('WS Connected'),
      onMessage: handleSocketMessage,
      onClose: () => console.log('WS Disconnected'),
    });
    setSocket(ws);
  };

  const handleSocketMessage = (data) => {
    if (data.type === 'chunk') {
      setIsTyping(false);
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant' && !last.isFinished) {
          const updated = { ...last, content: last.content + data.content };
          return [...prev.slice(0, -1), updated];
        } else {
          return [...prev, { role: 'assistant', content: data.content, isFinished: false }];
        }
      });
    } else if (data.type === 'sources') {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant') {
          return [...prev.slice(0, -1), { ...last, sources: data.content }];
        }
        return prev;
      });
    } else if (data.type === 'done') {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant') {
          return [...prev.slice(0, -1), { ...last, isFinished: true }];
        }
        return prev;
      });
    } else if (data.type === 'error') {
      setIsTyping(false);
      setMessages((prev) => [...prev, { role: 'system', content: `Error: ${data.content}` }]);
    } else if (data.type === 'connected') {
      setMessages((prev) => [...prev, { role: 'system', content: data.content.message }]);
    }
  };

  const handleSend = () => {
    if (!input.trim() || !socket) return;
    
    const msg = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setIsTyping(true);
    
    socket.send(JSON.stringify({ query: msg }));
  };

  return (
    <div className="dashboard-grid" style={{ height: 'calc(100vh - 120px)' }}>
      {/* Sidebar: Session List */}
      <div className="neu-card" style={{ display: 'flex', flexDirection: 'column', padding: 0 }}>
        <div style={{ padding: 20, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <button 
            className="chat-send-btn" 
            style={{ width: '100%', borderRadius: 8, height: 40, fontSize: 14 }}
            onClick={handleCreateSession}
          >
            + New Chat
          </button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '10px 0' }}>
          {sessions.map((s) => (
            <div 
              key={s.id} 
              onClick={() => selectSession(s.id, s.session_id)}
              style={{
                padding: '12px 20px', cursor: 'pointer',
                background: activeSession === s.session_id ? 'rgba(0, 245, 255, 0.1)' : 'transparent',
                borderLeft: activeSession === s.session_id ? '3px solid var(--accent-cyan)' : '3px solid transparent',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{s.title}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {new Date(s.started_at).toLocaleDateString()}
                </div>
              </div>
              <div className="flex gap-sm">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm(`Delete session "${s.title}"?`)) {
                      api.troubleshooter.deleteSession(s.id).then(() => {
                        const newSessions = sessions.filter(sess => sess.id !== s.id);
                        setSessions(newSessions);
                        if (activeSession === s.session_id) {
                          setActiveSession(null);
                          setMessages([]);
                        }
                      });
                    }
                  }}
                  style={{
                    background: 'transparent', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', fontSize: 16,
                    opacity: 0.7, padding: '0 4px'
                  }}
                  onMouseEnter={(e) => e.target.style.opacity = 1}
                  onMouseLeave={(e) => e.target.style.opacity = 0.7}
                  title="Delete Session"
                >
                  ×
                </button>
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    const newTitle = window.prompt("Enter new session name:", s.title);
                    if (newTitle && newTitle.trim() !== "" && newTitle !== s.title) {
                      api.troubleshooter.renameSession(s.id, newTitle.trim()).then(() => {
                        setSessions(sessions.map(sess => sess.id === s.id ? { ...sess, title: newTitle.trim() } : sess));
                      });
                    }
                  }}
                  style={{
                    background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 14,
                    opacity: 0.7, padding: '0 4px'
                  }}
                  onMouseEnter={(e) => e.target.style.opacity = 1}
                  onMouseLeave={(e) => e.target.style.opacity = 0.7}
                  title="Rename Session"
                >
                  ✎
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="neu-card" style={{ display: 'flex', flexDirection: 'column', padding: 0 }}>
        {!activeSession ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
            Select or create a chat session to begin troubleshooting.
          </div>
        ) : (
          <>
            <div className="chat-messages">
              {messages.map((m, i) => (
                <div key={i} className={`chat-msg ${m.role}`}>
                  {/* Basic Markdown Rendering */}
                  {m.content.split('\n').map((line, j) => {
                    if (line.startsWith('## ')) return <h2 key={j}>{line.replace('## ', '')}</h2>;
                    if (line.startsWith('### ')) return <h3 key={j} style={{marginTop: 10, marginBottom: 5}}>{line.replace('### ', '')}</h3>;
                    if (line.startsWith('- ')) return <li key={j} style={{marginLeft: 20, marginBottom: 4}}>{line.replace('- ', '')}</li>;
                    if (line.startsWith('**') && line.endsWith('**')) return <strong key={j}>{line.replace(/\*\*/g, '')}</strong>;
                    if (line.startsWith('> ')) return <blockquote key={j} style={{borderLeft: '3px solid var(--accent-amber)', paddingLeft: 10, color: 'var(--accent-amber)', margin: '10px 0'}}>{line.replace('> ', '')}</blockquote>;
                    
                    // Inline bold parsing (hacky but works for demo)
                    const parts = line.split(/(\*\*.*?\*\*)/);
                    return (
                      <p key={j} style={{ marginBottom: 6 }}>
                        {parts.map((p, k) => p.startsWith('**') ? <strong key={k}>{p.replace(/\*\*/g, '')}</strong> : p)}
                      </p>
                    );
                  })}
                  
                  {m.sources && m.sources.length > 0 && (
                    <div className="chat-sources">
                      <strong>Sources:</strong> {m.sources.map(s => `[${s.title}]`).join(', ')}
                    </div>
                  )}
                </div>
              ))}
              
              {isTyping && (
                <div className="chat-msg assistant typing-indicator">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            
            <div className="chat-input-bar" style={{ gap: 0 }}>
              <button 
                className="chat-upload-btn" 
                onClick={() => fileInputRef.current.click()}
                disabled={isUploading}
                style={{ 
                  background: 'none', border: 'none', color: 'var(--accent-blue)', 
                  fontSize: 24, cursor: 'pointer', padding: '0 16px', fontWeight: 'bold'
                }}
                title="Upload Device Manual (PDF)"
              >
                {isUploading ? '⌛' : '+'}
              </button>
              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleFileUpload} 
                style={{ display: 'none' }} 
                accept=".pdf"
              />
              <input 
                type="text" 
                className="chat-input"
                placeholder={isUploading ? "Reading manual..." : "E.g., Check my smart lock or why is my thermostat offline?"}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                disabled={isUploading}
              />
              <button className="chat-send-btn" onClick={handleSend} disabled={!input.trim() || isUploading}>
                ↑
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
