import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Backend al que el proxy de desarrollo reenvía los pedidos a /api/*.
// Por defecto el Django local; con VITE_BACKEND_URL se puede apuntar a otro
// host (por ejemplo un backend de pruebas compartido o un túnel).
const backend = process.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: backend,
        changeOrigin: true,
      },
    },
  },
})
