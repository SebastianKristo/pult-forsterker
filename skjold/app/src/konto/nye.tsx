// Konto-siden: passkeys og sikkerhetsnøkler (WebAuthn), påloggede enheter, godkjenning fra en annen enhet og profilbilde.
import { useEffect, useRef, useState } from 'preact/hooks';
import { kall, S, visMelding, tid } from './felles';

// ---------- WebAuthn ----------
const fraB64u = (s: string) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4)), (c) => c.charCodeAt(0));
const tilB64u = (b: ArrayBuffer) => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
export const harWebauthn = () => typeof window !== 'undefined' && !!window.PublicKeyCredential && !!navigator.credentials;

interface OpprettValg { challenge: string; rp: { name: string; id: string }; user: { id: string; name: string; displayName: string }; pubKeyCredParams: PublicKeyCredentialParameters[]; timeout: number; attestation: AttestationConveyancePreference; excludeCredentials: { type: 'public-key'; id: string }[]; authenticatorSelection: AuthenticatorSelectionCriteria }
export async function registrerNokkel(type: 'passkey' | 'nokkel', navn: string) {
  const o = await kall<OpprettValg>('POST', '/api/hjem/konto/passkey/start', { type });
  const c = (await navigator.credentials.create({ publicKey: {
    ...o, challenge: fraB64u(o.challenge), user: { ...o.user, id: fraB64u(o.user.id) },
    excludeCredentials: o.excludeCredentials.map((x) => ({ ...x, id: fraB64u(x.id) })),
  } })) as PublicKeyCredential | null;
  if (!c) throw new Error('avbrutt');
  const r = c.response as AuthenticatorAttestationResponse;
  return kall('POST', '/api/hjem/konto/passkey/registrer', { clientDataJSON: tilB64u(r.clientDataJSON), attestationObject: tilB64u(r.attestationObject), navn });
}
export async function loggInnMedNokkel() {
  const o = await kall<{ challenge: string; rpId: string; timeout: number; userVerification: UserVerificationRequirement; allowCredentials: { type: 'public-key'; id: string }[] }>('POST', '/api/hjem/konto/passkey/login-start', {});
  const c = (await navigator.credentials.get({ publicKey: { ...o, challenge: fraB64u(o.challenge), allowCredentials: o.allowCredentials.map((x) => ({ ...x, id: fraB64u(x.id) })) } })) as PublicKeyCredential | null;
  if (!c) throw new Error('avbrutt');
  const r = c.response as AuthenticatorAssertionResponse;
  return kall('POST', '/api/hjem/konto/passkey/login', { id: c.id, clientDataJSON: tilB64u(r.clientDataJSON), authenticatorData: tilB64u(r.authenticatorData), signature: tilB64u(r.signature) });
}
const webauthnFeil = (e: unknown) => { const n = (e as Error).name; return n === 'NotAllowedError' ? 'Avbrutt eller tidsavbrudd' : n === 'InvalidStateError' ? 'Denne nøkkelen er allerede lagt til' : (e as Error).message; };

/** «Godkjenn fra en annen enhet»: viser et tall som skal trykkes på den andre enheten. */
export function GodkjennHer({ ferdig, avbryt }: { ferdig: () => void; avbryt: () => void }) {
  const [f, setF] = useState<{ rid: string; tall: number } | null>(null), [status, setStatus] = useState('starter');
  useEffect(() => {
    let slutt = false, id = 0;
    void kall<{ rid: string; tall: number }>('POST', '/api/hjem/konto/godkjenn/start', {}).then((r) => {
      setF(r); setStatus('venter');
      const poll = async () => {
        if (slutt) return;
        try {
          const s = await kall<{ status: string }>('GET', '/api/hjem/konto/godkjenn/status?rid=' + r.rid);
          if (s.status === 'godkjent') { ferdig(); return; }
          if (s.status !== 'venter') { setStatus(s.status); return; }
        } catch { /* prøv igjen */ }
        id = window.setTimeout(() => void poll(), 2000);
      };
      void poll();
    }).catch((e) => { setStatus('feil'); visMelding((e as Error).message); });
    return () => { slutt = true; clearTimeout(id); };
  }, []);
  return (
    <div class="inn" style="display:flex;flex-direction:column;align-items:center;gap:12px;width:100%">
      {status === 'venter' && f && <>
        <span style={S.liten}>Åpne Skjold-appen eller konto-siden på en enhet der du allerede er logget inn, og trykk på dette tallet:</span>
        <span class="mono" style="font-size:64px;font-weight:500;color:var(--gull);line-height:1">{f.tall}</span>
        <span style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--demp)"><i class="puls" />Venter på godkjenning …</span>
      </>}
      {status === 'avvist' && <span style="color:#ff9a8a">Innloggingen ble avvist på den andre enheten.</span>}
      {status === 'utlopt' && <span style="color:#ff9a8a">Forespørselen gikk ut. Prøv igjen.</span>}
      <button onClick={avbryt} style={S.knapp}>Tilbake</button>
    </div>);
}

