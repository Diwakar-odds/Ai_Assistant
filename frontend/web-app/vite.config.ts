import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './', // Use relative paths for Flask serving
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['framer-motion', 'lucide-react'],
        },
      },
    },
  },
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err: any, req, res) => {
            if (err.code === 'ECONNREFUSED') {
              // Suppress scary terminal errors during backend startup
              if (!res.headersSent) {
                res.writeHead(503, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Backend is starting up, please wait.' }));
              }
            }
          });
        }
      },
      '/socket.io': {
        target: 'http://localhost:5000',
        ws: true,
        configure: (proxy) => {
          proxy.on('error', (err: any) => {
            if (err.code === 'ECONNREFUSED') {
              // Suppress websocket connection errors silently during startup
            }
          });
        }
      },
    },
  },
  preview: {
    port: 4173,
  },
});
