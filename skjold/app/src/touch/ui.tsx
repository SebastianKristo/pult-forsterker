// Skjold Touch – felles byggeklosser laget for fingre: glidebryter, skjermtastatur og ark som glir opp.
import type { ComponentChildren } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';

export const MONO = "'IBM Plex Mono',monospace";

/** Glidebryter med 44 px treffflate. Følger fingeren direkte, og knotten vokser mens du drar.
 *  onInput kalles fortløpende, onCommit når fingeren slipper. */
export function Slider({ value, max = 100, onInput, onCommit, color = '#f0c46a', thin, disabled, label }: {
  value: number; max?: number; onInput?: (v: number) => void; onCommit?: (v: number) => void; color?: string; thin?: boolean; disabled?: boolean; label: string;
}) {
  const el = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<number | null>(null);
  const at = (x: number) => { const r = el.current!.getBoundingClientRect(); return Math.max(0, Math.min(1, (x - r.left - 11) / Math.max(1, r.width - 22))) * max; };
  const v = drag ?? value, pct = max > 0 ? Math.max(0, Math.min(1, v / max)) : 0;
  const h = thin ? 4 : 6, knob = drag !== null ? 26 : thin ? 14 : 22;
  return (
    <div ref={el} role="slider" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={Math.round(v)} aria-disabled={disabled}
      onPointerDown={(e) => { if (disabled) return; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); const n = at(e.clientX); setDrag(n); onInput?.(n); }}
      onPointerMove={(e) => { if (drag === null) return; const n = at(e.clientX); setDrag(n); onInput?.(n); }}
      onPointerUp={(e) => { if (drag === null) return; const n = at(e.clientX); setDrag(null); onCommit?.(n); }}
      onPointerCancel={() => setDrag(null)}
      style="position:relative;flex:1;min-width:0;height:44px;touch-action:none;display:flex;align-items:center;padding:0 11px;box-sizing:border-box">
      <div style={`position:relative;width:100%;height:${h}px;border-radius:${h / 2}px;background:#2a2a2c`}>
        <div style={`width:${(pct * 100).toFixed(2)}%;height:100%;border-radius:${h / 2}px;background:${color}`} />
        {!disabled && <div style={`position:absolute;top:50%;left:${(pct * 100).toFixed(2)}%;width:${knob}px;height:${knob}px;margin:${-knob / 2}px 0 0 ${-knob / 2}px;border-radius:50%;background:#f2f2ee;box-shadow:0 2px 8px rgba(0,0,0,.5);transition:width .12s ease,height .12s ease,margin .12s ease`} />}
      </div>
    </div>
  );
}

const ROWS = ['qwertyuiopå', 'asdfghjkløæ', 'zxcvbnm'];
const NUM = ['1234567890', '-/:;()&@"', ".,?!'"];
const SYM = ['[]{}#%^*+=', '_\\|~<>€$£', ".,?!'"];   // flere tegn
/** Skjermtastatur (norsk). Enheten har ikke noe annet tastatur.
 *  Shift: ett trykk = stor bokstav på neste tegn, dobbelttrykk = lås (alle store), hold inne = store mens du holder.
 *  «123» gir tall og tegn, og «#+=» der gir flere tegn (# % * + = osv.). */