interface Ventende { rid: string; navn: string; sted: string; t: number; valg: number[] }
/** Innlogget enhet: «Er det deg som logger inn?» – trykk riktig tall. */
export function GodkjennVarsel() {
  const [l, setL] = useState<Ventende[]>([]);
  useEffect(() => {
    let id = 0;
    const poll = async () => { try { setL(await kall<Ventende[]>('GET', '/api/hjem/konto/godkjenn/ventende')); } catch { /* */ } id = window.setTimeout(() => void poll(), document.hidden ? 15000 : 4000); };
    void poll(); return () => clearTimeout(id);
  }, []);
  const f = l[0];
  if (!f) return null;
  const svar = async (s: number | 'avvis') => {
    try { const r = await kall<{ status: string }>('POST', '/api/hjem/konto/godkjenn/' + f.rid, { svar: s }); visMelding(r.status === 'godkjent' ? 'Innloggingen er godkjent' : 'Innloggingen ble avvist'); } catch (e) { visMelding((e as Error).message); }
    setL(l.slice(1));
  };
  return (
    <div style="position:fixed;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(6px);z-index:30;display:flex;align-items:center;justify-content:center;padding:20px">
      <div class="inn" style={S.kort + ';max-width:400px;width:100%;align-items:center;text-align:center;padding:30px'}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--gull)" stroke-width="1.6"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /></svg>
        <h2 style="margin:0;font-size:21px">Prøver du å logge inn?</h2>
        <span style={S.liten}>{f.navn}{f.sted ? ' · ' + f.sted : ''} · {tid(f.t)}</span>
        <span style="font-size:14px">Trykk tallet som vises på den andre enheten.</span>
        <div style="display:flex;gap:12px">{f.valg.map((x) => <button key={x} onClick={() => void svar(x)} class="mono" style="width:76px;height:76px;border-radius:38px;border:1px solid var(--kant);background:#1b1b1c;font-size:26px;cursor:pointer">{x}</button>)}</div>
        <button onClick={() => void svar('avvis')} style={S.knapp + ';color:#ff9a8a'}>Nei, det er ikke meg</button>
      </div>
    </div>);
}

export interface Nokkel { id: string; navn: string; type: 'passkey' | 'nokkel'; opprettet: number; sist: number | null }
export function Nokler({ liste, last }: { liste: Nokkel[]; last: () => void }) {
  const [opptatt, setOpptatt] = useState(false);
  const legg = async (type: 'passkey' | 'nokkel') => {
    const navn = prompt(type === 'nokkel' ? 'Navn på sikkerhetsnøkkelen (f.eks. YubiKey)' : 'Navn på passkeyen (f.eks. iPhone)', type === 'nokkel' ? 'Sikkerhetsnøkkel' : 'Passkey');
    if (navn === null) return;
    setOpptatt(true);
    try { await registrerNokkel(type, navn); visMelding(type === 'nokkel' ? 'Sikkerhetsnøkkelen er lagt til' : 'Passkeyen er lagt til'); last(); } catch (e) { visMelding(webauthnFeil(e)); }
    setOpptatt(false);
  };
  const ikon = (t: string) => t === 'nokkel' ? 'M15 7a4 4 0 1 1-3.9 4.9L4 19v2h3v-2h2v-2h2l1.1-1.1A4 4 0 0 1 15 7zM16 10h.01' : 'M12 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 20a6 6 0 0 1 12 0M18 11h4M20 9v4';
  return (
    <div style={S.kort}>
      <span style="font-size:17px;font-weight:600">Passkeys og sikkerhetsnøkler</span>
      <span style={S.liten}>Bekreft med fingeren, ansiktet eller en fysisk nøkkel (YubiKey o.l.) i stedet for en kode. Teller som totrinnsbekreftelse.</span>
      {liste.map((n) => <div key={n.id} style={S.rad}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--gull)" stroke-width="1.7" stroke-linecap="round"><path d={ikon(n.type)} /></svg>
        <span style="flex:1;min-width:0"><b>{n.navn}</b><br /><span style={S.liten}>{n.type === 'nokkel' ? 'Sikkerhetsnøkkel' : 'Passkey'} · lagt til {tid(n.opprettet)}{n.sist ? ' · sist brukt ' + tid(n.sist) : ''}</span></span>
        <button onClick={() => { if (confirm('Fjerne «' + n.navn + '»?')) void kall('DELETE', '/api/hjem/konto/passkey/' + encodeURIComponent(n.id)).then(() => { visMelding('Fjernet'); last(); }).catch((e) => visMelding((e as Error).message)); }} style={S.knapp + ';color:#ff9a8a'}>Fjern</button>
      </div>)}
      {!harWebauthn() ? <span style={S.liten}>Denne nettleseren støtter ikke passkeys.</span> :
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button disabled={opptatt} onClick={() => void legg('passkey')} style={S.gull}>Legg til passkey</button><button disabled={opptatt} onClick={() => void legg('nokkel')} style={S.knapp}>Legg til sikkerhetsnøkkel</button></div>}
    </div>);
}

