// frontend/src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import ReportSetup from './pages/report_setup.tsx';
import ChatSystem from './pages/chat.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ReportSetup />} />
        <Route path="/chat" element={<ChatSystem />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);