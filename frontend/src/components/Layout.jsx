import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

const navItems = [
  { path: '/', icon: '⬡', label: 'Dashboard' },
  { path: '/diagnostics', icon: '⚙', label: 'Diagnostics' },
  { path: '/troubleshooter', icon: '◉', label: 'Troubleshooter' },
  { path: '/observability', icon: '◈', label: 'Observability' },
];

const pageTitles = {
  '/': 'Digital Twin — Dashboard',
  '/diagnostics': 'Hardware Intelligence — Diagnostics',
  '/troubleshooter': 'Neural Troubleshooter — Chat',
  '/observability': 'MLOps — Observability',
};

export default function Layout() {
  const location = useLocation();
  const title = pageTitles[location.pathname] || 'ARHIS';

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">AR</div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-btn ${isActive ? 'active' : ''}`}
              title={item.label}
              end={item.path === '/'}
            >
              {item.icon}
            </NavLink>
          ))}
        </nav>
        <div className="nav-btn" title="ARHIS v1.0" style={{ fontSize: 10, color: '#444' }}>
          v1
        </div>
      </aside>
      <div className="main-content">
        <header className="topbar">
          <h1>{title}</h1>
          <div className="topbar-right">
            <span className="topbar-badge">● System Active</span>
          </div>
        </header>
        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
