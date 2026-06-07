import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', rewrite: (p) => p.replace(/^\/api/, '') },
      '/chat': 'http://localhost:8000',
      '/analyze': 'http://localhost:8000',
      '/backtest': 'http://localhost:8000',
      '/hypotheses': 'http://localhost:8000',
      '/positions': 'http://localhost:8000',
      '/sessions': 'http://localhost:8000',
    },
  },
})
