import type { ComponentChildren, JSX } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';

export function Logo({ lg = false, word = true }: { lg?: boolean; word?: boolean }) {
  const hs = lg ? [11, 16, 21, 16, 11] : [8, 12, 16, 12, 8];
  return (
    <div class={'logo' + (lg ? ' lg' : '')}>
      <div class="bars">{hs.map((h, i) => <i key={i} style={{ height: h + 'px' }} />)}</div>
      {word && <span class="word">SKJOLD</span>}
    </div>
  );
}

export function Icon({ d, size = 18, sw = 1.8, color, style }: { d: string; size?: number; sw?: number; color?: string; style?: JSX.CSSProperties }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color ?? 'currentColor'} stroke-width={sw} stroke-linecap="round" stroke-linejoin="round" style={style}>
      <path d={d} />
    </svg>
  );
}

export function Toggle({ on, onChange, red = false, disabled = false, label }: { on: boolean; onChange: (v: boolean) => void; red?: boolean; disabled?: boolean; label?: string }) {
  return <button type="button" class={'toggle' + (on ? ' on' : '') + (red ? ' red' : '')} role="switch" aria-checked={on} aria-label={label} disabled={disabled} onClick={() => onChange(!on)} />;
}

export function Chip({ on = false, sq = false, onClick, children, dot, title }: { on?: boolean; sq?: boolean; onClick?: () => void; children: ComponentChildren; dot?: boolean | null; title?: string }) {
  return (
    <button type="button" class={'chip' + (on ? ' on' : '') + (sq ? ' sq' : '')} onClick={onClick} title={title}>
      {children}
      {dot !== undefined && <i class={'dot' + (dot ? ' on' : '')} />}
    </button>
  );
}

export function Stepper({ value, min, max, fmt, onChange }: { value: number; min: number; max: number; fmt: (v: number) => string; onChange: (v: number) => void }) {
  return (
    <div class="stepper">
      <button type="button" class="btn square" aria-label="Mindre" onClick={() => onChange(Math.max(min, value - 1))}>−</button>
      <span class="v">{fmt(value)}</span>
      <button type="button" class="btn square" aria-label="Mer" onClick={() => onChange(Math.min(max, value + 1))}>+</button>
    </div>
  );
}

/** Confirm-on-second-tap action button (as in the design: "Trykk igjen"). */
export function ConfirmButton({ label, onConfirm, safe = false, danger = false, className = '' }: { label: string; onConfirm: () => void; safe?: boolean; danger?: boolean; className?: string }) {
  const [armed, setArmed] = useState(false);
  useEffect(() => { if (!armed) return; const t = setTimeout(() => setArmed(false), 4000); return () => clearTimeout(t); }, [armed]);
  return (
    <button type="button" class={'btn sm ' + (armed || danger ? 'danger ' : '') + className} onClick={() => { if (safe || armed) { setArmed(false); onConfirm(); } else setArmed(true); }}>
      {armed ? 'Trykk igjen' : label}
    </button>
  );
}

/**
 * Slider som eier verdien sin mens den dras og i 800 ms etter slipp (innkommende status ignoreres da, så den ikke hopper).
 * onCommit(v, false) mens den dras (maks hvert 100 ms), onCommit(v, true) ved slipp.
 */
export function Slider({ value, min = 0, max = 100, step = 1, onCommit, className = 'range', vertical = false, label }: { value: number; min?: number; max?: number; step?: number; onCommit: (v: number, final: boolean) => void; className?: string; vertical?: boolean; label?: string }) {
  const [local, setLocal] = useState(value);
  const drag = useRef(false);
  const released = useRef(0);
  const last = useRef(0);
  const sent = useRef<number | null>(null);
  const relT = useRef(0);
  const latest = useRef(value); latest.current = value;
  useEffect(() => {
    if (drag.current || Date.now() - released.current < 800) return;
    setLocal(value);
  }, [value]);
  useEffect(() => () => clearTimeout(relT.current), []);
  const release = (v: number) => {
    drag.current = false; released.current = Date.now();
    if (sent.current !== v) { sent.current = v; onCommit(v, true); }
    clearTimeout(relT.current);
    relT.current = window.setTimeout(() => { if (!drag.current) setLocal(latest.current); }, 850);
  };
  return (
    <input
      type="range" min={min} max={max} step={step} value={local} class={vertical ? 'vrange' : className} aria-label={label}
      onPointerDown={() => { drag.current = true; sent.current = null; }}
      onPointerUp={(e) => release(+(e.currentTarget as HTMLInputElement).value)}
      onPointerCancel={(e) => release(+(e.currentTarget as HTMLInputElement).value)}
      onInput={(e) => {
        const v = +(e.currentTarget as HTMLInputElement).value; setLocal(v);
        const now = Date.now();
        if (now - last.current >= 100) { last.current = now; sent.current = v; onCommit(v, false); }
      }}
      onChange={(e) => release(+(e.currentTarget as HTMLInputElement).value)}
    />
  );
}