interface Okt { sid: string; navn: string; sted: string; opprettet: number; sist: number; bekreftet: boolean; metode: string | null; denne: boolean }
export function Okter() {
  const [l, setL] = useState<Okt[] | null>(null);
  const last = () => void kall<Okt[]>('GET', '/api/hjem/konto/okter').then(setL).catch(() => setL([]));
  useEffect(last, []);
  const ikon = (n: string) => /iPhone|Android|Skjold-appen/.test(n) ? 'M8 3h8a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM11 18h2' : 'M3 5h18v11H3zM8 20h8M12 16v4';
  return (
    <div style={S.kort}>
      <span style="font-size:17px;font-weight:600">Enhetene dine</span>
      <span style={S.liten}>Nettlesere og telefoner som er logget inn på Skjold-kontoen. Kjenner du ikke igjen en, logg den ut.</span>
      {(l || []).map((o) => <div key={o.sid} style={S.rad}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d={ikon(o.navn)} /></svg>
        <span style="flex:1;min-width:0"><b>{o.navn}</b>{o.denne && <span class="mono" style="font-size:10.5px;color:var(--gronn);margin-left:8px">DENNE ENHETEN</span>}<br />
          <span style={S.liten}>{o.sted ? o.sted + ' · ' : ''}sist aktiv {tid(o.sist)} · {o.bekreftet ? (o.metode ? 'bekreftet med ' + o.metode : 'innlogget') : 'ikke bekreftet'}</span></span>
        {!o.denne && <button onClick={() => void kall('DELETE', '/api/hjem/konto/okter/' + o.sid).then(() => { visMelding('Logget ut'); last(); })} style={S.knapp}>Logg ut</button>}
      </div>)}
      {l === null && <span style={S.liten}>Henter …</span>}
      <div style={S.rad}><span style="flex:1"><b>Logg ut på alle enheter</b><br /><span style={S.liten}>Alle må logge inn igjen – og bekrefte med kode, passkey eller fra en annen enhet når totrinnsbekreftelse er på. Også denne.</span></span>
        <button onClick={() => { if (confirm('Logge ut på alle enheter, også denne?')) void kall('POST', '/api/hjem/konto/logg-ut-overalt', {}).then(() => { visMelding('Logget ut overalt'); setTimeout(() => location.reload(), 900); }); }} style={S.knapp + ';color:#ff9a8a'}>Logg ut overalt</button></div>
    </div>);
}

// ---------- profilbilde ----------
export function Avatar({ bilde, navn, px = 36 }: { bilde?: string; navn: string; px?: number }) {
  return bilde ? <img src={bilde} alt="" width={px} height={px} style={`width:${px}px;height:${px}px;border-radius:50%;object-fit:cover;display:block;flex-shrink:0`} />
    : <span style={`width:${px}px;height:${px}px;flex-shrink:0;border-radius:50%;background:linear-gradient(135deg,#f3cf7f,#d9a441);color:#0b0b0c;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:${Math.round(px * 0.43)}px`}>{(navn || '?')[0]?.toUpperCase()}</span>;
}

