// Innstillinger → Maskinvare → Pinner (GPIO): pinne-editoren for Skjold S1 rev F.
// Viser den 40-pinners headeren loddrett (pinne 1 øverst ved SD-kort-enden, oddetall innerst, partall mot kanten),
// med etikettene på sidene så den får plass på en smal mobilskjerm. Trykk en GPIO for å velge hva den skal være,
// eller bruk listen over funksjonene under. Lagres i /etc/skjold/s1f_pins.yaml via POST /api/s1f/pins.
import { useEffect, useMemo, useState } from 'preact/hooks';
import { api, ApiError, type S1fHeaderPinne, type S1fPins, type S1fRegler, type S1fTildeling } from '../lib/api';
import { showToast } from '../lib/store';
import { endringer, eierAv, fysisk, GRUPPE, I2S, ledigeGpio, navnPaa, sperret, STROM, tildel, valider } from '../lib/pinner';

const CARD = 'display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;flex-shrink:0';
const MONO = "font-family:'IBM Plex Mono',monospace";
const BTN = (bd = '#2e2e30', fg = '#f2f2ee', bg = '#1b1b1c') => `height:36px;padding:0 14px;border-radius:9px;border:1px solid ${bd};background:${bg};color:${fg};font-size:13px;cursor:pointer;white-space:nowrap`;
const PCB = '#0e2418';

type Visning = { farge: string; ring: string; tittel: string; under: string; gpio: number | null; stiplet?: boolean };

function gruppeAv(r: S1fRegler, fid: string): string {
  return r.funksjoner.find((f) => f.id === fid)?.gruppe ?? '';
}

/** Hvordan én fysisk pinne tegnes: farge, etikett og undertekst. */
function visning(r: S1fRegler, t: S1fTildeling, p: S1fHeaderPinne): Visning {
  if (p.type === '3V3' || p.type === '5V' || p.type === 'GND') {
    return { farge: STROM[p.type] ?? '#333', ring: p.type === 'GND' ? '#5a5a5e' : 'transparent', tittel: p.type === '3V3' ? '3,3 V' : p.type === '5V' ? '5 V' : 'GND', under: '', gpio: null };
  }
  const g = p.gpio ?? -1;
  const alt = r.alt[String(g)];
  if (p.type === 'id') return { farge: GRUPPE.reservert!.farge, ring: 'transparent', tittel: g === 0 ? 'ID_SD' : 'ID_SC', under: `GPIO${g} · HAT-EEPROM`, gpio: g };
  if (I2S.has(g)) {
    const navn = { 18: 'Lydkort BCK', 19: 'Lydkort LRCK', 21: 'Lydkort DIN' }[g as 18 | 19 | 21];
    return { farge: GRUPPE.i2s!.farge, ring: 'transparent', tittel: navn, under: `GPIO${g} · I²S, fast`, gpio: g };
  }
  const eier = eierAv(t, g);
  if (eier) {
    const gr = GRUPPE[gruppeAv(r, eier)];
    return { farge: gr?.farge ?? '#888', ring: 'transparent', tittel: navnPaa(r, eier), under: `GPIO${g}` + (alt ? ' · ' + alt : ''), gpio: g };
  }
  if (sperret(r, g)) return { farge: 'transparent', ring: '#3a5a8a', tittel: 'Fri til lydkortet', under: `GPIO${g}`, gpio: g, stiplet: true };
  return { farge: 'transparent', ring: '#6b6b70', tittel: 'ledig', under: `GPIO${g}` + (alt ? ' · ' + alt : ''), gpio: g };
}

