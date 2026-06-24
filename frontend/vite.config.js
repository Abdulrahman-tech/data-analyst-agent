import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Forward API calls to Flask so we avoid CORS issues in dev
      '/upload':  'http://localhost:5001',
      '/analyze': 'http://localhost:5001',
      '/health':  'http://localhost:5001',
      '/report':  'http://localhost:5001',
    }
  }
})
