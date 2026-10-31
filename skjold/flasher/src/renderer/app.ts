/* Skjold Flasher – GUI. Gjenskapt etter design/flasher/Skjold Flasher.dc.html. Ingen moduler: ett skript. */

interface DriveInfo { device: string; name: string; path: string; size: number; mountpoints: string[] }
interface ReleaseImage { tag: string; name: string; url: string; size: number; sha256?: string; publishedAt: string; base?: boolean }
interface LocalImage { path: string; name: string; size: number }
type Phase = 'download' | 'decompress' | 'configure' | 'authorize' | 'flashing' | 'verifying' | 'done' | 'error';
interface Progress { phase: Phase; percent: number; bytes?: number; total?: number; speed?: number; eta?: number; message?: string }
interface FlashResult { ok: boolean; error?: string; url?: string; qr?: string; install?: boolean }
interface SkjoldApi {
  listDrives(): Promise<DriveInfo[]>;
  latestImage(): Promise<ReleaseImage | null>;
  pickImage(): Promise<LocalImage | null>;
  flash(req: unknown): Promise<FlashResult>;
  cancel(): Promise<void>;
  hostname(name: string): Promise<string>;
  open(url: string): Promise<void>;
  version(): Promise<string>;
  platform: string;
  onProgress(cb: (p: Progress) => void): () => void;
}
declare const skjold: SkjoldApi;

const LANGS: [string, string, string][] = [['nb', 'Norsk', 'NO'], ['en', 'English', 'GB'], ['sv', 'Svenska', 'SE'], ['da', 'Dansk', 'DK']];
const DEVS: [string, string, string][] = [
  ['s1', 'Skjold S1', 'Forsterker · Raspberry Pi 4'],
  ['node-pi4', 'Skjold Node · Pi 4', 'Bare lydutgang · 3,5 mm, HDMI, USB eller I²S'],
  ['node-pi3', 'Skjold Node · Pi 3B', 'Bare lydutgang · 3,5 mm, HDMI, USB eller I²S'],
  ['core', 'Skjold Core', 'Ren Raspberry Pi 4/3B · ingen kasse, knapper eller skjerm'],
];
const STEPS = ['Velg SD-kort', 'Forhåndsinnstill', 'Skriv og verifiser', 'Ferdig'];

const S = {
  p: 0,
  dev: 0,
  drive: '' as string,
  drives: [] as DriveInfo[],
  imgMode: 'latest' as 'latest' | 'local',
  release: null as ReleaseImage | null,
  releaseState: 'loading' as 'loading' | 'ok' | 'none' | 'error',
  local: null as LocalImage | null,
  pre: true, ssid: '', pw: '', name: 'Stue', lang: 0, country: 'NO',
  hostname: 'skjold-stue', hostEdited: false,
  ssh: false, user: 'skjold', userPw: '', sshKey: '',
  progress: null as Progress | null,
  result: null as FlashResult | null,
};

