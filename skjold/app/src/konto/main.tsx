// Skjold-konto (hjem.skjold-lab.com/konto): som en Google-konto for Skjold – personlig info, sikkerhet med
// totrinnsbekreftelse, hjem og deling, og data og personvern. Innloggingen er Cloudflare Access (e-post-kode eller Google);
// totrinnsbekreftelsen er et ekstra steg med kodeapp (TOTP) og reservekoder. API: /api/hjem/konto (skjold/sky).
import { render } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { qrMatrix } from '../lib/qr';
import './konto.css';

interface Meg { epost: string; valhalla: boolean; eier: boolean; tofa: boolean; tofaOk: boolean }
interface Sted { id: string; navn: string; rolle: 'eier' | 'medlem'; enheter: number; online: number; medlemmer?: string[] }
interface Konto { epost: string; navn: string; opprettet: number; tofa: { aktiv: boolean; reservekoderIgjen: number }; steder: { id: string; navn: string }[]; sync: { del: string; storrelse: number; endret: number }[] }

async function kall<T>(metode: string, sti: string, kropp?: unknown): Promise<T> {
  const r = await fetch(sti, { method: metode, credentials: 'include', headers: kropp ? { 'content-type': 'application/json' } : {}, body: kropp ? JSON.stringify(kropp) : undefined });
  const ct = r.headers.get('content-type') || '';
  if (!ct.includes('json')) throw new Error('Logg inn på Skjold-hjem');
  const j = await r.json();
  if (!r.ok) throw Object.assign(new Error(j.feil || j.melding || j.error || 'HTTP ' + r.status), { status: r.status, data: j });
  return j as T;
}
const qs = new URLSearchParams(location.search);
const dato = (t: number) => (t ? new Date(t * 1000).toLocaleDateString('nb-NO', { day: 'numeric', month: 'long', year: 'numeric' }) : '–');
const S = {
  kort: 'background:var(--kort);border:1px solid var(--kant);border-radius:20px;padding:22px 24px;display:flex;flex-direction:column;gap:12px',
  knapp: 'height:42px;padding:0 18px;border-radius:21px;border:1px solid var(--kant);background:#1b1b1c;cursor:pointer;font-size:14px;font-weight:600',
  gull: 'height:42px;padding:0 20px;border-radius:21px;border:none;background:var(--gull);color:#0b0b0c;cursor:pointer;font-size:14px;font-weight:600',
  felt: 'height:46px;border-radius:12px;border:1px solid var(--kant);background:#101011;padding:0 14px;font-size:15px;width:100%',
  rad: 'display:flex;align-items:center;gap:14px;padding:14px 0;border-top:1px solid #1d1d1f',
  liten: 'font-size:12.5px;color:var(--demp);line-height:1.45'
};
function Logo({ k = 1 }: { k?: number }) {
  return <span style={`display:flex;gap:${3.3 * k}px;align-items:flex-start;height:${28 * k}px`}>{[14.7, 22, 28, 22, 14.7].map((h, i) => <i key={i} style={`width:${4.5 * k}px;height:${h * k}px;border-radius:${2.3 * k}px;background:${i === 2 ? 'var(--gull2)' : 'var(--tekst)'}`} />)}</span>;
}
function Qr({ tekst, px = 190 }: { tekst: string; px?: number }) {
  let m: boolean[][]; try { m = qrMatrix(tekst); } catch { return null; }
  const n = m.length, q = 3, d: string[] = [];
  m.forEach((r, y) => r.forEach((on, x) => { if (on) d.push(`M${x + q} ${y + q}h1v1h-1z`); }));
  return <svg width={px} height={px} viewBox={`0 0 ${n + 2 * q} ${n + 2 * q}`} shape-rendering="crispEdges" style="background:#fff;border-radius:14px;display:block"><path d={d.join('')} fill="#0b0b0c" /></svg>;
}
function Melding({ t }: { t: string }) { return t ? <div style="position:fixed;left:50%;bottom:28px;transform:translateX(-50%);background:#1c1c1e;border:1px solid var(--kant);padding:12px 18px;border-radius:12px;font-size:14px;z-index:20">{t}</div> : null; }
let visMelding: (t: string) => void = () => {};

