import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Diagnostics from './pages/Diagnostics.jsx';
import Troubleshooter from './pages/Troubleshooter.jsx';
import Observability from './pages/Observability.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/diagnostics" element={<Diagnostics />} />
          <Route path="/troubleshooter" element={<Troubleshooter />} />
          <Route path="/observability" element={<Observability />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