const $ = (id: string) => document.getElementById(id)!;
const esc = (s: string) => s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
const gb = (n: number) => (n / 1e9).toLocaleString('nb-NO', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' GB';
const mb = (n: number) => Math.round(n / 1e6).toLocaleString('nb-NO');

function hostOk(h: string) { return /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/.test(h); }
function imageReady() { return S.imgMode === 'latest' ? !!S.release : !!S.local; }
function canNext(): boolean {
  if (S.p === 0) return imageReady() && !!S.drive && S.drives.some(d => d.device === S.drive);
  if (S.p === 1) {
    if (!hostOk(S.hostname)) return false;
    if (S.pre && !(S.ssid.trim() && S.pw.length >= 8 && S.pw.length <= 63 && S.name.trim() && /^[A-Z]{2}$/.test(S.country))) return false;
    if (S.ssh && !(/^[a-z_][a-z0-9_-]{0,31}$/.test(S.user) && S.user !== 'root' && ((S.userPw.length >= 6) || (!S.userPw && S.sshKey.trim())))) return false;
    return true;
  }
  return S.p === 3 || (S.p === 2 && S.progress?.phase === 'error');
}

function renderSide() {
  $('steps').innerHTML = STEPS.map((label, i) =>
    `<div class="step ${i === S.p ? 'cur' : i < S.p ? 'past' : ''}"><div class="ring">${i < S.p ? '✓' : i + 1}</div><span>${label}</span></div>`).join('');
  let a = '', b = '';
  if (S.imgMode === 'latest') {
    if (S.release) { a = S.release.name; b = `${gb(S.release.size)} · ${S.release.sha256 ? 'SHA-256 sjekkes' : S.release.tag}`; }
    else if (S.releaseState === 'loading') a = 'Ser etter siste bilde …';
  } else if (S.local) { a = S.local.name; b = `${gb(S.local.size)} · lokal fil`; }
  $('imginfo').innerHTML = `<span>${esc(a)}</span><span>${esc(b)}</span>`;
}

function renderFooter() {
  const back = $('back') as HTMLButtonElement, next = $('next') as HTMLButtonElement;
  back.hidden = S.p !== 1;
  const err = S.p === 2 && S.progress?.phase === 'error';
  next.textContent = err ? 'Prøv igjen' : ['Neste', 'Skriv til kortet', 'Skriver …', 'Flash et kort til'][S.p];
  next.disabled = !canNext();
}

function page0(): string {
  const rel = S.release ? `${esc(S.release.tag)} · ${gb(S.release.size)}`
    : { loading: 'Henter bildeliste …', none: 'Ingen bilde funnet', error: 'Fikk ikke kontakt med GitHub / raspberrypi.com', ok: '' }[S.releaseState];
  const drives = S.drives.length
    ? S.drives.map(d => `<button class="card drive ${S.drive === d.device ? 'sel' : ''}" data-drive="${esc(d.device)}">
        <div class="sd"></div><div style="display:flex;flex-direction:column;gap:3px;min-width:0"><span class="t">${esc(d.name)}</span><span class="s">${esc(d.path)}</span></div>
        <span class="size">${gb(d.size)}</span></button>`).join('')
    : '<div class="empty">Sett inn et SD-kort. Bare flyttbare disker vises.</div>';
  return `<h1>Velg SD-kort</h1>
    <p class="lead">Bare flyttbare disker vises. Alt på kortet blir slettet.</p>
    <div class="group"><span class="label">Bilde</span><div class="grid">
      <button class="card ${S.imgMode === 'latest' ? 'sel' : ''}" data-img="latest"><span class="t">${S.release?.base ? 'Raspberry Pi OS Lite 64-bit + Skjold' : 'Siste Skjold-bilde'}</span><span class="s">${rel}</span></button>
      <button class="card ${S.imgMode === 'local' ? 'sel' : ''}" data-img="local"><span class="t">Velg fil …</span><span class="s">${S.local ? esc(S.local.name) : '.img, .img.xz eller .zip'}</span></button>
    </div></div>
    <div class="group"><span class="label">Enhet</span><div class="grid">
      ${DEVS.map(([, n, s], i) => `<button class="card ${S.dev === i ? 'sel' : ''}" data-dev="${i}"><span class="t">${n}</span><span class="s">${s}</span></button>`).join('')}
    </div></div>
    <div class="group"><span class="label">SD-kort</span>${drives}</div>`;
}

const field = (k: string, label: string, val: string, extra = '') =>
  `<label class="f ${extra.includes('wide') ? 'wide' : ''}"><span class="label">${label}</span><input class="inp" data-k="${k}" value="${esc(val)}" ${extra.replace('wide', '')}></label>`;

function page1(): string {
  return `<h1>Forhåndsinnstill</h1>
    <p class="lead">Valgfritt. Fyller du inn dette, kobler forsterkeren seg rett til Wi-Fi ved første oppstart, og oppsettet på telefonen hoppes over.</p>
    <div class="toggle-row"><span>Forhåndsinnstill Wi-Fi og navn</span><button class="toggle ${S.pre ? 'on' : ''}" data-toggle="pre" aria-label="Forhåndsinnstill"><i></i></button></div>
    ${S.pre ? `<div class="grid form">
      ${field('ssid', 'Wi-Fi-navn', S.ssid, 'autocomplete="off" spellcheck="false"')}
      ${field('pw', 'Passord', S.pw, 'type="password" placeholder="Minst 8 tegn"')}
      ${field('name', 'Navn / rom', S.name)}
      <div class="f" style="display:flex;flex-direction:column;gap:6px"><span class="label">Språk</span><div class="langs">
        ${LANGS.map(([, l], i) => `<button class="card ${S.lang === i ? 'sel' : ''}" data-lang="${i}">${l}</button>`).join('')}
      </div></div>
      ${field('country', 'Wi-Fi-land', S.country, 'maxlength="2" style="text-transform:uppercase"')}
      ${field('hostname', 'Vertsnavn', S.hostname, 'spellcheck="false"')}
    </div>` : `<div class="grid form">${field('hostname', 'Vertsnavn', S.hostname, 'spellcheck="false"')}</div>`}
    <div class="toggle-row"><span>Slå på SSH</span><button class="toggle ${S.ssh ? 'on' : ''}" data-toggle="ssh" aria-label="SSH"><i></i></button></div>
    ${S.ssh ? `<div class="grid form">
      ${field('user', 'Brukernavn', S.user, 'spellcheck="false" autocomplete="off"')}
      ${field('userPw', 'Passord', S.userPw, 'type="password" placeholder="Minst 6 tegn, eller bruk nøkkel"')}
      <label class="f wide"><span class="label">Offentlig SSH-nøkkel (valgfritt)</span><textarea class="inp" data-k="sshKey" spellcheck="false" placeholder="ssh-ed25519 AAAA…">${esc(S.sshKey)}</textarea></label>
    </div>` : ''}
    <span class="hint">Nås på http://${esc(S.hostname)}.local:8765/</span>`;
}

const PHASE_TITLE: Record<Phase, string> = {
  download: 'Laster ned bildet', decompress: 'Pakker ut bildet', configure: 'Legger inn oppsett', authorize: 'Venter på tilgang',
  flashing: 'Skriver til SD-kortet', verifying: 'Verifiserer', done: 'Ferdig', error: 'Noe gikk galt',
};

function page2(): string {
  const pr = S.progress ?? { phase: 'download' as Phase, percent: 0 };
  if (pr.phase === 'error') return `<h1>Noe gikk galt</h1><div class="err">${esc(pr.message ?? 'Ukjent feil')}</div>
    <p class="lead">Kortet kan være delvis skrevet. Prøv igjen, eller velg et annet kort.</p>`;
  const sub = {
    download: (S.release?.base ? 'Henter Raspberry Pi OS Lite fra raspberrypi.com' : 'Henter fra GitHub Releases') + (S.release?.sha256 ? ' og kontrollerer SHA-256.' : '.'),
    decompress: 'Gjør bildet klart på datamaskinen før skriving.',
    configure: S.pre ? 'Wi-Fi og navn legges i skjold-setup.json.' : 'Navn og innstillinger legges på boot-partisjonen.',
    authorize: 'Datamaskinen ber om administratorpassord for å skrive til kortet.',
    flashing: 'Ikke ta ut kortet. ' + (S.pre ? 'Wi-Fi og navn ligger i skjold-setup.json.' : ''),
    verifying: 'Leser tilbake og sammenligner med bildet.',
    done: '', error: '',
  }[pr.phase];
  const indet = pr.phase === 'authorize' || pr.phase === 'configure';
  const left = pr.bytes && pr.total && (pr.phase === 'flashing' || pr.phase === 'download')
    ? `${mb(pr.bytes)} / ${mb(pr.total)} MB` : `${Math.round(pr.percent)} %`;
  const right = pr.eta && pr.eta > 0 ? `ca. ${Math.max(1, Math.round(pr.eta))} s igjen` : pr.speed ? `${(pr.speed / 1e6).toFixed(1)} MB/s` : '';
  return `<h1>${PHASE_TITLE[pr.phase]}</h1><p class="lead">${esc(sub)}</p>
    <div class="progress"><div class="track ${indet ? 'indet' : ''}"><div style="width:${Math.min(100, pr.percent)}%"></div></div>
    <div class="meta"><span>${left}</span><span>${right}</span></div></div>`;
}

function page3(): string {
  const r = S.result!;
  const inst = r.install ? `<li>Første oppstart installerer Skjold fra nettet. Det tar 15–30 minutter, og Pi-en starter på nytt av seg selv${S.pre ? '' : ' (krever nettverkskabel når Wi-Fi ikke er forhåndsinnstilt)'}.</li>` : '';
  const hint = S.pre ? `«${esc(S.name)}» kobler seg til ${esc(S.ssid)} av seg selv. Skjermen viser IP-adressen når den er klar.`
    : 'Skjermen viser en QR-kode. Skann den med telefonen for å sette opp Wi-Fi og navn.';
  const hintCore = DEVS[S.dev][0] === 'core' && !S.pre ? 'Core har ingen skjerm: koble Pi-en til ruteren med nettverkskabel, eller flash på nytt med Wi-Fi forhåndsinnstilt.' : null;
  return `<div class="check">✓</div><h1>SD-kortet er klart</h1>
    <div class="done"><ol>
      <li>${DEVS[S.dev][0] === 'core' ? 'Ta ut kortet, sett det i Raspberry Pi-en og koble til høyttalere eller en forsterker.' : `Ta ut kortet og sett det i Raspberry Pi-en i ${S.dev === 0 ? 'forsterkeren' : 'Node-en'}.`}</li>
      <li>${S.dev === 0 ? 'Koble til strøm og slå på hovedbryteren bak.' : 'Koble til strøm.'}</li>
      ${inst}<li>${hintCore ?? hint}</li>
      ${S.pre ? '<li>Skann QR-koden med telefonen når den er klar, for å åpne Skjold.</li>' : ''}
    </ol>
    ${S.pre && r.qr ? `<div class="qr"><img src="${r.qr}" alt="QR-kode"><span>${esc(r.url ?? '')}</span></div>` : ''}</div>
    ${r.url ? `<a data-open="${esc(r.url)}" style="font-size:13px">Åpne ${esc(r.url)}</a>` : ''}`;
}

function render() {
  $('page').innerHTML = [page0, page1, page2, page3][S.p]();
  renderSide();
  renderFooter();
}

async function refreshDrives() {
  try {
    const list = await skjold.listDrives();
    const same = JSON.stringify(list) === JSON.stringify(S.drives);
    S.drives = list;
    if (S.drive && !list.some(d => d.device === S.drive)) S.drive = '';
    if (!S.drive && list.length === 1) S.drive = list[0].device;
    if (!same && S.p === 0) render(); else renderFooter();
  } catch { /* prøver igjen */ }
}

async function startFlash() {
  S.p = 2; S.progress = { phase: S.imgMode === 'latest' ? 'download' : 'decompress', percent: 0 }; S.result = null; render();
  const [lang, , ] = LANGS[S.lang];
  const req = {
    image: S.imgMode === 'latest' ? { kind: 'latest', release: S.release } : { kind: 'local', path: S.local!.path },
    drive: S.drive,
    setup: { device: DEVS[S.dev][0], preset: S.pre, ssid: S.ssid, wifiPassword: S.pw, country: S.country, name: S.name.trim(),
      hostname: S.hostname, lang, ssh: S.ssh, user: S.user, userPassword: S.userPw, sshKey: S.sshKey.trim() },
  };
  const r = await skjold.flash(req);
  S.result = r;
  if (r.ok) { S.p = 3; render(); }
  else { S.progress = { phase: 'error', percent: 0, message: r.error }; render(); }
}

async function setName(v: string) {
  S.name = v;
  if (!S.hostEdited) {
    S.hostname = await skjold.hostname(v);
    const h = document.querySelector<HTMLInputElement>('input[data-k="hostname"]');
    if (h) h.value = S.hostname;
    const hint = document.querySelector('.hint'); if (hint) hint.textContent = `Nås på http://${S.hostname}.local:8765/`;
    renderFooter();
  }
}

function bind() {
  const page = $('page');
  page.addEventListener('click', async e => {
    const t = (e.target as HTMLElement).closest<HTMLElement>('[data-drive],[data-dev],[data-img],[data-lang],[data-toggle],[data-open]');
    if (!t) return;
    const d = t.dataset;
    if (d.drive !== undefined) S.drive = d.drive;
    else if (d.dev !== undefined) S.dev = Number(d.dev);
    else if (d.lang !== undefined) { S.lang = Number(d.lang); S.country = LANGS[S.lang][2]; }
    else if (d.toggle === 'pre') S.pre = !S.pre;
    else if (d.toggle === 'ssh') S.ssh = !S.ssh;
    else if (d.open) { skjold.open(d.open); return; }
    else if (d.img === 'latest') S.imgMode = 'latest';
    else if (d.img === 'local') {
      const f = await skjold.pickImage();
      if (f) { S.local = f; S.imgMode = 'local'; }
    }
    render();
  });
  page.addEventListener('input', e => {
    const el = e.target as HTMLInputElement;
    const k = el.dataset.k;
    if (!k) return;
    if (k === 'name') { setName(el.value); return; }
    if (k === 'country') { S.country = el.value.toUpperCase(); }
    else if (k === 'hostname') { S.hostname = el.value.trim().toLowerCase(); S.hostEdited = true; const hint = document.querySelector('.hint'); if (hint) hint.textContent = `Nås på http://${S.hostname}.local:8765/`; }
    else (S as unknown as Record<string, string>)[k] = el.value;
    renderFooter();
  });
  $('back').addEventListener('click', () => { if (S.p === 1) { S.p = 0; render(); } });
  $('next').addEventListener('click', () => {
    if (!canNext()) return;
    if (S.p === 0) { S.p = 1; render(); }
    else if (S.p === 1) startFlash();
    else if (S.p === 2) { S.p = 1; S.progress = null; render(); }
    else if (S.p === 3) { S.p = 0; S.drive = ''; S.progress = null; S.result = null; render(); refreshDrives(); }
  });
  skjold.onProgress(p => {
    if (S.p !== 2 || p.phase === 'done') return;
    S.progress = p;
    render();
  });
}

async function init() {
  document.body.classList.add(skjold.platform);
  skjold.version().then(v => { $('ver').textContent = 'FLASHER ' + v.replace(/\.0$/, ''); }).catch(() => undefined);
  bind();
  render();
  refreshDrives();
  setInterval(() => { if (S.p === 0) refreshDrives(); }, 2000);
  try {
    S.release = await skjold.latestImage();
    S.releaseState = S.release ? 'ok' : 'none';
    if (!S.release && !S.local) S.imgMode = 'local';
  } catch { S.releaseState = 'error'; }
  if (S.p === 0) render();
}

init();
