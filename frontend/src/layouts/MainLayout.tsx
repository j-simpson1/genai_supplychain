import React from 'react';
import { Box } from '@mui/material';
import Header from '../components/Header';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header />
      <Box
        component="main"
        sx={{
          flex: 1,
          px: 2,
          py: 4,
          backgroundColor: 'background.default'
        }}
      >
        {children}
      </Box>
    </Box>
  );
};