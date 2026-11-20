import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

// Skjold-konto (hjem.skjold-lab.com/konto): kontosiden – profil, totrinnsbekreftelse, hjem og deling, data. Egen side i samme dist.
export default defineConfig({
  base: './',
  plugins: [preact()],
  build: { outDir: 'dist', emptyOutDir: false, target: 'es2020', sourcemap: false, assetsDir: 'konto', rollupOptions: { input: 'konto.html' } }
});
