// frontend/src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import BillOfMaterials from './pages/Bill_of_Materials.tsx';
import ModelConfiguration from './pages/model_configuration.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<BillOfMaterials />} />
        <Route path="/model_configuration" element={<ModelConfiguration />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);