export function PinEditor() {
  const [data, setData] = useState<S1fPins | null>(null);
  const [feil, setFeil] = useState('');
  const [utkast, setUtkast] = useState<S1fTildeling>({});
  const [valgt, setValgt] = useState<number | null>(null);
  const [melding, setMelding] = useState('');
  const [lagrer, setLagrer] = useState<'' | 'lagrer' | 'restart'>('');
  const [svar, setSvar] = useState<string[]>([]);

  const last = async (forsok = 0): Promise<void> => {
    try {
      const d = await api.s1fPins();
      setData(d); setUtkast({ ...d.pinner }); setFeil(''); setLagrer(''); setMelding('');
    } catch (e) {
      if (forsok > 0) { setTimeout(() => void last(forsok - 1), 2500); return; }   // Skjold starter på nytt
      const s = e instanceof ApiError ? e.status : 0;
      setFeil(s === 404 ? 'Pinne-editoren finnes bare på Skjold S1 rev F.' : s === 403 ? 'Pinnene kan bare endres fra hjemmenettet.' : 'Fikk ikke kontakt med Skjold' + (e instanceof Error && e.message ? ` (${e.message})` : '') + '.');
      setLagrer('');
    }
  };
  useEffect(() => { void last(); }, []);

  const r = data?.regler;
  const v = useMemo(() => (r ? valider(r, utkast) : { feil: [], advarsler: [] }), [r, utkast]);
  const endret = useMemo(() => (r && data ? endringer(r, data.pinner, utkast) : []), [r, data, utkast]);
  const ikkeAktiv = useMemo(() => (r && data?.aktive ? endringer(r, data.aktive, data.pinner) : []), [r, data]);

  if (feil) return <div class="banner warn"><span>{feil}</span></div>;
  if (!data || !r) return <span style="font-size:13px;color:#8b8b86">Henter pinnene …</span>;

  const sett = (gpio: number, fid: string | null) => {
    const res = tildel(r, utkast, gpio, fid);
    setUtkast(res.t); setMelding(res.melding); showToast(res.melding, 3600); setValgt(null);
  };
  const fys = fysisk(r);

  const lagre = async () => {
    setLagrer('lagrer'); setSvar([]);
    try {
      const res = await api.s1fPinsSave(utkast);
      // advarslene vises allerede (samme regler lokalt); utkastet er nå det lagrede
      setData({ ...data, pinner: res.pinner, fil: res.fil, overstyrt: true }); setUtkast({ ...res.pinner }); setLagrer('restart'); setMelding('');
      showToast('Pinnene er lagret – Skjold starter på nytt', 4000);
      setTimeout(() => void last(10), 6000);
    } catch (e) {
      setLagrer(''); setSvar([e instanceof Error ? e.message : 'Lagring feilet']);
    }
  };
  const tilbakestill = async () => {
    setLagrer('lagrer');
    try {
      const res = await api.s1fPinsReset();
      if (res.restart) { setLagrer('restart'); showToast('Standardpinnene brukes igjen – Skjold starter på nytt', 4000); setTimeout(() => void last(10), 6000); }
      else void last();
    } catch (e) {
      setLagrer(''); setSvar([e instanceof Error ? e.message : 'Tilbakestilling feilet']);
    }
  };

  const rader = Array.from({ length: 20 }, (_, k) => [r.header[2 * k], r.header[2 * k + 1]] as const);
  const pinneKnapp = (p: S1fHeaderPinne | undefined) => {
    if (!p) return <span />;
    const vi = visning(r, utkast, p);
    const kan = p.type === 'gpio';
    const aktiv = valgt !== null && valgt === p.gpio;
    return (
      <button aria-label={`Pinne ${p.fys}: ${vi.tittel} ${vi.under}`} disabled={!kan} onClick={() => kan && setValgt(p.gpio)}
        style={`width:26px;height:26px;margin:3px auto;border-radius:${p.fys === 1 ? '4px' : '50%'};background:${vi.farge};border:2px ${vi.stiplet ? 'dashed' : 'solid'} ${aktiv ? '#fff' : vi.ring};box-shadow:${aktiv ? '0 0 0 3px #d9a441' : 'none'};color:${vi.farge === 'transparent' || p.type === 'GND' ? '#c9c9c4' : '#111'};${MONO};font-size:9.5px;font-weight:600;display:flex;align-items:center;justify-content:center;padding:0;cursor:${kan ? 'pointer' : 'default'}`}>
        {p.fys}
      </button>
    );
  };
  const etikett = (p: S1fHeaderPinne | undefined, side: 'v' | 'h') => {
    if (!p) return <span />;
    const vi = visning(r, utkast, p);
    const g = p.gpio;
    const nyEndret = g !== null && (eierAv(utkast, g) ?? null) !== (eierAv(data.pinner, g) ?? null);
    const varsel = g !== null && eierAv(utkast, g) && r.varsel[String(g)];
    const kan = p.type === 'gpio';
    return (
      <button disabled={!kan} onClick={() => kan && setValgt(g)}
        style={`display:flex;flex-direction:column;justify-content:center;gap:1px;width:100%;min-width:0;min-height:32px;padding:0 8px;border:none;background:${valgt !== null && valgt === g ? '#1c170d' : 'transparent'};border-radius:6px;text-align:${side === 'v' ? 'right' : 'left'};align-items:${side === 'v' ? 'flex-end' : 'flex-start'};cursor:${kan ? 'pointer' : 'default'};color:inherit`}>
        <span style={`font-size:12px;line-height:1.2;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:${vi.tittel === 'ledig' || vi.stiplet ? '#8b8b86' : '#f2f2ee'}`}>
          {side === 'v' && nyEndret ? <span style="color:#d9a441">● </span> : null}{varsel ? <span title={varsel} style="color:#e0a63a">⚠ </span> : null}{vi.tittel}{side === 'h' && nyEndret ? <span style="color:#d9a441"> ●</span> : null}
        </span>
        {vi.under && <span style={`${MONO};font-size:9.5px;color:#8b8b86;white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis`}>{vi.under}</span>}
      </button>
    );
  };

  const valgtSperret = valgt !== null ? sperret(r, valgt) : null;
  const valgtEier = valgt !== null ? eierAv(utkast, valgt) : undefined;
  const grupper = [...new Set(r.funksjoner.map((f) => f.gruppe))];
  const valg = ledigeGpio(r);

  return (
    <div style="display:flex;flex-direction:column;gap:14px;max-width:620px;width:100%;padding-bottom:20px">
      <span style="font-size:12px;color:#8b8b86;text-wrap:pretty">
        Trykk en GPIO-pinne og velg hva den skal brukes til. Velger du en pinne som er i bruk, bytter de to funksjonene pinne.
        Pinnene lagres i <span style={MONO}>{data.egen_fil}</span>, og Skjold starter på nytt for å ta dem i bruk.
      </span>
      <div style="display:flex;flex-wrap:wrap;gap:6px 12px">
        {Object.entries(GRUPPE).map(([k, gr]) => <span key={k} style="display:flex;align-items:center;gap:5px;font-size:11px;color:#c9c9c4"><span style={`width:10px;height:10px;border-radius:50%;background:${gr.farge}`} />{gr.navn}</span>)}
        {(['3V3', '5V', 'GND'] as const).map((k) => <span key={k} style="display:flex;align-items:center;gap:5px;font-size:11px;color:#c9c9c4"><span style={`width:10px;height:10px;border-radius:50%;background:${STROM[k]};border:1px solid #5a5a5e`} />{k === '3V3' ? '3,3 V' : k === '5V' ? '5 V' : 'GND'}</span>)}
      </div>

      {melding && <div class="banner" style="border:1px solid #6a5420;background:#1c170d;color:#f0c46a;border-radius:10px;padding:10px 12px;font-size:13px">{melding}</div>}

      <div style={`${CARD};padding:10px 6px`}>
        <div style="display:grid;grid-template-columns:minmax(0,1fr) 34px 34px minmax(0,1fr);align-items:center">
          <span style={`grid-column:1 / span 4;text-align:center;${MONO};font-size:10px;color:#8b8b86;letter-spacing:.08em;margin-bottom:4px`}>▲ SD-KORT-ENDEN · PINNE 1</span>
          <span style={`${MONO};font-size:9.5px;color:#8b8b86;text-align:right;padding-right:8px`}>innerst (oddetall)</span>
          <span style={`grid-column:2 / span 2;background:${PCB};border-radius:8px 8px 0 0;height:8px;align-self:end`} />
          <span style={`${MONO};font-size:9.5px;color:#8b8b86;padding-left:8px`}>mot kanten (partall)</span>
          {rader.map(([o, e], k) => {
            const sone = (o?.fys ?? 0) >= (r.lydkort_fys[0] ?? 31);
            return [
              <div key={'l' + k} style="min-width:0;overflow:hidden">{etikett(o, 'v')}</div>,
              <div key={'o' + k} style={`background:${PCB};${sone ? 'box-shadow:inset 0 0 0 999px rgba(79,127,224,.10);' : ''}`}>{pinneKnapp(o)}</div>,
              <div key={'e' + k} style={`background:${PCB};${sone ? 'box-shadow:inset 0 0 0 999px rgba(79,127,224,.10);' : ''}`}>{pinneKnapp(e)}</div>,
              <div key={'r' + k} style="min-width:0;overflow:hidden">{etikett(e, 'h')}</div>,
            ];
          })}
          <span />
          <span style={`grid-column:2 / span 2;background:${PCB};border-radius:0 0 8px 8px;height:8px`} />
          <span />
          <span style={`grid-column:1 / span 4;text-align:center;${MONO};font-size:10px;color:#8b8b86;letter-spacing:.08em;margin-top:4px`}>PINNE 31–40: LYDKORTET (I²S) OG GND · ▼ USB-ENDEN</span>
        </div>
      </div>

      <span style="font-size:16px;font-weight:600;margin-top:4px">Funksjoner</span>
      <div style={CARD}>
        {grupper.map((gr, gi) => (
          <div key={gr} style={`display:flex;flex-direction:column;border-top:1px solid ${gi ? '#242426' : 'transparent'};padding:8px 14px 10px`}>
            <span style={`${MONO};font-size:10px;letter-spacing:.1em;color:${GRUPPE[gr]?.farge ?? '#8b8b86'};margin:2px 0 4px`}>{(GRUPPE[gr]?.navn ?? gr).toUpperCase()}</span>
            {r.funksjoner.filter((f) => f.gruppe === gr).map((f) => {
              const g = utkast[f.id] ?? null;
              const endretHer = (data.pinner[f.id] ?? null) !== g;
              return (
                <label key={f.id} style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;min-height:40px">
                  <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style="font-size:13px;overflow-wrap:anywhere">{f.navn}{endretHer && <span style="color:#d9a441"> ●</span>}</span>{g !== null && <span style={`${MONO};font-size:10px;color:#8b8b86`}>fysisk pinne {fys.get(g) ?? '?'}</span>}</span>
                  <select value={g === null ? '' : String(g)} aria-label={'Pinne for ' + f.navn}
                    onChange={(ev) => { const x = (ev.currentTarget as HTMLSelectElement).value; if (x === '') { if (g !== null) sett(g, null); } else sett(Number(x), f.id); }}
                    style="height:34px;max-width:52vw;padding:0 8px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;color:#f2f2ee;font-size:13px">
                    <option value="">Ingen</option>
                    {valg.map((x) => { const e = eierAv(utkast, x); return <option key={x} value={String(x)}>{`GPIO${x} (pinne ${fys.get(x) ?? '?'})` + (e && e !== f.id ? ' – ' + navnPaa(r, e) : '')}</option>; })}
                  </select>
                </label>
              );
            })}
          </div>
        ))}
      </div>

      <div style={`${CARD};padding:12px 14px;gap:10px`}>
        {v.feil.length > 0 && <div style="display:flex;flex-direction:column;gap:4px">{v.feil.map((x) => <span key={x} style="font-size:12px;color:#ff8a7a">✕ {x}</span>)}</div>}
        {v.advarsler.length > 0 && <div style="display:flex;flex-direction:column;gap:4px">{v.advarsler.map((x) => <span key={x} style="font-size:12px;color:#e0b25a;text-wrap:pretty">⚠ {x}</span>)}</div>}
        {endret.length > 0 && <div style="display:flex;flex-direction:column;gap:3px"><span style="font-size:12px;color:#c9c9c4">Endringer som ikke er lagret:</span>{endret.map((x) => <span key={x} style={`${MONO};font-size:11px;color:#f0c46a`}>{x}</span>)}</div>}
        {svar.length > 0 && <div style="display:flex;flex-direction:column;gap:3px">{svar.map((x) => <span key={x} style="font-size:12px;color:#c9c9c4">{x}</span>)}</div>}
        {lagrer === 'restart' && <span style="font-size:13px;color:#6fcf7f">Lagret. Skjold starter på nytt med de nye pinnene – siden lastes inn igjen om litt.</span>}
        <div style="display:flex;flex-wrap:wrap;gap:8px">
          <button disabled={!!lagrer || v.feil.length > 0 || endret.length === 0} onClick={() => void lagre()}
            style={BTN('#d9a441', '#111', v.feil.length || !endret.length || lagrer ? '#6b5a35' : '#d9a441') + ';font-weight:600'}>
            {lagrer === 'lagrer' ? 'Lagrer …' : 'Lagre og start på nytt'}
          </button>
          {endret.length > 0 && <button disabled={!!lagrer} onClick={() => { setUtkast({ ...data.pinner }); setMelding(''); }} style={BTN()}>Angre endringer</button>}
          {data.overstyrt && <Bekreft disabled={!!lagrer} label="Tilbakestill til standard" onConfirm={() => void tilbakestill()} />}
        </div>
        <span style="font-size:11px;color:#8b8b86;text-wrap:pretty">
          Pinnene leses fra <span style={MONO}>{data.fil}</span>{data.overstyrt ? ' (dine egne pinner – «Tilbakestill til standard» sletter fila).' : ' (standardpinnene).'}
        </span>
        {ikkeAktiv.length > 0 && <span style="font-size:11px;color:#e0b25a">Fila er endret siden Skjold startet. Disse er ikke i bruk ennå: {ikkeAktiv.join(', ')}</span>}
        {data.maskinvarefeil.length > 0 && <div style="display:flex;flex-direction:column;gap:3px"><span style="font-size:12px;color:#ff8a7a">Pinner som ikke kunne tas i bruk ved oppstart:</span>{data.maskinvarefeil.map((x) => <span key={x} style={`${MONO};font-size:11px;color:#ff8a7a`}>{x}</span>)}</div>}
      </div>

      {valgt !== null && (
        <div role="dialog" aria-label={`Velg funksjon for GPIO${valgt}`} onClick={(e) => { if (e.target === e.currentTarget) setValgt(null); }}
          style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.45);display:flex;align-items:flex-end;justify-content:center">
          <div style="width:100%;max-width:620px;max-height:75vh;overflow-y:auto;background:#141415;border:1px solid #2e2e30;border-radius:16px 16px 0 0;padding:14px 16px calc(16px + env(safe-area-inset-bottom));display:flex;flex-direction:column;gap:10px">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
              <span style="display:flex;flex-direction:column;gap:2px">
                <span style="font-size:16px;font-weight:600">GPIO{valgt} · pinne {fys.get(valgt) ?? '?'}{r.alt[String(valgt)] ? ' · ' + r.alt[String(valgt)] : ''}</span>
                <span style="font-size:12px;color:#8b8b86">{valgtEier ? 'Brukes nå til: ' + navnPaa(r, valgtEier) : valgtSperret ? '' : 'Ledig'}</span>
              </span>
              <button onClick={() => setValgt(null)} style={BTN()}>Lukk</button>
            </div>
            {valgtSperret ? <span style="font-size:13px;color:#ff8a7a">{valgtSperret}. Denne pinnen kan ikke brukes.</span> : <>
              {r.varsel[String(valgt)] && <span style="font-size:12px;color:#e0b25a;text-wrap:pretty">⚠ {r.varsel[String(valgt)]}</span>}
              {grupper.map((gr) => (
                <div key={gr} style="display:flex;flex-direction:column;gap:6px">
                  <span style={`${MONO};font-size:10px;letter-spacing:.1em;color:${GRUPPE[gr]?.farge ?? '#8b8b86'}`}>{(GRUPPE[gr]?.navn ?? gr).toUpperCase()}</span>
                  <div style="display:flex;flex-wrap:wrap;gap:6px">
                    {r.funksjoner.filter((f) => f.gruppe === gr).map((f) => {
                      const har = utkast[f.id] ?? null, er = har === valgt;
                      return (
                        <button key={f.id} onClick={() => sett(valgt, f.id)}
                          style={`min-height:34px;padding:4px 12px;border-radius:999px;border:1px solid ${er ? '#d9a441' : '#2e2e30'};background:${er ? '#1c170d' : '#1b1b1c'};color:${er ? '#f0c46a' : '#f2f2ee'};font-size:12px;cursor:pointer;text-align:left`}>
                          {f.navn}{!er && har !== null ? <span style={`${MONO};font-size:10px;color:#8b8b86`}> (nå GPIO{har})</span> : null}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
              <button onClick={() => sett(valgt, null)} style={BTN(valgtEier ? '#e05a4a' : '#2e2e30', valgtEier ? '#ff8a7a' : '#8b8b86')}>Ingen (gjør pinnen ledig)</button>
              <span style="font-size:11px;color:#8b8b86;text-wrap:pretty">Har en annen funksjon pinnen fra før, får den pinnen du flytter fra – eller ingen pinne hvis funksjonen ikke hadde noen.</span>
            </>}
          </div>
        </div>
      )}
    </div>
  );
}

function Bekreft({ label, onConfirm, disabled }: { label: string; onConfirm: () => void; disabled: boolean }) {
  const [armed, setArmed] = useState(false);
  useEffect(() => { if (!armed) return; const t = setTimeout(() => setArmed(false), 4000); return () => clearTimeout(t); }, [armed]);
  return <button disabled={disabled} onClick={() => { if (armed) { setArmed(false); onConfirm(); } else setArmed(true); }} style={BTN(armed ? '#e05a4a' : '#2e2e30', armed ? '#ff8a7a' : '#f2f2ee')}>{armed ? 'Trykk igjen for å slette dine pinner' : label}</button>;
}
