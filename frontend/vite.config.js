import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// API calls go to /api which Caddy proxies to the backend.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
  build: { outDir: 'dist' }
})