/** Markøren i et tekstfelt på skjermen: verdi + posisjon, med inn/slett/flytt. */
export interface Tekst { v: string; p: number; sett: (v: string) => void; inn: (c: string) => void; slett: () => void; flytt: (d: number) => void; til: (p: number) => void }
export function useTekst(maks: number, start = ''): Tekst {
  const [s, setS] = useState({ v: start, p: start.length });
  return {
    v: s.v, p: s.p,
    sett: (v) => setS({ v: v.slice(0, maks), p: Math.min(v.length, maks) }),
    inn: (c) => setS((o) => (o.v.length + c.length > maks ? o : { v: o.v.slice(0, o.p) + c + o.v.slice(o.p), p: o.p + c.length })),
    slett: () => setS((o) => (o.p === 0 ? o : { v: o.v.slice(0, o.p - 1) + o.v.slice(o.p), p: o.p - 1 })),
    flytt: (d) => setS((o) => ({ ...o, p: Math.max(0, Math.min(o.v.length, o.p + d)) })),
    til: (p) => setS((o) => ({ ...o, p: Math.max(0, Math.min(o.v.length, p)) }))
  };
}
/** Teksten med blinkende markør. Trykk på et tegn for å flytte markøren dit. skjul = passord (prikker). */
export function TekstFelt({ t, skjul = false, tom, size = 17 }: { t: Tekst; skjul?: boolean; tom: string; size?: number }) {
  const tegn = [...t.v];
  const markør = <i key="m" class="markor" style={`display:inline-block;width:2px;height:${Math.round(size * 1.15)}px;margin:0 -1px;vertical-align:middle;background:#f0c46a;border-radius:1px`} />;
  const trykk = (i: number) => (e: PointerEvent) => { const r = (e.currentTarget as HTMLElement).getBoundingClientRect(); t.til(e.clientX > r.left + r.width / 2 ? i + 1 : i); };
  return (
    <span style={`flex:1;min-width:0;font-size:${size}px;letter-spacing:${skjul ? '.15em' : 0};white-space:pre;overflow:hidden;display:flex;align-items:center;justify-content:flex-start;color:${t.v ? '#f2f2ee' : '#6b6b67'}`}
      onPointerDown={(e) => { if (e.target === e.currentTarget) t.til(t.v.length); }}>
      {!t.v ? <>{markør}<span style="margin-left:4px">{tom}</span></> : <>
        {tegn.map((c, i) => [i === t.p ? markør : null, <span key={i} onPointerDown={trykk(i)}>{skjul ? '•' : c}</span>])}
        {t.p >= tegn.length && markør}
      </>}
    </span>
  );
}
/** Tekstfeltet som volumhjulet styrer nå (Keyboard registrerer seg når det vises). */
export const hjulMål: { cur: null | { flytt: (d: number) => void; slett: () => void } } = { cur: null };

