import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { readFileSync } from 'fs'
import { resolve } from 'path'

function getBackendPort(): number {
  try {
    const raw = readFileSync(resolve(__dirname, '..', 'ports.json'), 'utf-8')
    return JSON.parse(raw).backend_port || 8080
  } catch {
    return 8080
  }
}

const backendPort = getBackendPort()

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': `http://localhost:${backendPort}`,
    },
  },
})
