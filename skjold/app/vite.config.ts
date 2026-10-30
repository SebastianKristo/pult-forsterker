import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

// base './' => relative asset paths, so the build works from '/', '/app/' or file://
export default defineConfig({
  base: './',
  plugins: [preact()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'es2020',
    sourcemap: false,
    cssCodeSplit: false
  },
  server: {
    port: 5173,
    // dev: proxy the API to a daemon on localhost (KI_AMP_PORT=8765)
    proxy: { '/api': { target: process.env.SKJOLD_API ?? 'http://127.0.0.1:8765', changeOrigin: true } }
  }
});