export function Keyboard({ onKey, onBack, onEnter, onFlytt, enter = 'Søk' }: { onKey: (c: string) => void; onBack: () => void; onEnter: () => void; onFlytt?: (d: number) => void; enter?: string; pw?: boolean }) {
  const siste = useRef({ onBack, onFlytt });
  siste.current = { onBack, onFlytt };
  useEffect(() => {
    const mål = { flytt: (d: number) => siste.current.onFlytt?.(d), slett: () => siste.current.onBack() };
    hjulMål.cur = mål;
    const si = (on: boolean) => { void fetch('/api/touch/tekst', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ on }) }).catch(() => {}); };
    si(true);
    const iv = window.setInterval(() => si(true), 20000);
    return () => { window.clearInterval(iv); if (hjulMål.cur === mål) { hjulMål.cur = null; si(false); } };
  }, []);
  const [num, setNum] = useState(false), [sym, setSym] = useState(false);
  const [shift, setShift] = useState<0 | 1 | 2>(0);   // 0 av, 1 neste tegn, 2 låst
  const sist = useRef(0), holdt = useRef(false), brukt = useRef(false);
  const caps = shift > 0;
  const rows = num ? (sym ? SYM : NUM) : caps ? ROWS.map((r) => r.toUpperCase()) : ROWS;
  const key = 'height:42px;border-radius:9px;border:none;background:#242426;color:#f2f2ee;font-size:17px;padding:0;flex:1;min-width:0';
  const wide = 'height:42px;border-radius:9px;border:none;background:#1a1a1c;color:#c9c9c4;font-size:12.5px;font-weight:600;padding:0';
  const shiftNed = (e: PointerEvent) => {
    e.preventDefault();
    const n = Date.now();
    setShift(shift === 2 ? 0 : shift === 1 ? (n - sist.current < 350 ? 2 : 0) : 1);
    sist.current = n; holdt.current = true; brukt.current = false;
  };
  const shiftOpp = () => { if (holdt.current && brukt.current) setShift(0); holdt.current = false; };
  const tast = (c: string) => {
    onKey(c);
    if (shift === 1 && !num) { if (holdt.current) brukt.current = true; else setShift(0); }
  };
  const aktiv = 'background:#f2f2ee;color:#0b0b0c';
  return (
    <div class="kb" style="flex-shrink:0;display:flex;flex-direction:column;gap:5px;padding:8px 10px 10px;background:#101011;border-top:1px solid #1f1f21">
      {rows.map((r, i) => (
        <div key={i + (num ? 'n' : 'a')} style="display:flex;gap:5px">
          {i === 1 && (num
            ? <button onClick={() => setSym(!sym)} aria-label="Flere tegn" aria-pressed={sym} style={wide + `;width:52px;flex-shrink:0;${sym ? aktiv : ''}`}>{sym ? '123' : '#+='}</button>
            : <button data-lyd="tast" onPointerDown={shiftNed} onPointerUp={shiftOpp} onPointerCancel={shiftOpp} onPointerLeave={shiftOpp}
                aria-label={shift === 2 ? 'Store bokstaver låst' : 'Store bokstaver'} aria-pressed={caps}
                style={wide + `;width:52px;flex-shrink:0;touch-action:none;font-size:18px;${caps ? aktiv : ''}${shift === 2 ? ';box-shadow:inset 0 -3px 0 #f0c46a' : ''}`}>{shift === 2 ? '⇪' : '⇧'}</button>)}
          {i === 2 && <button onClick={() => setNum(!num)} aria-label={num ? 'Bokstaver' : 'Tall og tegn'} style={wide + ';width:74px;flex-shrink:0'}>{num ? 'abc' : '123'}</button>}
          {[...r].map((c) => <button key={c} data-lyd="tast" onPointerDown={(e) => { e.preventDefault(); tast(c); }} style={key + ';touch-action:none'}>{c}</button>)}
          {i === 2 && <button data-lyd="slett" onPointerDown={(e) => { e.preventDefault(); onBack(); }} aria-label="Slett" style={wide + ';width:74px;flex-shrink:0;touch-action:none;display:flex;align-items:center;justify-content:center'}><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 5h12v14H8l-6-7zM12 9.5l5 5M17 9.5l-5 5" /></svg></button>}
        </div>
      ))}
      <div style="display:flex;gap:5px">
        {onFlytt && <button data-lyd="tast" onPointerDown={(e) => { e.preventDefault(); onFlytt(-1); }} aria-label="Markør til venstre" style={wide + ';width:52px;flex-shrink:0;touch-action:none;font-size:16px'}>◀</button>}
        <button data-lyd="tast" onPointerDown={(e) => { e.preventDefault(); tast(' '); }} aria-label="Mellomrom" style={key + ';background:#1a1a1c;font-size:12.5px;color:#8b8b86;touch-action:none'}>mellomrom</button>
        {onFlytt && <button data-lyd="tast" onPointerDown={(e) => { e.preventDefault(); onFlytt(1); }} aria-label="Markør til høyre" style={wide + ';width:52px;flex-shrink:0;touch-action:none;font-size:16px'}>▶</button>}
        <button onClick={onEnter} style="height:42px;width:150px;flex-shrink:0;border-radius:9px;border:none;background:#f0c46a;color:#0b0b0c;font-size:13.5px;font-weight:600;padding:0">{enter}</button>
      </div>
    </div>
  );
}

