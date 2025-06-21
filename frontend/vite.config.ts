import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file from parent directory
  const parentEnv = loadEnv(mode, path.resolve('..'), 'VITE_')

  return {
    plugins: [react(), tailwindcss()],
    define: {
      // Make env variables available
      'import.meta.env.VITE_REACT_APP_STREAM_API_KEY':
        JSON.stringify(parentEnv.VITE_REACT_APP_STREAM_API_KEY)
    }
  }
})