// frontend/src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import BillOfMaterials from './pages/bill_of_materials.tsx';
import ModelConfiguration from './pages/model_configuration.tsx';
import OutputPage from './pages/output.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<BillOfMaterials />} />
        <Route path="/model_configuration" element={<ModelConfiguration />} />
        <Route path="/output" element={<OutputPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);