/** Totrinnsbekreftelse kreves på denne enheten: kode fra kodeappen eller en reservekode. */
function Bekreft({ ferdig }: { ferdig: () => void }) {
  const [kode, setKode] = useState(''), [feil, setFeil] = useState(''), [opptatt, setOpptatt] = useState(false);
  const send = async () => { setOpptatt(true); setFeil(''); try { await kall('POST', '/api/hjem/konto/2fa/bekreft', { kode }); ferdig(); } catch (e) { setFeil((e as Error).message); } setOpptatt(false); };
  return (
    <div class="inn" style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px">
      <div style={S.kort + ';max-width:420px;width:100%;align-items:center;text-align:center;padding:36px 30px'}>
        <Logo k={1.2} />
        <h1 style="margin:10px 0 0;font-size:24px">Bekreft at det er deg</h1>
        <p style={S.liten}>Skriv koden fra kodeappen (Google Authenticator, 1Password, Microsoft Authenticator …), eller en av reservekodene.</p>
        <input value={kode} onInput={(e) => setKode(e.currentTarget.value)} onKeyDown={(e) => { if (e.key === 'Enter') void send(); }} autoFocus inputMode="numeric" autoComplete="one-time-code" placeholder="123 456" style={S.felt + ';text-align:center;font-size:22px;letter-spacing:.2em;font-family:IBM Plex Mono,monospace'} />
        {feil && <span style="color:#ff9a8a;font-size:13px">{feil}</span>}
        <button disabled={opptatt || kode.trim().length < 6} onClick={() => void send()} style={S.gull + ';width:100%'}>{opptatt ? 'Sjekker …' : 'Bekreft'}</button>
        <span style={S.liten}>Mistet telefonen og reservekodene? Kontakt Skjold Lab, så kan totrinnsbekreftelsen tilbakestilles.</span>
      </div>
    </div>);
}

