// Cloudflare Pages Function: /api/admin/*  – backend for den visuelle editoren på /admin/.
// «Publiser» = commit til GitHub (main), som utløser .github/workflows/nettside.yml og ny utrulling.
//
// Auth: header `Authorization: Bearer <ADMIN_NOKKEL>` (konstant-tid-sammenligning). Feilede forsøk telles
// per IP-hash i KV (INTERESSE, nøkkel `arl:`), maks 10 per 15 min.
//
// Endepunkter (stier er relative til skjold/nettside):
//   GET  /api/admin/ping                                  -> { ok, github } (sjekk av nøkkel)
//   GET  /api/admin/pages                                 -> { pages: ["index.html", "en/index.html", ...] }
//   GET  /api/admin/page?path=x.html                      -> { path, html, sha }
//   POST /api/admin/page   {path, html, sha?, message?}   -> { ok, sha, commit }
//   POST /api/admin/upload {name, base64}                 -> { ok, path: "/assets/img/opplastet/..." }
//   POST /api/admin/new    {from, to}                     -> { ok, path, sha }
//
// Miljø: ADMIN_NOKKEL (secret), GITHUB_TOKEN (secret, fine-grained PAT med Contents: read/write),
//        GITHUB_REPO (valgfri, standard SebastianKristo/pult-forsterker), GITHUB_BRANCH (valgfri, main),
//        GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL (valgfri), INTERESSE (KV, brukes til rate-limit).

const ROT = 'skjold/nettside/';
const BILDE_MAPPE = 'assets/img/opplastet/';
const MAKS_HTML = 1024 * 1024;          // 1 MB per side
const MAKS_BILDE = 5 * 1024 * 1024;     // 5 MB per bilde
const GRENSE = 10, VINDU_S = 900;       // feilede innlogginger per IP per 15 min
const NO_STORE = { 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' };

const json = (data, status = 200) => Response.json(data, { status, headers: NO_STORE });
const feil = (status, melding) => json({ ok: false, feil: melding }, status);

export function likTid(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let r = 0; for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

async function sha256(s) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, '0')).join('');
}

