// Kopierer statiske renderer-filer (HTML/CSS) til dist/renderer etter tsc.
const fs = require('fs');
const path = require('path');
const src = path.join(__dirname, '..', 'src', 'renderer');
const out = path.join(__dirname, '..', 'dist', 'renderer');
fs.mkdirSync(out, { recursive: true });
for (const f of fs.readdirSync(src)) {
  if (/\.(html|css|svg|png)$/.test(f)) fs.copyFileSync(path.join(src, f), path.join(out, f));
}
console.log('statiske filer kopiert til dist/renderer');
