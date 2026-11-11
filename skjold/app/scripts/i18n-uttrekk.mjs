// Trekker ut alle brukersynlige tekster fra web-appen med TypeScript-parseren (strenger, maltekster og JSX-tekst), og
// skriver dem som ikke finnes i ordbøkene (i18n/en.ts og i18n/en-auto.ts), én per linje.
// Kjør: node scripts/i18n-uttrekk.mjs [ut-fil]      (uten ut-fil: skriver antallet)
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import ts from 'typescript';
const root = new URL('../src/', import.meta.url).pathname;
const have = new Set();
for (const f of ['i18n/en.ts', 'i18n/en-auto.ts']) {
  const sf = ts.createSourceFile(f, readFileSync(join(root, f), 'utf8'), ts.ScriptTarget.Latest, true);
  (function v(n) { if (ts.isPropertyAssignment(n) && ts.isStringLiteralLike(n.name)) have.add(n.name.text); ts.forEachChild(n, v); })(sf);
}
const files = [];
(function walk(d) { for (const f of readdirSync(d)) { const p = join(d, f); if (statSync(p).isDirectory()) { if (f !== 'i18n' && f !== 'touch') walk(p); } else if (/\.tsx?$/.test(f)) files.push(p); } })(root);
const NO = /[æøåÆØÅ]|\b(og|ikke|eller|med|til|for|på|av|som|er|du|kan|skal|har|når|alle|ingen|velg|slå|vis|spill|hent)\b/i;
const seen = new Set();
const add = (raw) => {
  const x = raw.replace(/\s+/g, ' ').trim();
  if (x.length < 2 || x.length > 400 || have.has(x)) return;
  if (!/[a-zæøå]{2}/i.test(x) || /^[a-z0-9_./:#-]+$/.test(x) || /[{};<>]|=>|\dpx|rgba?\(|^https?:|^\/api\//.test(x)) return;
  if (NO.test(x) || /^[A-ZÆØÅ][a-zæøå]{2,}( |$)/.test(x)) seen.add(x);
};
for (const f of files) {
  const sf = ts.createSourceFile(f, readFileSync(f, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  (function v(n) {
    if (ts.isImportDeclaration(n)) return;
    if (ts.isStringLiteralLike(n)) { if (!(n.parent && ts.isJsxAttribute(n.parent) && /^(style|class|d|viewBox|stroke|fill|type|key|href|src|id|name|role)/.test(n.parent.name.getText()))) add(n.text); }
    else if (ts.isJsxText(n)) add(n.text);
    else if (ts.isTemplateExpression(n)) { add(n.head.text); for (const s of n.templateSpans) add(s.literal.text); }
    ts.forEachChild(n, v);
  })(sf);
}
const l = [...seen].sort((a, b) => a.localeCompare(b, 'nb'));
if (process.argv[2]) writeFileSync(process.argv[2], l.join('\n') + '\n');
console.log(l.length + ' tekster mangler i ordbøkene');
