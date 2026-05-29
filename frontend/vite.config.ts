import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 2000,
    rollupOptions: {
      output: {
        manualChunks: (id: string) => {
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) return 'vendor-react';
          if (id.includes('node_modules/recharts') || id.includes('node_modules/plotly')) return 'vendor-charts';
          if (id.includes('node_modules/@xyflow') || id.includes('node_modules/reactflow')) return 'vendor-flow';
          if (id.includes('node_modules/framer-motion') || id.includes('node_modules/lucide-react')) return 'vendor-ui';
          if (id.includes('node_modules/axios') || id.includes('node_modules/zustand')) return 'vendor-data';
        }
      }
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true, // proxy WebSocket connections too
      },
      '/ws': {
        target: 'ws://localhost:8000',
        changeOrigin: true,
        ws: true,
      }
    }
  }
})