/** Ark som glir opp fra bunnen over innholdet (kø, dimmer). Trykk utenfor lukker. */
export function Sheet({ title, kicker, onClose, children, height = 300 }: { title: string; kicker?: string; onClose: () => void; children: ComponentChildren; height?: number }) {
  return (
    <div style="position:absolute;inset:0;z-index:8">
      <div onClick={onClose} style="position:absolute;inset:0;background:rgba(0,0,0,.6);animation:tinn .2s ease both" />
      <div style={`position:absolute;left:10px;right:10px;bottom:10px;max-height:${height}px;border-radius:18px;border:1px solid #2e2e30;background:#18181a;box-shadow:0 -10px 40px rgba(0,0,0,.6);display:flex;flex-direction:column;animation:opp .25s cubic-bezier(.2,.8,.2,1) both;overflow:hidden`}>
        <div style="display:flex;align-items:center;gap:10px;padding:8px 8px 6px 18px;flex-shrink:0">
          <span style="display:flex;flex-direction:column;gap:1px;flex:1;min-width:0">
            {kicker && <span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>{kicker}</span>}
            <span style="font-size:16px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{title}</span>
          </span>
          <button onClick={onClose} aria-label="Lukk" style="width:44px;height:44px;border:none;background:none;color:#8b8b86;display:flex;align-items:center;justify-content:center;padding:0"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** Kaller `fn` når fingeren har ligget stille i 450 ms (langt trykk). Returnerer hendelsene som settes på elementet,
 *  og `fired()` som sier om det siste trykket ble et langt trykk (så det vanlige trykket kan hoppes over). */
export function useLongPress(fn: () => void): { on: Record<string, (e: PointerEvent) => void>; fired: () => boolean } {
  const t = useRef(0), hit = useRef(false), xy = useRef<[number, number]>([0, 0]);
  const clear = () => { clearTimeout(t.current); };
  return {
    on: {
      onPointerDown: (e) => { hit.current = false; xy.current = [e.clientX, e.clientY]; clear(); t.current = window.setTimeout(() => { hit.current = true; fn(); }, 450); },
      onPointerMove: (e) => { if (Math.abs(e.clientX - xy.current[0]) + Math.abs(e.clientY - xy.current[1]) > 12) clear(); },
      onPointerUp: clear, onPointerCancel: clear, onPointerLeave: clear
    },
    fired: () => hit.current
  };
}

const WH = 62;      // høyden på én rad i hjulet
/** Rullehjul for tall (time, minutt): dra eller sveip, og det stopper på nærmeste verdi. Trykk på raden over eller under
 *  for å gå ett steg. Tre rader vises, den midterste er valgt. */
export function Wheel({ value, count, onChange, label, pad = 2 }: { value: number; count: number; onChange: (v: number) => void; label: string; pad?: number }) {
  const el = useRef<HTMLDivElement>(null), t = useRef(0), own = useRef(value);
  useEffect(() => { if (el.current && own.current !== value) { own.current = value; el.current.scrollTop = value * WH; } }, [value]);
  useEffect(() => { if (el.current) el.current.scrollTop = value * WH; }, []);
  const settle = () => {
    clearTimeout(t.current);
    t.current = window.setTimeout(() => {
      if (!el.current) return;
      const v = Math.max(0, Math.min(count - 1, Math.round(el.current.scrollTop / WH)));
      if (v !== own.current) { own.current = v; onChange(v); }
    }, 90);
  };
  const go = (v: number) => { if (el.current && v >= 0 && v < count) el.current.scrollTo({ top: v * WH, behavior: 'smooth' }); };
  return (
    <div style={`position:relative;width:118px;height:${WH * 3}px;flex-shrink:0`}>
      <div style={`position:absolute;left:0;right:0;top:${WH}px;height:${WH}px;border-radius:14px;background:#1c170d;border:1px solid #d9a441;pointer-events:none`} />
      <div ref={el} role="spinbutton" aria-label={label} aria-valuemin={0} aria-valuemax={count - 1} aria-valuenow={value} onScroll={settle}
        style={`position:relative;height:100%;overflow-y:scroll;scroll-snap-type:y mandatory;scrollbar-width:none;touch-action:pan-y;overscroll-behavior:contain;-webkit-mask-image:linear-gradient(180deg,transparent,#000 30%,#000 70%,transparent);mask-image:linear-gradient(180deg,transparent,#000 30%,#000 70%,transparent)`}>
        <div style={`height:${WH}px`} />
        {Array.from({ length: count }, (_, i) => (
          <button key={i} class="flat" onClick={() => go(i)} tabIndex={-1}
            style={`display:block;width:100%;height:${WH}px;scroll-snap-align:center;border:none;background:none;padding:0;font-family:${MONO};font-size:44px;font-weight:500;color:${i === value ? '#f2f2ee' : '#6b6b67'}`}>{String(i).padStart(pad, '0')}</button>
        ))}
        <div style={`height:${WH}px`} />
      </div>
    </div>
  );
}