function Sikkerhet({ k, last }: { k: Konto; last: () => void }) {
  const [oppsett, setOppsett] = useState<{ hemmelighet: string; uri: string } | null>(null);
  const [kode, setKode] = useState(''), [koder, setKoder] = useState<string[] | null>(null), [av, setAv] = useState<'av' | 'nye' | null>(null);
  const start = async () => { try { setOppsett(await kall('POST', '/api/hjem/konto/2fa/start', {})); setKode(''); } catch (e) { visMelding((e as Error).message); } };
  const aktiver = async () => { try { const r = await kall<{ reservekoder: string[] }>('POST', '/api/hjem/konto/2fa/aktiver', { kode }); setKoder(r.reservekoder); setOppsett(null); setKode(''); last(); } catch (e) { visMelding((e as Error).message); } };
  const medKode = async () => {
    try {
      if (av === 'av') { await kall('POST', '/api/hjem/konto/2fa/av', { kode }); visMelding('Totrinnsbekreftelse er slått av'); }
      else { const r = await kall<{ reservekoder: string[] }>('POST', '/api/hjem/konto/2fa/nye-koder', { kode }); setKoder(r.reservekoder); }
      setAv(null); setKode(''); last();
    } catch (e) { visMelding((e as Error).message); }
  };
  return (
    <div class="inn" style="display:flex;flex-direction:column;gap:18px">
      <div><h1 style="margin:0;font-size:28px">Sikkerhet</h1><p style={S.liten}>Innstillinger og anbefalinger som holder kontoen din trygg.</p></div>
      <div style={S.kort}>
        <span style="font-size:17px;font-weight:600">Slik logger du inn</span>
        <div style={S.rad}><span style="flex:1"><b>E-post-kode eller Google</b><br /><span style={S.liten}>Du logger inn med {k.epost} via Cloudflare Access.</span></span><span class="mono" style="font-size:11px;color:var(--gronn)">PÅ</span></div>
        <div style={S.rad}>
          <span style="flex:1"><b>Totrinnsbekreftelse</b><br /><span style={S.liten}>{k.tofa.aktiv ? `På · ${k.tofa.reservekoderIgjen} reservekoder igjen` : 'Av – vi anbefaler å slå den på. Da trengs også en kode fra telefonen din.'}</span></span>
          {!k.tofa.aktiv && !oppsett && <button onClick={() => void start()} style={S.gull}>Slå på</button>}
          {k.tofa.aktiv && !av && <><button onClick={() => { setAv('nye'); setKode(''); }} style={S.knapp}>Nye reservekoder</button><button onClick={() => { setAv('av'); setKode(''); }} style={S.knapp + ';color:#ff9a8a'}>Slå av</button></>}
        </div>
        {oppsett && <div class="inn" style="display:grid;grid-template-columns:auto minmax(0,1fr);gap:22px;align-items:center;padding:16px;border-radius:16px;background:#101011;border:1px solid var(--kant)">
          <Qr tekst={oppsett.uri} />
          <div style="display:flex;flex-direction:column;gap:10px">
            <b>1. Skann koden med kodeappen</b>
            <span style={S.liten}>Google Authenticator, Microsoft Authenticator, 1Password, Bitwarden … Eller skriv inn nøkkelen:<br /><span class="mono" style="color:var(--tekst);word-break:break-all">{oppsett.hemmelighet.replace(/(.{4})/g, '$1 ').trim()}</span></span>
            <b>2. Skriv koden appen viser</b>
            <div style="display:flex;gap:8px"><input value={kode} onInput={(e) => setKode(e.currentTarget.value)} onKeyDown={(e) => { if (e.key === 'Enter') void aktiver(); }} inputMode="numeric" placeholder="123456" style={S.felt + ';max-width:170px;font-family:IBM Plex Mono,monospace;letter-spacing:.15em'} /><button onClick={() => void aktiver()} disabled={kode.replace(/\D/g, '').length !== 6} style={S.gull}>Slå på</button><button onClick={() => setOppsett(null)} style={S.knapp}>Avbryt</button></div>
          </div>
        </div>}
        {av && <div class="inn" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:14px;border-radius:14px;background:#101011;border:1px solid var(--kant)">
          <span style={S.liten + ';flex-basis:100%'}>{av === 'av' ? 'Skriv en kode fra kodeappen (eller en reservekode) for å slå av totrinnsbekreftelsen.' : 'Skriv en kode fra kodeappen for å lage nye reservekoder. De gamle slutter å virke.'}</span>
          <input value={kode} onInput={(e) => setKode(e.currentTarget.value)} placeholder="Kode" style={S.felt + ';max-width:200px;font-family:IBM Plex Mono,monospace'} />
          <button onClick={() => void medKode()} style={av === 'av' ? S.knapp + ';color:#ff9a8a' : S.gull}>{av === 'av' ? 'Slå av' : 'Lag nye koder'}</button><button onClick={() => setAv(null)} style={S.knapp}>Avbryt</button>
        </div>}
        {koder && <div class="inn" style="padding:18px;border-radius:16px;background:#1c170d;border:1px solid #5a4420;display:flex;flex-direction:column;gap:10px">
          <b style="color:var(--gull)">Reservekodene dine – ta vare på dem</b>
          <span style={S.liten}>Hver kode kan brukes én gang hvis du ikke har telefonen. Skriv dem ut eller lagre dem i passordbehandleren. De vises bare nå.</span>
          <div class="mono" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 22px;font-size:16px;letter-spacing:.06em">{koder.map((x) => <span key={x}>{x}</span>)}</div>
          <div style="display:flex;gap:8px"><button onClick={() => { void navigator.clipboard?.writeText(koder.join('\n')); visMelding('Kopiert'); }} style={S.knapp}>Kopier</button><button onClick={() => window.print()} style={S.knapp}>Skriv ut</button><button onClick={() => setKoder(null)} style={S.gull}>Jeg har tatt vare på dem</button></div>
        </div>}
      </div>
      <div style={S.kort}>
        <span style="font-size:17px;font-weight:600">Enhetene dine</span>
        <div style={S.rad}><span style="flex:1"><b>Logg ut på alle enheter</b><br /><span style={S.liten}>Alle telefoner og nettlesere må bekrefte med kode igjen (når totrinnsbekreftelse er på).</span></span>
          <button onClick={() => { if (confirm('Logge ut på alle enheter?')) void kall('POST', '/api/hjem/konto/logg-ut-overalt', {}).then(() => { visMelding('Logget ut overalt'); setTimeout(() => location.reload(), 900); }); }} style={S.knapp}>Logg ut overalt</button></div>
      </div>
    </div>);
}

