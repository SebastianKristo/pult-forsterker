import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';
import type { Plugin } from 'vite';

// ki_amp_daemon.py serverer nå hele mappen på '/' (og fortsatt under '/app/'), så inlining er ikke lenger nødvendig der,
// men JS og CSS legges fortsatt inn i index.html: én fil å cache, og den virker også fra eldre daemoner og file://.
function inlineEntry(): Plugin {
  return {
    name: 'skjold-inline-entry',
    apply: 'build',
    enforce: 'post',
    generateBundle(_o, bundle) {
      const html = bundle['index.html'];
      if (!html || html.type !== 'asset') return;
      let src = String(html.source);
      for (const [name, f] of Object.entries(bundle)) {
        if (f.type === 'chunk' && f.isEntry) {
          const tag = new RegExp(`<script type="module" crossorigin src="\\./${name.replace(/[.]/g, '\\.')}"></script>`);
          src = src.replace(tag, () => `<script type="module">${f.code.replace(/<\/script/gi, '<\\/script')}</script>`);
          delete bundle[name];
        } else if (f.type === 'asset' && name.endsWith('.css')) {
          const tag = new RegExp(`<link rel="stylesheet" crossorigin href="\\./${name.replace(/[.]/g, '\\.')}">`);
          src = src.replace(tag, () => `<style>${String(f.source)}</style>`);
          delete bundle[name];
        }
      }
      html.source = src;
    }
  };
}

// base './' => relative asset paths, so the build works from '/', '/app/' or file://
export default defineConfig({
  base: './',
  plugins: [preact(), inlineEntry()],
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
