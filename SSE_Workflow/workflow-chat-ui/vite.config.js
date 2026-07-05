import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/workflows': 'http://127.0.0.1:8001',
      '/execution': 'http://127.0.0.1:8001',
      '/events':    'http://127.0.0.1:8001',
      '/health':    'http://127.0.0.1:8001',
    },
  },
})
