/* Skjold Flasher – GUI. Gjenskapt etter design/flasher/Skjold Flasher.dc.html. Ingen moduler: ett skript. */

type Media = 'sd' | 'usb';
interface DriveInfo { device: string; name: string; path: string; size: number; mountpoints: string[]; media: Media; readOnly: boolean }
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
const STEPS = ['Velg lagring', 'Forhåndsinnstill', 'Skriv og verifiser', 'Ferdig'];

const S = {
  p: 0,
  dev: 0,
  drive: '' as string,
  media: 'sd' as Media,
  drives: [] as DriveInfo[],
  imgMode: 'latest' as 'latest' | 'local',
  release: null as ReleaseImage | null,
  releaseState: 'loading' as 'loading' | 'ok' | 'none' | 'error',
  local: null as LocalImage | null,
  net: 'wifi' as 'wifi' | 'eth', stat: false, ip: '', gw: '', dns: '',
  pre: true, ssid: '', pw: '', name: 'Stue', lang: 0, country: 'NO',
  hostname: 'skjold-stue', hostEdited: false,
  ssh: false, user: 'skjold', userPw: '', sshKey: '', lms: false,
  progress: null as Progress | null,
  result: null as FlashResult | null,
};

const $ = (id: string) => document.getElementById(id)!;
const esc = (s: string) => s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
const gb = (n: number) => (n / 1e9).toLocaleString('nb-NO', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' GB';
const mb = (n: number) => Math.round(n / 1e6).toLocaleString('nb-NO');

function ipv4(s: string) { const p = s.trim().split('.'); return p.length === 4 && p.every(x => /^(0|[1-9]\d{0,2})$/.test(x) && Number(x) <= 255); }
function cidrOk(s: string) {
  const m = /^\s*([0-9.]+)(?:\/(\d{1,2}))?\s*$/.exec(s);
  if (!m || !ipv4(m[1])) return false;
  const pre = m[2] === undefined ? 24 : Number(m[2]), first = Number(m[1].split('.')[0]);
  return pre >= 1 && pre <= 32 && first !== 0 && first !== 127 && first < 224;
}
const gwOk = () => !S.gw.trim() || ipv4(S.gw);
const dnsOk = () => S.dns.split(/[\s,;]+/).filter(Boolean).every(ipv4);
const staticOk = () => cidrOk(S.ip) && gwOk() && dnsOk();
const isUsb = () => S.media === 'usb';
const shownDrives = () => S.drives.filter(d => d.media === S.media);
const WP_HINT: Record<Media, string> = {
  sd: 'Låsen på siden av kortet står på «Lock». Ta ut kortet, skyv låsen opp og sett det inn igjen.',
  usb: 'Pinnen har en skrivebeskyttelse-bryter. Slå den av, eller velg en annen disk.',
};
const USB_HINT: Record<string, string> = {
  's1': 'Raspberry Pi 4 starter fra USB når det ikke står noe SD-kort i. Pi-er kjøpt før 2020 trenger en nyere bootloader: start én gang fra et Skjold-SD-kort, så oppdateres den automatisk.',
  'node-pi4': 'Pi 4 starter fra USB når det ikke står noe SD-kort i. Pi-er kjøpt før 2020 trenger én oppstart fra et Skjold-SD-kort først, så oppdateres bootloaderen.',
  'node-pi3': 'Pi 3B må først starte én gang fra et Skjold-SD-kort. Da slås USB-oppstart på permanent. Pi 3B+ starter fra USB uten dette.',
  'core': 'Pi 4 starter fra USB når det ikke står noe SD-kort i (Pi-er kjøpt før 2020 trenger én oppstart fra et Skjold-SD-kort først). Pi 3B må først starte én gang fra et Skjold-SD-kort. Da slås USB-oppstart på permanent. Pi 3B+ starter fra USB uten dette.',
};
const IC: Record<Media, string> = { sd: 'M7 3h7l4 4v14H7zM10 3v3M12.5 3v3', usb: 'M8 9h8v12H8zM9.5 3h5v6h-5zM11 5.5h.01M13 5.5h.01' };
const LOCK = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 11h12v9H6zM8.5 11V8a3.5 3.5 0 0 1 7 0v3"></path></svg>';
const NETS: ['wifi' | 'eth', string, string, string][] = [
  ['wifi', 'Wi-Fi', 'Trådløst', 'M2 8.5a15 15 0 0 1 20 0M5.5 12a10 10 0 0 1 13 0M9 15.5a5 5 0 0 1 6 0M12 19h.01'],
  ['eth', 'Ethernet', 'Kabel · mest stabilt', 'M4 5h16v10H4zM8 15v4h8v-4M8 9v2M11 9v2M14 9v2M17 9v2'],
];

function hostOk(h: string) { return /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/.test(h); }
function imageReady() { return S.imgMode === 'latest' ? !!S.release : !!S.local; }
function canNext(): boolean {
  if (S.p === 0) return imageReady() && shownDrives().some(d => d.device === S.drive && !d.readOnly);
  if (S.p === 1) {
    if (!hostOk(S.hostname)) return false;
    if (S.pre && !(S.name.trim() && /^[A-Z]{2}$/.test(S.country))) return false;
    if (S.pre && S.net === 'wifi' && !(S.ssid.trim() && S.pw.length >= 8 && S.pw.length <= 63)) return false;
    if (S.pre && S.net === 'eth' && S.stat && !staticOk()) return false;
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
  next.textContent = err ? 'Prøv igjen' : ['Neste', isUsb() ? 'Skriv til USB-disken' : 'Skriv til kortet', 'Skriver …', isUsb() ? 'Flash en disk til' : 'Flash et kort til'][S.p];
  next.disabled = !canNext();
}

function page0(): string {
  const rel = S.release ? `${esc(S.release.tag)} · ${gb(S.release.size)}`
    : { loading: 'Henter bildeliste …', none: 'Ingen bilde funnet', error: 'Fikk ikke kontakt med GitHub / raspberrypi.com', ok: '' }[S.releaseState];
  const list = shownDrives();
  const drives = list.length
    ? list.map(d => `<button class="card drive ${S.drive === d.device && !d.readOnly ? 'sel' : ''} ${d.readOnly ? 'wp' : ''}" data-drive="${esc(d.device)}" ${d.readOnly ? 'aria-disabled="true"' : ''}>
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="${IC[d.media]}"></path></svg>
        <div style="display:flex;flex-direction:column;gap:3px;min-width:0"><span class="t">${esc(d.name)}${d.readOnly ? `<span class="badge">${LOCK}Skrivebeskyttet</span>` : ''}</span><span class="s">${esc(d.path)}</span>
        ${d.readOnly ? `<span class="wphint">${WP_HINT[d.media]}</span>` : ''}</div>
        <span class="size">${gb(d.size)}</span></button>`).join('')
    : `<div class="empty">Fant ingen ${isUsb() ? 'USB-disk' : 'SD-kort'}. Sett den inn, så dukker den opp her.</div>`;
  return `<h1>Velg lagring</h1>
    <p class="lead">Bare flyttbare disker vises. Alt på disken blir slettet.</p>
    <div class="group"><span class="label">Bilde</span><div class="grid">
      <button class="card ${S.imgMode === 'latest' ? 'sel' : ''}" data-img="latest"><span class="t">${S.release?.base ? 'Raspberry Pi OS Lite 64-bit + Skjold' : 'Siste Skjold-bilde'}</span><span class="s">${rel}</span></button>
      <button class="card ${S.imgMode === 'local' ? 'sel' : ''}" data-img="local"><span class="t">Velg fil …</span><span class="s">${S.local ? esc(S.local.name) : '.img, .img.xz eller .zip'}</span></button>
    </div></div>
    <div class="group"><span class="label">Start fra</span>
      <div class="seg">${(['sd', 'usb'] as Media[]).map(k => `<button class="${S.media === k ? 'on' : ''}" data-media="${k}">${k === 'sd' ? 'SD-kort' : 'USB-pinne eller SSD'}</button>`).join('')}</div>
      ${isUsb() ? `<div class="infobox"><span class="h">Start fra USB</span><span>${USB_HINT[DEVS[S.dev][0]]}</span>
        <span class="m">Ta ut SD-kortet, ellers starter Pi-en fra det først. En USB-SSD er raskere og tåler mer skriving enn et SD-kort.</span></div>` : ''}
    </div>
    <div class="group"><span class="label">Enhet</span><div class="grid">
      ${DEVS.map(([, n, s], i) => `<button class="card ${S.dev === i ? 'sel' : ''}" data-dev="${i}"><span class="t">${n}</span><span class="s">${s}</span></button>`).join('')}
    </div></div>
    <div class="group">${drives}</div>`;
}

const field = (k: string, label: string, val: string, extra = '', bad = false) =>
  `<label class="f ${extra.includes('wide') ? 'wide' : ''}"><span class="label">${label}</span><input class="inp ${bad ? 'bad' : ''}" data-k="${k}" value="${esc(val)}" ${extra.replace('wide', '')}></label>`;

function page1(): string {
  return `<h1>Forhåndsinnstill</h1>
    <p class="lead">Valgfritt. Fyller du inn dette, kobler forsterkeren seg rett til nettverket ved første oppstart, og oppsettet på telefonen hoppes over.</p>
    <div class="toggle-row"><span>Forhåndsinnstill nettverk og navn</span><button class="toggle ${S.pre ? 'on' : ''}" data-toggle="pre" aria-label="Forhåndsinnstill"><i></i></button></div>
    ${S.pre ? `<div class="group"><span class="label">Nettverk</span><div class="nets">
      ${NETS.map(([k, l, sub, ic]) => `<button class="card net ${S.net === k ? 'sel' : ''}" data-net="${k}"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c9c9c4" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="${ic}"></path></svg><span style="display:flex;flex-direction:column;gap:2px"><span class="t">${l}</span><span class="s">${sub}</span></span></button>`).join('')}
    </div></div>
    ${S.net === 'eth' ? `<div class="toggle-row"><span>Fast IP-adresse<br><small>Av: ruteren deler ut adresse automatisk (DHCP)</small></span><button class="toggle ${S.stat ? 'on' : ''}" data-toggle="stat" aria-label="Fast IP"><i></i></button></div>
    ${S.stat ? `<div class="grid ipf">
      ${field('ip', 'IP-adresse', S.ip, 'placeholder="192.168.1.50/24" spellcheck="false"', !!S.ip && !cidrOk(S.ip))}
      ${field('gw', 'Ruter', S.gw, 'placeholder="192.168.1.1" spellcheck="false"', !gwOk())}
      ${field('dns', 'DNS', S.dns, 'placeholder="1.1.1.1" spellcheck="false"', !dnsOk())}
    </div>` : ''}` : ''}
    <div class="grid form">
      ${S.net === 'wifi' ? `${field('ssid', 'Wi-Fi-navn', S.ssid, 'autocomplete="off" spellcheck="false"')}
      ${field('pw', 'Passord', S.pw, 'type="password" placeholder="Minst 8 tegn"')}` : ''}
      ${field('name', 'Navn / rom', S.name)}
      <div class="f" style="display:flex;flex-direction:column;gap:6px"><span class="label">Språk</span><div class="langs">
        ${LANGS.map(([, l], i) => `<button class="card ${S.lang === i ? 'sel' : ''}" data-lang="${i}">${l}</button>`).join('')}
      </div></div>
      ${S.net === 'eth' ? '' : field('country', 'Wi-Fi-land', S.country, 'maxlength="2" style="text-transform:uppercase"')}
      ${field('hostname', 'Vertsnavn', S.hostname, 'spellcheck="false"')}
    </div>` : `<div class="grid form">${field('hostname', 'Vertsnavn', S.hostname, 'spellcheck="false"')}</div>`}
    <div class="toggle-row"><span>Installer Lyrion-server på denne enheten<br><small style="opacity:.7">Av: kobler seg til en Lyrion-server du allerede har.</small></span><button class="toggle ${S.lms ? 'on' : ''}" data-toggle="lms" aria-label="Lyrion-server"><i></i></button></div>
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
  flashing: 'Skriver til lagringen', verifying: 'Verifiserer', done: 'Ferdig', error: 'Noe gikk galt',
};

function page2(): string {
  const pr = S.progress ?? { phase: 'download' as Phase, percent: 0 };
  if (pr.phase === 'error') return `<h1>Noe gikk galt</h1><div class="err">${esc(pr.message ?? 'Ukjent feil')}</div>
    <p class="lead">${isUsb() ? 'Disken kan være delvis skrevet. Prøv igjen, eller velg en annen disk.' : 'Kortet kan være delvis skrevet. Prøv igjen, eller velg et annet kort.'}</p>`;
  const sub = {
    download: (S.release?.base ? 'Henter Raspberry Pi OS Lite fra raspberrypi.com' : 'Henter fra GitHub Releases') + (S.release?.sha256 ? ' og kontrollerer SHA-256.' : '.'),
    decompress: 'Gjør bildet klart på datamaskinen før skriving.',
    configure: S.pre ? 'Nettverk og navn legges i skjold-setup.json.' : 'Navn og innstillinger legges på boot-partisjonen.',
    authorize: `Datamaskinen ber om administratorpassord for å skrive til ${isUsb() ? 'disken' : 'kortet'}.`,
    flashing: (isUsb() ? 'Ikke ta ut disken. ' : 'Ikke ta ut kortet. ') + (S.pre ? 'Nettverk og navn ligger i skjold-setup.json.' : ''),
    verifying: 'Leser tilbake og sammenligner med bildet.',
    done: '', error: '',
  }[pr.phase];
  const indet = pr.phase === 'authorize' || pr.phase === 'configure';
  const left = pr.bytes && pr.total && (pr.phase === 'flashing' || pr.phase === 'download')
    ? `${mb(pr.bytes)} / ${mb(pr.total)} MB` : `${Math.round(pr.percent)} %`;
  const right = pr.eta && pr.eta > 0 ? `ca. ${Math.max(1, Math.round(pr.eta))} s igjen` : pr.speed ? `${(pr.speed / 1e6).toFixed(1)} MB/s` : '';
  const title = pr.phase === 'flashing' ? (isUsb() ? 'Skriver til USB-disken' : 'Skriver til SD-kortet') : PHASE_TITLE[pr.phase];
  return `<h1>${title}</h1><p class="lead">${esc(sub)}</p>
    <div class="progress"><div class="track ${indet ? 'indet' : ''}"><div style="width:${Math.min(100, pr.percent)}%"></div></div>
    <div class="meta"><span>${left}</span><span>${right}</span></div></div>`;
}

function page3(): string {
  const r = S.result!;
  const inst = r.install ? `<li>Første oppstart installerer Skjold fra nettet. Det tar 15–30 minutter, og Pi-en starter på nytt av seg selv${S.pre ? '' : ' (krever nettverkskabel når Wi-Fi ikke er forhåndsinnstilt)'}.</li>` : '';
  const eth = S.pre && S.net === 'eth';
  const where = eth ? 'nettverket via kabel' + (S.stat && cidrOk(S.ip) ? ' på ' + S.ip.trim().split('/')[0] : '') : S.ssid;
  const hint = S.pre ? `«${esc(S.name)}» kobler seg til ${esc(where)} av seg selv. Skjermen viser IP-adressen når den er klar.`
    : 'Skjermen viser en QR-kode. Skann den med telefonen for å sette opp Wi-Fi og navn.';
  const hintCore = DEVS[S.dev][0] === 'core' && !S.pre ? 'Core har ingen skjerm: koble Pi-en til ruteren med nettverkskabel, eller flash på nytt med Wi-Fi forhåndsinnstilt.' : null;
  const core = DEVS[S.dev][0] === 'core';
  const step1 = isUsb()
    ? (DEVS[S.dev][0] === 'node-pi3' ? 'Ta ut SD-kortet fra Raspberry Pi-en hvis det står et der, og koble USB-disken til en USB-port.' : 'Ta ut SD-kortet fra Raspberry Pi-en hvis det står et der, og koble USB-disken til en blå USB 3-port.') + (core ? ' Koble til høyttalere eller en forsterker.' : '')
    : core ? 'Ta ut kortet, sett det i Raspberry Pi-en og koble til høyttalere eller en forsterker.' : `Ta ut kortet og sett det i Raspberry Pi-en i ${S.dev === 0 ? 'forsterkeren' : 'Node-en'}.`;
  return `<div class="check">✓</div><h1>${isUsb() ? 'USB-disken er klar' : 'SD-kortet er klart'}</h1>
    <div class="done"><ol>
      <li>${step1}</li>
      ${eth ? '<li>Koble en nettverkskabel fra ruteren til Ethernet-porten.</li>' : ''}
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

function autoPick() {
  const shown = shownDrives();
  if (S.drive && !shown.some(d => d.device === S.drive && !d.readOnly)) S.drive = '';
  const ok = shown.filter(d => !d.readOnly);
  if (!S.drive && ok.length === 1) S.drive = ok[0].device;
}

async function refreshDrives() {
  try {
    const list = await skjold.listDrives();
    const same = JSON.stringify(list) === JSON.stringify(S.drives);
    S.drives = list;
    autoPick();
    if (!same && S.p === 0) render(); else renderFooter();
  } catch { /* prøver igjen */ }
}

async function startFlash() {
  S.p = 2; S.progress = { phase: S.imgMode === 'latest' ? 'download' : 'decompress', percent: 0 }; S.result = null; render();
  const [lang, , ] = LANGS[S.lang];
  const req = {
    image: S.imgMode === 'latest' ? { kind: 'latest', release: S.release } : { kind: 'local', path: S.local!.path },
    drive: S.drive,
    setup: { device: DEVS[S.dev][0], preset: S.pre, net: S.net, media: S.media,
      staticIp: S.net === 'eth' && S.stat ? { ip: S.ip.trim(), gw: S.gw.trim(), dns: S.dns.trim() } : null, ssid: S.ssid, wifiPassword: S.pw, country: S.country, name: S.name.trim(),
      hostname: S.hostname, lang, ssh: S.ssh, user: S.user, userPassword: S.userPw, sshKey: S.sshKey.trim(), lyrionServer: S.lms },
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
    const t = (e.target as HTMLElement).closest<HTMLElement>('[data-drive],[data-dev],[data-img],[data-lang],[data-toggle],[data-open],[data-media],[data-net]');
    if (!t) return;
    const d = t.dataset;
    if (d.drive !== undefined) { if (S.drives.some(x => x.device === d.drive && x.readOnly)) return; S.drive = d.drive; }
    else if (d.media !== undefined) { S.media = d.media as Media; S.drive = ''; autoPick(); }
    else if (d.net !== undefined) S.net = d.net as 'wifi' | 'eth';
    else if (d.toggle === 'stat') S.stat = !S.stat;
    else if (d.dev !== undefined) S.dev = Number(d.dev);
    else if (d.lang !== undefined) { S.lang = Number(d.lang); S.country = LANGS[S.lang][2]; }
    else if (d.toggle === 'pre') S.pre = !S.pre;
    else if (d.toggle === 'lms') S.lms = !S.lms;
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
    if (k === 'ip') el.classList.toggle('bad', !!S.ip && !cidrOk(S.ip));
    else if (k === 'gw') el.classList.toggle('bad', !gwOk());
    else if (k === 'dns') el.classList.toggle('bad', !dnsOk());
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
