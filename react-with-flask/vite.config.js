import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:5001',
    }
  },
  build: {
    // Ensure assets are properly referenced
    outDir: 'dist',
    // Generate source maps for debugging
    sourcemap: false,
    // Optimize build for production
    minify: 'esbuild',
    target: 'es2015'
  },
  // Handle environment-specific API URLs
  define: {
    // These will be replaced at build time
    __API_URL__: JSON.stringify(
      process.env.NODE_ENV === 'production' 
        ? 'https://your-flask-api-service.onrender.com'
        : 'http://localhost:5001'
    )
  }
})
