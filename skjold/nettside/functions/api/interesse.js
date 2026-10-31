// Cloudflare Pages Function: /api/interesse
// POST: lagrer en interessemelding i KV (binding INTERESSE). Tar imot JSON (fetch fra skjemaet)
//       eller application/x-www-form-urlencoded (skjema uten JS -> 303 til /takk/ eller /takk/feil/, /en/thanks/ eller /en/thanks/error/ når lang=en).
// GET  ?nokkel=<ADMIN_NOKKEL>: lister alle meldinger som JSON (legg til &format=csv for CSV).
// Miljø: INTERESSE (KV, påkrevd), ADMIN_NOKKEL (hemmelig), VARSEL_WEBHOOK (valgfri, Discord/Slack/Homey).
//
// Vern: honningfelt (`nettsted`), størrelsesgrense, Origin-sjekk, enkel rate-limit per IP (hash) i KV,
// og én post per e-postadresse (ny innsending overskriver den gamle i stedet for å fylle opp KV).

const MAKS_BYTES = 8 * 1024;
const GRENSE = 5;            // innsendinger
const VINDU_S = 600;         // per 10 minutter per IP
const EPOST_RE = /^[^@\s<>"']{1,64}@[^@\s<>"']{1,190}\.[^@\s<>"'.]{2,}$/;
const PRODUKT = ['S1', 'Node', 'Begge'];
const TYPE = ['done', 'kit'];

const rens = (v, n) => String(v ?? '').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, '').trim().slice(0, n);

async function sha256(s) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, '0')).join('');
}

// Språk for omdirigeringen: skjemafeltet `lang` (eller `spraak`), ellers Referer-stien (/en/...). Norsk er standard.
function spraakFra(b, request) {
  const v = b && typeof b === 'object' ? (b.lang || b.spraak) : '';
  if (v === 'en') return 'en';
  if (v) return 'no';
  try { return new URL(request.headers.get('referer') || '').pathname.startsWith('/en/') ? 'en' : 'no'; } catch { return 'no'; }
}

function svar(erSkjema, ok, status, url, lang = 'no') {
  if (erSkjema) {
    const dest = new URL(lang === 'en' ? (ok ? '/en/thanks/' : '/en/thanks/error/') : (ok ? '/takk/' : '/takk/feil/'), url);
    return new Response(null, { status: 303, headers: { Location: dest.pathname, 'Cache-Control': 'no-store' } });
  }
  return Response.json(ok ? { ok: true } : { ok: false, feil: status }, { status: ok ? 200 : status, headers: { 'Cache-Control': 'no-store' } });
}

export async function onRequestPost({ request, env, waitUntil }) {
  const url = new URL(request.url);
  const ct = (request.headers.get('content-type') || '').toLowerCase();
  const erSkjema = ct.startsWith('application/x-www-form-urlencoded') || ct.startsWith('multipart/form-data');
  let lang = spraakFra(null, request);

  const origin = request.headers.get('origin');
  if (origin && origin !== url.origin) return svar(erSkjema, false, 403, url, lang);
  if (!env.INTERESSE) return svar(erSkjema, false, 503, url, lang);

  const lengde = +(request.headers.get('content-length') || 0);
  if (lengde > MAKS_BYTES) return svar(erSkjema, false, 413, url, lang);

  let b;
  try {
    const tekst = await request.text();
    if (tekst.length > MAKS_BYTES) return svar(erSkjema, false, 413, url, lang);
    if (erSkjema && ct.startsWith('multipart/')) return svar(erSkjema, false, 415, url, lang);
    b = erSkjema ? Object.fromEntries(new URLSearchParams(tekst)) : JSON.parse(tekst);
    if (!b || typeof b !== 'object' || Array.isArray(b)) throw 0;
    lang = spraakFra(b, request);
  } catch { return svar(erSkjema, false, 400, url, lang); }

  // Honningfelt: roboter fyller det ut. Svar "ok" så de ikke prøver på nytt, men lagre ingenting.
  if (rens(b.nettsted, 200)) return svar(erSkjema, true, 200, url, lang);

  const navn = rens(b.navn, 120);
  const epost = rens(b.epost, 200).toLowerCase();
  if (!navn || !EPOST_RE.test(epost)) return svar(erSkjema, false, 422, url, lang);

  // Rate-limit per IP (bare hash lagres). KV er "eventually consistent", så dette er et grovt vern.
  const ip = request.headers.get('cf-connecting-ip') || 'ukjent';
  const rlKey = 'rl:' + (await sha256(ip + ':' + (env.ADMIN_NOKKEL || 'skjold'))).slice(0, 32);
  const teller = parseInt((await env.INTERESSE.get(rlKey)) || '0', 10) || 0;
  if (teller >= GRENSE) return svar(erSkjema, false, 429, url, lang);
  await env.INTERESSE.put(rlKey, String(teller + 1), { expirationTtl: VINDU_S });

  const rec = {
    navn, epost,
    produkt: PRODUKT.includes(b.produkt) ? b.produkt : 'Begge',
    type: TYPE.includes(b.type) ? b.type : 'done',
    melding: rens(b.melding, 2000),
    spraak: lang,
    side: rens(b.side, 100),
    tid: new Date().toISOString(),
    land: request.headers.get('cf-ipcountry') || '',
  };
  await env.INTERESSE.put('i:' + epost, JSON.stringify(rec));

  if (env.VARSEL_WEBHOOK) {
    const p = fetch(env.VARSEL_WEBHOOK, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: `Ny interesse for Skjold ${rec.produkt} (${rec.type}): ${rec.navn} <${rec.epost}> ${rec.melding}`.slice(0, 1900) }),
    }).catch(() => {});
    if (waitUntil) waitUntil(p); else await p;
  }
  return svar(erSkjema, true, 200, url, lang);
}

function likTid(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let r = 0; for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

export async function onRequestGet({ request, env }) {
  const q = new URL(request.url).searchParams;
  if (!env.ADMIN_NOKKEL || !likTid(q.get('nokkel') || '', env.ADMIN_NOKKEL)) return new Response('forbidden', { status: 403, headers: { 'Cache-Control': 'no-store' } });
  const out = [];
  let cursor;
  do {
    const list = await env.INTERESSE.list({ prefix: 'i:', cursor });
    for (const { name } of list.keys) { const v = await env.INTERESSE.get(name); if (v) out.push(JSON.parse(v)); }
    cursor = list.list_complete ? undefined : list.cursor;
  } while (cursor);
  out.sort((a, b) => a.tid < b.tid ? -1 : 1);
  if (q.get('format') === 'csv') {
    const k = ['tid', 'navn', 'epost', 'produkt', 'type', 'melding', 'land', 'side'];
    const c = v => '"' + String(v ?? '').replace(/^([=+\-@])/, "'$1").replace(/"/g, '""') + '"';
    return new Response([k.join(','), ...out.map(r => k.map(x => c(r[x])).join(','))].join('\n'), { headers: { 'Content-Type': 'text/csv; charset=utf-8', 'Cache-Control': 'no-store' } });
  }
  return Response.json(out, { headers: { 'Cache-Control': 'no-store' } });
}

export async function onRequest({ request }) {
  return new Response('method not allowed', { status: 405, headers: { Allow: 'GET, POST' } });
}