/** Velg utsnitt: dra bildet under sirkelen, zoom med hjulet/klypa eller glidebryteren. Gir et 256 px JPEG-data-URL. */
export function BildeKutt({ fil, ferdig, avbryt }: { fil: File; ferdig: (dataUrl: string) => void; avbryt: () => void }) {
  const V = 300, R = 130;   // visningens størrelse og sirkelens radius
  const [img, setImg] = useState<HTMLImageElement | null>(null);
  const [z, setZ] = useState(1), [pos, setPos] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null), pekere = useRef(new Map<number, { x: number; y: number }>()), klyp = useRef(0);
  useEffect(() => {
    const u = URL.createObjectURL(fil), i = new Image();
    i.onload = () => setImg(i); i.onerror = () => { visMelding('Kunne ikke lese bildet'); avbryt(); };
    i.src = u; return () => URL.revokeObjectURL(u);
  }, [fil]);
  if (!img) return null;
  const grunn = (2 * R) / Math.min(img.width, img.height);   // minste skala som fyller sirkelen
  const sk = grunn * z, w = img.width * sk, h = img.height * sk;
  const klem = (p: { x: number; y: number }, s = sk) => { const mx = Math.max(0, (img.width * s) / 2 - R), my = Math.max(0, (img.height * s) / 2 - R); return { x: Math.min(mx, Math.max(-mx, p.x)), y: Math.min(my, Math.max(-my, p.y)) }; };
  const zoom = (nz: number) => { const zz = Math.min(5, Math.max(1, nz)); setZ(zz); setPos((p) => klem({ x: (p.x * zz) / z, y: (p.y * zz) / z }, grunn * zz)); };
  const lagre = () => {
    const c = document.createElement('canvas'); c.width = c.height = 256;
    const g = c.getContext('2d')!, k = 256 / (2 * R);
    g.fillStyle = '#141415'; g.fillRect(0, 0, 256, 256);
    g.imageSmoothingQuality = 'high';
    g.drawImage(img, (V / 2 + pos.x - w / 2 - (V / 2 - R)) * k, (V / 2 + pos.y - h / 2 - (V / 2 - R)) * k, w * k, h * k);
    let q = 0.86, u = c.toDataURL('image/jpeg', q);
    while (u.length > 88000 && q > 0.4) { q -= 0.1; u = c.toDataURL('image/jpeg', q); }
    ferdig(u);
  };
  return (
    <div style="position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(6px);z-index:30;display:flex;align-items:center;justify-content:center;padding:20px">
      <div class="inn" style={S.kort + ';align-items:center;max-width:380px;width:100%'}>
        <b style="font-size:17px">Velg utsnitt</b>
        <span style={S.liten}>Dra for å flytte, zoom med hjulet eller to fingre.</span>
        <div style={`position:relative;width:${V}px;height:${V}px;overflow:hidden;border-radius:16px;background:#0b0b0c;touch-action:none;cursor:grab;max-width:100%`}
          onWheel={(e) => { e.preventDefault(); zoom(z * (e.deltaY < 0 ? 1.08 : 1 / 1.08)); }}
          onPointerDown={(e) => { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); pekere.current.set(e.pointerId, { x: e.clientX, y: e.clientY }); drag.current = { x: e.clientX, y: e.clientY, px: pos.x, py: pos.y }; klyp.current = 0; }}
          onPointerMove={(e) => {
            if (!pekere.current.has(e.pointerId)) return;
            pekere.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
            const p = [...pekere.current.values()];
            if (p.length === 2 && p[0] && p[1]) { const d = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y); if (klyp.current) zoom(z * (d / klyp.current)); klyp.current = d; return; }
            if (drag.current) setPos(klem({ x: drag.current.px + e.clientX - drag.current.x, y: drag.current.py + e.clientY - drag.current.y }));
          }}
          onPointerUp={(e) => { pekere.current.delete(e.pointerId); drag.current = null; klyp.current = 0; }}>
          <img src={img.src} alt="" draggable={false} style={`position:absolute;left:${V / 2 + pos.x - w / 2}px;top:${V / 2 + pos.y - h / 2}px;width:${w}px;height:${h}px;max-width:none;user-select:none;pointer-events:none`} />
          <svg width={V} height={V} style="position:absolute;inset:0;pointer-events:none"><defs><mask id="hull"><rect width={V} height={V} fill="#fff" /><circle cx={V / 2} cy={V / 2} r={R} fill="#000" /></mask></defs>
            <rect width={V} height={V} fill="rgba(11,11,12,.62)" mask="url(#hull)" /><circle cx={V / 2} cy={V / 2} r={R} fill="none" stroke="#f0c46a" stroke-width="2" /></svg>
        </div>
        <input type="range" min="1" max="5" step="0.01" value={z} onInput={(e) => zoom(Number(e.currentTarget.value))} style="width:100%;accent-color:var(--gull)" aria-label="Zoom" />
        <div style="display:flex;gap:8px"><button onClick={avbryt} style={S.knapp}>Avbryt</button><button onClick={lagre} style={S.gull}>Bruk bildet</button></div>
      </div>
    </div>);
}
