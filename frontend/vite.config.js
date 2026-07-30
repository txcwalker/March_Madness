import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// No backend API yet -- the frontend reads static JSON from public/data/
// (written by scripts/export_site_data.py), so there's no proxy to configure.
// See ../LOCALHOST_PORT_REGISTRY.md for why this project claims port 5181.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5181,
    strictPort: true,
  },
})