// Gyldig sidesti: relativ, bare [a-z0-9._-/], slutter på .html, ingen «..», ikke admin/ eller functions/.
export function gyldigSide(p) {
  if (typeof p !== 'string' || p.length > 200) return false;
  if (!/^[a-z0-9][a-z0-9._\-/]*\.html$/i.test(p)) return false;
  if (p.includes('..') || p.includes('//') || p.includes('/.')) return false;
  if (/^(admin|functions|node_modules)\//i.test(p)) return false;
  return true;
}

// Trygt filnavn for opplastede bilder: små bokstaver, æøå -> ae/o/a, bare [a-z0-9-], fast endelse.
export function trygtNavn(navn, ext) {
  const base = String(navn || 'bilde').replace(/\.[a-z0-9]+$/i, '').toLowerCase()
    .replace(/æ/g, 'ae').replace(/ø/g, 'o').replace(/å/g, 'a')
    .normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'bilde';
  return base + '.' + ext;
}

// Bildetype ut fra «magiske bytes» (SVG er bevisst ikke tillatt – kan inneholde skript).
export function bildeType(b) {
  if (b.length > 8 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return 'png';
  if (b.length > 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'jpg';
  if (b.length > 12 && b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50) return 'webp';
  if (b.length > 6 && b[0] === 0x47 && b[1] === 0x49 && b[2] === 0x46) return 'gif';
  if (b.length > 12 && String.fromCharCode(...b.slice(4, 12)) === 'ftypavif') return 'avif';
  return null;
}

function b64TilBytes(s) {
  const bin = atob(String(s).replace(/^data:[^,]*,/, '').replace(/\s+/g, ''));
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}
function bytesTilB64(u) {
  let s = '';
  for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
  return btoa(s);
}
const tekstTilB64 = t => bytesTilB64(new TextEncoder().encode(t));
const b64TilTekst = s => new TextDecoder().decode(b64TilBytes(s));

function gh(env) {
  const repo = env.GITHUB_REPO || 'SebastianKristo/pult-forsterker';
  const branch = env.GITHUB_BRANCH || 'main';
  const base = 'https://api.github.com/repos/' + repo;
  const headers = {
    Authorization: 'Bearer ' + env.GITHUB_TOKEN,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'skjold-nettside-admin',
  };
  const kall = async (sti, init = {}) => {
    const r = await fetch(base + sti, { ...init, headers: { ...headers, ...(init.body ? { 'Content-Type': 'application/json' } : {}) } });
    let data = null; try { data = await r.json(); } catch {}
    return { status: r.status, ok: r.ok, data };
  };
  const forfatter = { name: env.GIT_AUTHOR_NAME || 'Sebastian Kristo Jemtland', email: env.GIT_AUTHOR_EMAIL || 'sebastian@kristo.no' };
  const enc = p => p.split('/').map(encodeURIComponent).join('/');
  return {
    hent: p => kall('/contents/' + enc(ROT + p) + '?ref=' + encodeURIComponent(branch)),
    tre: () => kall('/git/trees/' + encodeURIComponent(branch + ':' + ROT.replace(/\/$/, '')) + '?recursive=1'),
    skriv: (p, b64, message, sha) => kall('/contents/' + enc(ROT + p), {
      method: 'PUT',
      body: JSON.stringify({ message, content: b64, branch, author: forfatter, committer: forfatter, ...(sha ? { sha } : {}) }),
    }),
  };
}

async function lesJson(request, maks) {
  const lengde = +(request.headers.get('content-length') || 0);
  if (lengde > maks) throw 413;
  const t = await request.text();
  if (t.length > maks) throw 413;
  let b; try { b = JSON.parse(t); } catch { throw 400; }
  if (b && typeof b === 'object' && !Array.isArray(b)) return b;
  throw 400;
}

const melding = (m, standard) => String(m || standard).replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, 200) || standard;

function ghFeil(r) {
  if (r.status === 409 || r.status === 422) return feil(409, 'Filen er endret av noen andre (eller finnes allerede). Last siden på nytt.');
  if (r.status === 401 || r.status === 403) return feil(502, 'GitHub avviste tokenet (sjekk GITHUB_TOKEN).');
  if (r.status === 404) return feil(404, 'Fant ikke filen på GitHub.');
  return feil(502, 'GitHub svarte ' + r.status + '.');
}

export async function onRequest({ request, env, params }) {
  const url = new URL(request.url);
  const sti = Array.isArray(params?.path) ? params.path.join('/') : url.pathname.replace(/^\/api\/admin\/?/, '');
  const metode = request.method;

  if (metode !== 'GET' && metode !== 'POST') return new Response('method not allowed', { status: 405, headers: { Allow: 'GET, POST', ...NO_STORE } });
  if (metode === 'POST') {
    const origin = request.headers.get('origin');
    if (origin && origin !== url.origin) return feil(403, 'Feil opphav.');
  }
  if (!env.ADMIN_NOKKEL) return feil(503, 'ADMIN_NOKKEL er ikke satt.');

  // Rate-limit på feilede forsøk (grovt, KV er «eventually consistent»).
  const kv = env.INTERESSE;
  const ip = request.headers.get('cf-connecting-ip') || 'ukjent';
  const rlKey = 'arl:' + (await sha256(ip + ':' + env.ADMIN_NOKKEL)).slice(0, 32);
  const teller = kv ? (parseInt((await kv.get(rlKey)) || '0', 10) || 0) : 0;
  if (teller >= GRENSE) return feil(429, 'For mange feil forsøk. Vent 15 minutter.');
  const auth = request.headers.get('authorization') || '';
  const nokkel = auth.startsWith('Bearer ') ? auth.slice(7).trim() : '';
  if (!likTid(nokkel, env.ADMIN_NOKKEL)) {
    if (kv) await kv.put(rlKey, String(teller + 1), { expirationTtl: VINDU_S });
    return feil(401, 'Feil nøkkel.');
  }

  if (metode === 'GET' && sti === 'ping') return json({ ok: true, github: !!env.GITHUB_TOKEN });
  if (!env.GITHUB_TOKEN) return feil(503, 'GITHUB_TOKEN er ikke satt i Cloudflare.');
  const g = gh(env);

  try {
    if (metode === 'GET' && sti === 'pages') {
      const r = await g.tre();
      if (!r.ok) return ghFeil(r);
      const pages = (r.data.tree || []).filter(t => t.type === 'blob' && gyldigSide(t.path)).map(t => t.path).sort();
      return json({ pages, truncated: !!r.data.truncated });
    }

    if (metode === 'GET' && sti === 'page') {
      const p = url.searchParams.get('path') || '';
      if (!gyldigSide(p)) return feil(400, 'Ugyldig sti.');
      const r = await g.hent(p);
      if (!r.ok) return ghFeil(r);
      if (Array.isArray(r.data) || r.data.type !== 'file') return feil(400, 'Ikke en fil.');
      return json({ path: p, html: b64TilTekst(r.data.content || ''), sha: r.data.sha });
    }

    if (metode === 'POST' && sti === 'page') {
      const b = await lesJson(request, MAKS_HTML * 2);
      if (!gyldigSide(b.path)) return feil(400, 'Ugyldig sti.');
      if (typeof b.html !== 'string' || !b.html.trim() || b.html.length > MAKS_HTML) return feil(400, 'Mangler eller for stor HTML.');
      let sha = typeof b.sha === 'string' && /^[0-9a-f]{40}$/.test(b.sha) ? b.sha : null;
      if (!sha) { const h = await g.hent(b.path); if (h.ok) sha = h.data.sha; }
      const r = await g.skriv(b.path, tekstTilB64(b.html), melding(b.message, 'Nettside: oppdater ' + b.path + ' (admin)'), sha);
      if (!r.ok) return ghFeil(r);
      return json({ ok: true, sha: r.data?.content?.sha, commit: r.data?.commit?.sha });
    }

    if (metode === 'POST' && sti === 'upload') {
      const b = await lesJson(request, Math.ceil(MAKS_BILDE * 1.4) + 4096);
      let bytes; try { bytes = b64TilBytes(b.base64 || ''); } catch { return feil(400, 'Ugyldig base64.'); }
      if (!bytes.length || bytes.length > MAKS_BILDE) return feil(413, 'Bildet må være mindre enn 5 MB.');
      const ext = bildeType(bytes);
      if (!ext) return feil(415, 'Bare PNG, JPG, WebP, GIF eller AVIF.');
      // Unngå å overskrive: legg på et kort tidsstempel.
      const navn = trygtNavn(b.name, ext).replace(/\.(\w+)$/, '-' + Date.now().toString(36) + '.$1');
      const p = BILDE_MAPPE + navn;
      const r = await g.skriv(p, bytesTilB64(bytes), 'Nettside: last opp bilde ' + navn + ' (admin)');
      if (!r.ok) return ghFeil(r);
      return json({ ok: true, path: '/' + p });
    }

    if (metode === 'POST' && sti === 'new') {
      const b = await lesJson(request, 4096);
      if (!gyldigSide(b.from) || !gyldigSide(b.to)) return feil(400, 'Ugyldig sti.');
      const fra = await g.hent(b.from);
      if (!fra.ok) return ghFeil(fra);
      const finnes = await g.hent(b.to);
      if (finnes.ok) return feil(409, 'Siden finnes allerede.');
      const r = await g.skriv(b.to, String(fra.data.content || '').replace(/\s+/g, ''), melding(b.message, 'Nettside: ny side ' + b.to + ' (kopi av ' + b.from + ', admin)'));
      if (!r.ok) return ghFeil(r);
      return json({ ok: true, path: b.to, sha: r.data?.content?.sha });
    }
  } catch (e) {
    if (e === 413) return feil(413, 'For stor forespørsel.');
    if (e === 400) return feil(400, 'Ugyldig JSON.');
    return feil(500, 'Intern feil.');
  }
  return feil(404, 'Ukjent endepunkt.');
}
