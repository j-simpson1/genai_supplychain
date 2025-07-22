// frontend/src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import BillOfMaterials from './pages/bill_of_materials.tsx';
import ChatSystem from './pages/chat.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatSystem />} />
        <Route path="/bill_of_materials" element={<BillOfMaterials />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);