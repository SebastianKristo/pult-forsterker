// Dekning for engelsk i web-appen (inkl. Touch): finner norske, brukersynlige tekster (JSX-tekst og strenger med norske
// ord/bokstaver) og teller hvor mange som finnes i ordboka src/i18n/en.ts. Grovt, men godt nok til å følge fremdriften.
// Kjør: node scripts/i18n-dekning.mjs [--mangler]
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
const root = new URL('../src/', import.meta.url).pathname;
const en = readFileSync(join(root, 'i18n/en.ts'), 'utf8');
const dict = new Set([...en.matchAll(/^\s*'((?:[^'\\]|\\.)+)':/gm), ...en.matchAll(/, '((?:[^'\\]|\\.)+)':/g)].map((m) => m[1].replace(/\\'/g, "'")));
const files = [];
(function walk(d) { for (const f of readdirSync(d)) { const p = join(d, f); if (statSync(p).isDirectory()) { if (f !== 'i18n') walk(p); } else if (/\.tsx?$/.test(f)) files.push(p); } })(root);
const NO = /[æøåÆØÅ]|\b(og|ikke|eller|med|til|for|på|av|som|er|du|kan|skal|har|når|alle|ingen|velg|slå|vis|spill|hent)\b/i;
const seen = new Set();
for (const f of files) {
  const s = readFileSync(f, 'utf8');
  for (const m of s.matchAll(/>([^<>{}\n]{2,})</g)) seen.add(m[1].trim());
  for (const m of s.matchAll(/'([^'\n\\]{2,80})'/g)) seen.add(m[1]);
}
const ui = [...seen].filter((x) => /[A-Za-zæøåÆØÅ]/.test(x) && NO.test(x) && !/^[a-z0-9_./:-]+$/.test(x) && !/[{};=<>]|https?:|^#|px|rgba?\(/.test(x));
const done = ui.filter((x) => dict.has(x));
console.log(`Web-app og Touch: ${done.length} av ${ui.length} norske tekster har engelsk oversettelse (${Math.round((100 * done.length) / ui.length)} %).`);
if (process.argv.includes('--mangler')) for (const m of ui.filter((x) => !dict.has(x)).slice(0, 500)) console.log('  ·', m);
