// Engelsk i hele appen uten å pakke inn hver tekst: når engelsk er valgt, slås tekstene i DOM-en opp i ordboka.
// Preact tegner på norsk som før; denne ser på tekstnoder og merkelapper (aria-label, title, placeholder, alt) og bytter
// dem som finnes i ordboka. Tekster som mangler blir stående på norsk. Innhold fra brukeren (låttitler, romnavn) røres
// bare hvis det tilfeldigvis er likt en grensesnitt-tekst; sett data-noi18n på et element for å holde det helt utenfor.
import { effect } from '@preact/signals';
import { EN } from './en';
import { EN_AUTO } from './en-auto';
import { lang } from './index';

const ATTRS = ['aria-label', 'title', 'placeholder', 'alt'];
const seen = new WeakMap<Node, { nb: string; en: string }>();
const seenAttr = new WeakMap<Element, Record<string, { nb: string; en: string }>>();

/** Engelsk for en norsk tekst (mellomrom foran og bak bevares), eller null når den ikke finnes i ordboka. */
export function lookup(s: string): string | null {
  const k = s.trim();
  if (k.length < 2) return null;
  const e = EN[k] ?? EN_AUTO[k];
  return e === undefined || e === k ? null : s.replace(k, e);
}

const skip = (el: Element | null): boolean => !!el && !!el.closest('[data-noi18n],script,style,textarea,code,pre');

function text(n: Text): void {
  const cur = n.data, s = seen.get(n);
  if (s && cur === s.en) return;                       // vår egen endring
  if (skip(n.parentElement)) return;
  const en = lookup(cur);
  if (en === null) { seen.delete(n); return; }
  seen.set(n, { nb: cur, en }); n.data = en;
}
function attrs(el: Element): void {
  if (skip(el)) return;
  for (const a of ATTRS) {
    const cur = el.getAttribute(a); if (!cur) continue;
    const m = seenAttr.get(el) ?? {};
    if (m[a] && cur === m[a]!.en) continue;
    const en = lookup(cur); if (en === null) continue;
    m[a] = { nb: cur, en }; seenAttr.set(el, m); el.setAttribute(a, en);
  }
}
function walk(root: Node): void {
  if (root.nodeType === 3) { text(root as Text); return; }
  if (root.nodeType !== 1) return;
  attrs(root as Element);
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  for (let n = w.nextNode(); n; n = w.nextNode()) { if (n.nodeType === 3) text(n as Text); else attrs(n as Element); }
}
/** Tilbake til norsk: sett tilbake det vi byttet ut. */
function restore(root: Node): void {
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    if (n.nodeType === 3) { const s = seen.get(n); if (s && (n as Text).data === s.en) (n as Text).data = s.nb; seen.delete(n); }
    else { const m = seenAttr.get(n as Element); if (m) { for (const a of Object.keys(m)) if ((n as Element).getAttribute(a) === m[a]!.en) (n as Element).setAttribute(a, m[a]!.nb); seenAttr.delete(n as Element); } }
  }
}

let obs: MutationObserver | null = null;
/** Start oversetteren. Kalles én gang fra appens inngang (ikke fra Touch, som bare er norsk). */
export function startDomI18n(): void {
  if (typeof document === 'undefined' || typeof MutationObserver === 'undefined') return;
  effect(() => {
    const en = lang.value === 'en';
    document.documentElement.lang = en ? 'en' : 'no';
    if (en && !obs) {
      obs = new MutationObserver((ms) => {
        for (const m of ms) {
          if (m.type === 'characterData') text(m.target as Text);
          else if (m.type === 'attributes') attrs(m.target as Element);
          else m.addedNodes.forEach(walk);
        }
      });
      walk(document.body);
      obs.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
    } else if (!en && obs) { obs.disconnect(); obs = null; restore(document.body); }
  });
}
