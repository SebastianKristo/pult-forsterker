import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

// Skjold Touch-skjermen (800 × 480, kiosk): egen side i samme dist, serveres av daemonen på /touch.html.
export default defineConfig({
  base: './',
  plugins: [preact()],
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    target: 'es2020',
    sourcemap: false,
    assetsDir: 'touch',
    rollupOptions: { input: 'touch.html' }
  }
});