function App() {
  const [meg, setMeg] = useState<Meg | null>(null), [k, setK] = useState<Konto | null>(null), [steder, setSteder] = useState<Sted[]>([]);
  const [feil, setFeil] = useState(''), [side, setSide] = useState(qs.get('side') || (qs.has('velkommen') ? 'velkommen' : 'hjem'));
  const [navn, setNavn] = useState(''), [msg, setMsg] = useState(''), [nyttHjem, setNyttHjem] = useState('');
  visMelding = (t) => { setMsg(t); setTimeout(() => setMsg(''), 3200); };
  const last = async () => {
    try {
      const m = await kall<Meg>('GET', '/api/hjem/meg'); setMeg(m);
      if (m.tofa && !m.tofaOk) return;
      const [kk, ss] = await Promise.all([kall<Konto>('GET', '/api/hjem/konto'), kall<Sted[]>('GET', '/api/hjem/steder')]);
      setK(kk); setSteder(ss); setNavn(kk.navn);
    } catch (e) { setFeil((e as Error).message); }
  };
  useEffect(() => { void last(); }, []);
  if (feil) return <div style="min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:20px;text-align:center"><Logo k={1.3} /><h1 style="margin:8px 0 0">Skjold-konto</h1><p style={S.liten}>{feil}</p><a href="/" style={S.gull + ';display:inline-flex;align-items:center;text-decoration:none'}>Logg inn</a></div>;
  if (meg?.tofa && !meg.tofaOk) return <Bekreft ferdig={() => void last()} />;
  if (!meg || !k) return <div style="min-height:100vh;display:flex;align-items:center;justify-content:center"><Logo k={1.3} /></div>;
  const fornavn = (k.navn || k.epost.split('@')[0] || '').split(' ')[0];
  const MENY: [string, string, string][] = [['hjem', 'Oversikt', 'M3 11l9-7 9 7M5 10v10h14V10'], ['info', 'Personlig info', 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0'], ['sikkerhet', 'Sikkerhet', 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z'], ['deling', 'Hjem og deling', 'M4 10l8-6 8 6v10H4zM9 20v-6h6v6'], ['data', 'Data og personvern', 'M4 6h16v12H4zM4 10h16']];
  const lagHjem = async () => { try { await kall('POST', '/api/hjem/steder', { navn: nyttHjem.trim() || 'Hjem' }); setNyttHjem(''); visMelding('Hjemmet er laget'); await last(); } catch (e) { visMelding((e as Error).message); } };
  let innhold;
  if (side === 'velkommen') innhold = (
    <div class="inn" style="display:flex;flex-direction:column;gap:18px">
      <div style={S.kort + ';background:linear-gradient(135deg,#1c170d,#141415 60%);border-color:#3a2e17;padding:30px'}>
        <span class="mono" style="font-size:11px;letter-spacing:.18em;color:var(--gull)">VELKOMMEN TIL SKJOLD</span>
        <h1 style="margin:0;font-size:30px;letter-spacing:-.01em">Kontoen din er klar{fornavn ? ', ' + fornavn : ''}</h1>
        <p style={S.liten + ';font-size:14px'}>Med en Skjold-konto når du enhetene dine hjemmefra, deler hjemmet med familien og tar vare på favoritter og innstillinger i Skjold Lab Valhalla.</p>
      </div>
      {[['1', 'Hva heter du?', <div style="display:flex;gap:8px"><input value={navn} onInput={(e) => setNavn(e.currentTarget.value)} placeholder="Navnet ditt" style={S.felt} /><button onClick={() => void kall('PATCH', '/api/hjem/konto', { navn }).then(() => { visMelding('Lagret'); void last(); })} style={S.gull}>Lagre</button></div>, !!k.navn],
        ['2', 'Lag hjemmet ditt', steder.length ? <span style={S.liten}>Du har {steder.length} hjem: {steder.map((x) => x.navn).join(', ')}</span> : <div style="display:flex;gap:8px"><input value={nyttHjem} onInput={(e) => setNyttHjem(e.currentTarget.value)} placeholder="For eksempel Hjemme" style={S.felt} /><button onClick={() => void lagHjem()} style={S.gull}>Lag</button></div>, steder.length > 0],
        ['3', 'Koble til Skjold-enheten', <span style={S.liten}>Åpne Skjold-appen eller web-UI-et, gå til Innstillinger → Skjold-hjem → hjemmet → <b>Legg til enhet</b>, og skriv koden inn på enheten. Nye enheter på samme nett blir med av seg selv.</span>, steder.some((x) => x.enheter > 0)],
        ['4', 'Slå på totrinnsbekreftelse', <button onClick={() => setSide('sikkerhet')} style={S.knapp + ';align-self:flex-start'}>Gå til Sikkerhet</button>, k.tofa.aktiv]].map(([n, t, c, ok]) => (
        <div key={String(n)} style={S.kort + ';flex-direction:row;gap:16px;align-items:flex-start'}>
          <span style={`width:34px;height:34px;flex-shrink:0;border-radius:17px;display:flex;align-items:center;justify-content:center;font-weight:700;${ok ? 'background:var(--gronn);color:#0b0b0c' : 'background:#1c170d;border:1px solid #5a4420;color:var(--gull)'}`}>{ok ? '✓' : n}</span>
          <span style="display:flex;flex-direction:column;gap:10px;flex:1;min-width:0"><b style="font-size:16px">{t}</b>{c}</span>
        </div>))}
      <div style="display:flex;gap:10px"><button onClick={() => setSide('hjem')} style={S.gull}>Ferdig</button>{qs.get('fra') && <a href={qs.get('fra') === 'app' ? '/' : String(qs.get('fra'))} style={S.knapp + ';display:inline-flex;align-items:center;text-decoration:none'}>Tilbake til Skjold</a>}</div>
    </div>);
  else if (side === 'info') innhold = (
    <div class="inn" style="display:flex;flex-direction:column;gap:18px">
      <div><h1 style="margin:0;font-size:28px">Personlig info</h1><p style={S.liten}>Navnet vises for dem du deler hjem med.</p></div>
      <div style={S.kort}>
        <div style={S.rad + ';border-top:none'}><span style="width:150px;color:var(--demp)">Navn</span><input value={navn} onInput={(e) => setNavn(e.currentTarget.value)} placeholder="Navnet ditt" style={S.felt + ';max-width:320px'} /><button disabled={navn === k.navn} onClick={() => void kall('PATCH', '/api/hjem/konto', { navn }).then(() => { visMelding('Lagret'); void last(); })} style={S.gull}>Lagre</button></div>
        <div style={S.rad}><span style="width:150px;color:var(--demp)">E-post</span><span style="flex:1">{k.epost}</span><span style={S.liten}>Brukes til innlogging</span></div>
        <div style={S.rad}><span style="width:150px;color:var(--demp)">Konto opprettet</span><span>{dato(k.opprettet)}</span></div>
      </div>
    </div>);
  else if (side === 'sikkerhet') innhold = <Sikkerhet k={k} last={() => void last()} />;
  else if (side === 'deling') innhold = (
    <div class="inn" style="display:flex;flex-direction:column;gap:18px">
      <div><h1 style="margin:0;font-size:28px">Hjem og deling</h1><p style={S.liten}>Hjemmene du eier eller er medlem av. Del et hjem i Skjold-appen eller web-UI-et (Skjold-hjem → hjemmet → Delt med).</p></div>
      <div style={S.kort}>
        {steder.map((x, i) => <div key={x.id} style={S.rad + (i ? '' : ';border-top:none')}><span style="flex:1"><b>{x.navn}</b><br /><span style={S.liten}>{x.rolle === 'eier' ? 'Du eier' : 'Medlem'} · {x.enheter} enheter, {x.online} på nett · delt med {(x.medlemmer?.length ?? 1) - 1}</span></span><a href="/" style="font-size:13.5px">Åpne ›</a></div>)}
        {!steder.length && <span style={S.liten}>Ingen hjem ennå.</span>}
        <div style="display:flex;gap:8px;margin-top:6px"><input value={nyttHjem} onInput={(e) => setNyttHjem(e.currentTarget.value)} placeholder="Nytt hjem, f.eks. Hytta" style={S.felt + ';max-width:320px'} /><button onClick={() => void lagHjem()} style={S.gull}>Lag hjem</button></div>
      </div>
    </div>);
  else if (side === 'data') innhold = (
    <div class="inn" style="display:flex;flex-direction:column;gap:18px">
      <div><h1 style="margin:0;font-size:28px">Data og personvern</h1><p style={S.liten}>Skjold lagrer så lite som mulig. Favoritter og innstillinger i Skjold Cloud er ende-til-ende-kryptert – bare enhetene dine kan lese dem.</p></div>
      <div style={S.kort}>
        <span style="font-size:17px;font-weight:600">Skjold Cloud</span>
        {k.sync.length ? k.sync.map((x) => <div key={x.del} style={S.rad}><span style="flex:1;text-transform:capitalize">{x.del}</span><span style={S.liten}>{Math.round(x.storrelse / 1024 * 10) / 10} kB · {dato(x.endret)}</span></div>) : <span style={S.liten}>Ingenting lagret ennå.</span>}
        {k.sync.length > 0 && <button onClick={() => { if (confirm('Slette alt i Skjold Cloud? Enhetene beholder sin egen kopi.')) void kall('DELETE', '/api/hjem/sync').then(() => { visMelding('Slettet'); void last(); }); }} style={S.knapp + ';align-self:flex-start;color:#ff9a8a'}>Slett alt i Skjold Cloud</button>}
      </div>
      <div style={S.kort + ';border-color:#3a2a20'}>
        <span style="font-size:17px;font-weight:600">Slett Skjold-kontoen</span>
        <span style={S.liten}>Du fjernes fra hjemmene du er medlem av, og dataene i Skjold Cloud slettes. Eier du et hjem, må du overføre eierskapet eller slette hjemmet først. Enhetene virker videre lokalt.</span>
        <button onClick={() => { if (prompt('Skriv SLETT for å slette kontoen') === 'SLETT') void kall('DELETE', '/api/hjem/konto').then(() => { visMelding('Kontoen er slettet'); setTimeout(() => { location.href = '/'; }, 1200); }).catch((e) => visMelding((e as Error).message)); }} style={S.knapp + ';align-self:flex-start;color:#ff9a8a;border-color:#3a2a20'}>Slett kontoen</button>
      </div>
    </div>);
  else innhold = (
    <div class="inn" style="display:flex;flex-direction:column;gap:18px">
      <div style="display:flex;flex-direction:column;align-items:center;gap:10px;padding:20px 0 6px;text-align:center">
        <span style="width:84px;height:84px;border-radius:42px;background:linear-gradient(135deg,#f3cf7f,#d9a441);color:#0b0b0c;display:flex;align-items:center;justify-content:center;font-size:36px;font-weight:600">{(k.navn || k.epost)[0]?.toUpperCase()}</span>
        <h1 style="margin:6px 0 0;font-size:28px">Velkommen, {fornavn}</h1>
        <span style={S.liten}>Administrer Skjold-kontoen din – hjem, sikkerhet og data.</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px">
        {[['sikkerhet', k.tofa.aktiv ? 'Kontoen er beskyttet' : 'Beskytt kontoen', k.tofa.aktiv ? 'Totrinnsbekreftelse er på.' : 'Slå på totrinnsbekreftelse med en kodeapp.', !k.tofa.aktiv],
          ['deling', steder.length + ' hjem', steder.filter((x) => x.rolle === 'eier').length + ' eier du · ' + steder.reduce((a, x) => a + (x.enheter || 0), 0) + ' enheter', false],
          ['info', 'Personlig info', k.navn ? k.navn + ' · ' + k.epost : 'Legg til navnet ditt', !k.navn],
          ['data', 'Data og personvern', 'Skjold Cloud: ' + (k.sync.length ? k.sync.length + ' deler lagret' : 'ingenting lagret'), false]].map(([id, t, u, varsel]) => (
          <button key={String(id)} onClick={() => setSide(String(id))} style={S.kort + `;text-align:left;cursor:pointer;${varsel ? 'border-color:#5a4420' : ''}`}>
            <b style="font-size:16px">{t}</b><span style={S.liten}>{u}</span>{varsel && <span style="font-size:13px;color:var(--gull)">Fiks nå ›</span>}
          </button>))}
      </div>
      {meg.valhalla && <a href="/valhalla/" style={S.kort + ';flex-direction:row;align-items:center;text-decoration:none;color:var(--tekst);background:linear-gradient(135deg,#1c170d,#141415);border-color:#5a4420'}><Logo k={0.7} /><span style="flex:1"><span class="mono" style="font-size:10px;letter-spacing:.16em;color:var(--gull)">SKJOLD LAB</span><br /><b>Valhalla – styr tjenesten</b></span><span style="color:var(--gull)">↗</span></a>}
    </div>);
  return (
    <div style="min-height:100vh">
      <header style="display:flex;align-items:center;gap:14px;padding:18px 28px;border-bottom:1px solid var(--kant)">
        <a href="/" style="display:flex;align-items:center;gap:12px;text-decoration:none;color:var(--tekst)"><Logo /><span style="font-size:18px;font-weight:600">Skjold-konto</span></a>
        <div style="flex:1" />
        <span style="font-size:13px;color:var(--demp)">{k.epost}</span>
        <span style="width:36px;height:36px;border-radius:18px;background:linear-gradient(135deg,#f3cf7f,#d9a441);color:#0b0b0c;display:flex;align-items:center;justify-content:center;font-weight:600">{(k.navn || k.epost)[0]?.toUpperCase()}</span>
      </header>
      <div class="oppsett" style="display:grid;grid-template-columns:250px minmax(0,1fr);gap:28px;max-width:1100px;margin:0 auto;padding:26px 24px 60px">
        <nav class="meny" style="display:flex;flex-direction:column;gap:4px;position:sticky;top:20px;align-self:start">
          {MENY.map(([id, n, ik]) => <button key={id} onClick={() => setSide(id)} style={`height:46px;border:none;border-radius:23px;padding:0 18px;display:flex;align-items:center;gap:14px;cursor:pointer;font-size:14.5px;font-weight:${side === id ? 600 : 400};background:${side === id ? 'rgba(240,196,106,.14)' : 'transparent'};color:${side === id ? 'var(--gull)' : 'var(--tekst)'}`}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={ik} /></svg>{n}</button>)}
        </nav>
        <main>{innhold}</main>
      </div>
      <Melding t={msg} />
    </div>);
}

render(<App />, document.getElementById('konto')!);