export function Section({ title, action, children }: { title: string; action?: ComponentChildren; children: ComponentChildren }) {
  return (
    <div class="col gap10">
      <div class="row between"><span class="h2">{title}</span>{action}</div>
      {children}
    </div>
  );
}

export const PLAY = 'M8 5.2v13.6a1 1 0 0 0 1.52.85l10.6-6.8a1 1 0 0 0 0-1.7L9.52 4.35A1 1 0 0 0 8 5.2z';
export function PlayPauseIcon({ playing, size = 28 }: { playing: boolean; size?: number }) {
  return playing ? (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4.5" width="4" height="15" rx="1.2" /><rect x="14" y="4.5" width="4" height="15" rx="1.2" /></svg>
  ) : (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><path d={PLAY} /></svg>
  );
}
export function PrevIcon({ size = 26 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="5" width="2.4" height="14" rx="1" /><path d="M20 5.8v12.4a1 1 0 0 1-1.55.83L9.3 12.83a1 1 0 0 1 0-1.66l9.15-6.2A1 1 0 0 1 20 5.8z" /></svg>;
}
export function NextIcon({ size = 26 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><rect x="17.6" y="5" width="2.4" height="14" rx="1" /><path d="M4 5.8v12.4a1 1 0 0 0 1.55.83l9.15-6.2a1 1 0 0 0 0-1.66l-9.15-6.2A1 1 0 0 0 4 5.8z" /></svg>;
}
export function MuteIcon({ muted }: { muted: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4 9h3l5-4v14l-5-4H4z" fill="currentColor" />
      {muted ? <path d="M16 9l5 6M21 9l-5 6" /> : <path d="M16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12" />}
    </svg>
  );
}
export function PowerIcon({ size = 18 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3v8" /><path d="M6.3 6.6a8 8 0 1 0 11.4 0" /></svg>;
}
export const S1_ICON = 'M3 7.5h18a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1zM4.5 9.8h5v3.4h-5zM11.6 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M11.6 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M16.4 12a2.3 2.3 0 1 0 4.6 0a2.3 2.3 0 1 0-4.6 0M18.7 10.2v1.2M3.5 16.5v1M20.5 16.5v1';
export const NODE_ICON = 'M4 6h14a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 18 18H4a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 4 6zM19.5 8h2v2.6h-2zM19.5 11.4h2v2.6h-2zM19.5 14.6h2v2h-2zM5 7.8h9M8 18v1.2M11.5 18v1.2M6.2 11.2h4.6v4.6H6.2zM15.2 15.3a.5.5 0 1 0 1 0a.5.5 0 1 0-1 0';
export const CORE_ICON = 'M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zM8 8h8v8H8zM12 4V2M12 22v-2M4 12H2M22 12h-2M10 11h4M10 13h4';
export const PRODUCT_ICON: Record<'s1' | 'node' | 'core', string> = { s1: S1_ICON, node: NODE_ICON, core: CORE_ICON };

export { SRC_ICON } from '../lib/srcicons';
import { SRC_ICON } from '../lib/srcicons';
export function SrcCircle({ label, size = 64 }: { label: string; size?: number }) {
  const ic = SRC_ICON[label] ?? { bg: '#2a2a2c', fg: '#f2f2ee', st: '', fi: '', fp: '', sz: '47%' };
  return (
    <div class="src-circle" style={{ width: size + 'px', height: size + 'px', borderRadius: '50%', overflow: 'hidden', background: ic.bg, color: ic.fg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style={{ width: ic.sz, height: ic.sz, display: 'block' }}>
        {ic.st && <path d={ic.st} />}{ic.fi && <path d={ic.fi} fill="currentColor" stroke="none" />}{ic.fp && <path d={ic.fp} fill="currentColor" stroke="none" />}
      </svg>
    </div>
  );
}
export function Chevron({ dir = 'right', size = 16, color = 'currentColor', sw = 2 }: { dir?: 'right' | 'left' | 'down' | 'up'; size?: number; color?: string; sw?: number }) {
  const d = { right: 'M9 5l7 7-7 7', left: 'M15 5l-7 7 7 7', down: 'M6 9l6 6 6-6', up: 'M6 15l6-6 6 6' }[dir];
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} stroke-width={sw} stroke-linecap="round" stroke-linejoin="round"><path d={d} /></svg>;
}
